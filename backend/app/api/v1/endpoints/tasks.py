from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.task import EvidenceSubmission, Task
from app.models.user import UserProfile
from app.schemas.task import (
    EvidenceSubmissionRequest,
    EvidenceSubmissionResponse,
    TaskAssignRequest,
    TaskCancelRequest,
    TaskCreateRequest,
    TaskDeadlineChangeRequest,
    TaskHistoryResponse,
    TaskResponse,
    TaskReviewRequest,
    TaskReviewResponse,
    TaskUpdateRequest,
)
from app.services.errors import (
    EvidenceSubmissionError,
    PermissionDeniedError,
    ReviewError,
    ScopeIntegrityError,
    SelfReviewError,
    TaskAssigneeError,
    TaskNotFoundError,
    TaskWorkflowError,
)
from app.services.platform import is_active_platform_admin
from app.services.task import (
    assign_task,
    cancel_task,
    change_task_deadline,
    create_task,
    get_task,
    get_task_history,
    list_task_submissions,
    list_tasks,
    review_task_submission,
    start_task,
    submit_task_evidence,
    update_task,
)

router = APIRouter()


def _ensure_org_access(db: Session, user: UserProfile, organization_id: uuid.UUID) -> Organization:
    """Verifies that the organization exists, is not archived, and caller is an active member or platform admin."""
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.membership_status == "active",
        OrganizationMembership.removed_at == None,
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if not membership:
        if not is_active_platform_admin(db, user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
    return org


def _ensure_task_in_org(db: Session, task_id: uuid.UUID, organization_id: uuid.UUID) -> Task:
    """Retrieves task asserting it belongs to the given organization and is not archived."""
    task = db.get(Task, task_id)
    if not task or task.organization_id != organization_id or task.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return task


@router.post(
    "/organizations/{organization_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_task(
    organization_id: uuid.UUID,
    payload: TaskCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Creates an operational task within a verified organization."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return create_task(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            title=payload.title,
            due_date=payload.due_date,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            description=payload.description,
            priority=payload.priority,
            proof_required=payload.proof_required,
            due_time=payload.due_time,
            timezone_name=payload.timezone,
            assignee_membership_id=payload.assignee_membership_id,
        )
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ScopeIntegrityError, TaskAssigneeError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/organizations/{organization_id}/tasks",
    response_model=List[TaskResponse],
)
def list_organization_tasks(
    organization_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[uuid.UUID] = Query(None),
    assigned_to_me: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskResponse]:
    """Lists operational tasks authorized for the caller with optional filters."""
    _ensure_org_access(db, current_user, organization_id)
    return list_tasks(
        db=db,
        user=current_user,
        organization_id=organization_id,
        status=status_filter,
        scope_type=scope_type,
        scope_id=scope_id,
        assigned_to_me=assigned_to_me,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/organizations/{organization_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_organization_task(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Retrieves an individual task by ID."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_task(
            db=db,
            task_id=task_id,
            user=current_user,
            organization_id=organization_id,
        )
    except (TaskNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch(
    "/organizations/{organization_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
def update_organization_task(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Updates permitted metadata on an active task."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        return update_task(
            db=db,
            user=current_user,
            task_id=task_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/assign",
    response_model=TaskResponse,
)
def assign_organization_task(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskAssignRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Assigns or reassigns the single accountable worker for a task (D-SLICE4-01)."""
    _ensure_org_access(db, current_user, organization_id)
    task = _ensure_task_in_org(db, task_id, organization_id)
    try:
        assign_task(
            db=db,
            user=current_user,
            task_id=task_id,
            assignee_membership_id=payload.assignee_membership_id,
        )
        db.refresh(task)
        return task
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (TaskAssigneeError, ScopeIntegrityError, TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/start",
    response_model=TaskResponse,
)
def start_organization_task(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Transitions a task to in_progress."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        return start_task(db=db, user=current_user, task_id=task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/cancel",
    response_model=TaskResponse,
)
def cancel_organization_task(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskCancelRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Cancels an active task with mandatory cancellation reason."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        return cancel_task(
            db=db,
            user=current_user,
            task_id=task_id,
            cancellation_reason=payload.cancellation_reason,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/organizations/{organization_id}/tasks/{task_id}/history",
    response_model=TaskHistoryResponse,
)
def get_organization_task_history(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskHistoryResponse:
    """Retrieves full status, deadline, and assignment history for a task."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        history_data = get_task_history(db=db, user=current_user, task_id=task_id)
        return TaskHistoryResponse(**history_data)
    except (TaskNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/deadline",
    response_model=TaskResponse,
)
def change_organization_task_deadline(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskDeadlineChangeRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Adjusts task deadline with mandatory reason and audit recording."""
    _ensure_org_access(db, current_user, organization_id)
    task = _ensure_task_in_org(db, task_id, organization_id)
    try:
        change_task_deadline(
            db=db,
            user=current_user,
            task_id=task_id,
            new_due_date=payload.new_due_date,
            new_due_time=payload.new_due_time,
            reason=payload.reason,
        )
        db.refresh(task)
        return task
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/submissions",
    response_model=EvidenceSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_organization_task_evidence(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: EvidenceSubmissionRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceSubmissionResponse:
    """Submits evidence for an assigned task."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        return submit_task_evidence(
            db=db,
            user=current_user,
            task_id=task_id,
            evidence_urls=payload.evidence_urls,
            submitter_note=payload.submitter_note,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (EvidenceSubmissionError, TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/organizations/{organization_id}/tasks/{task_id}/submissions",
    response_model=List[EvidenceSubmissionResponse],
)
def list_organization_task_submissions(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EvidenceSubmissionResponse]:
    """Lists all evidence submissions and reviews for a task."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)
    try:
        return list_task_submissions(db=db, user=current_user, task_id=task_id)
    except (TaskNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/organizations/{organization_id}/tasks/{task_id}/submissions/{submission_id}/review",
    response_model=TaskReviewResponse,
)
def review_organization_task_submission(
    organization_id: uuid.UUID,
    task_id: uuid.UUID,
    submission_id: uuid.UUID,
    payload: TaskReviewRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskReviewResponse:
    """Approves or requests changes on an evidence submission."""
    _ensure_org_access(db, current_user, organization_id)
    _ensure_task_in_org(db, task_id, organization_id)

    submission = db.get(EvidenceSubmission, submission_id)
    if not submission or submission.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    try:
        return review_task_submission(
            db=db,
            user=current_user,
            submission_id=submission_id,
            decision=payload.decision,
            review_note=payload.review_note,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    except SelfReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ReviewError, TaskWorkflowError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

