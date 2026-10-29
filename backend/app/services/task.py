import urllib.parse
import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.event import Department, Event, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.task import (
    EvidenceArtifact,
    EvidenceSubmission,
    Notification,
    OperationalBlocker,
    OperationalBlockerHistory,
    Task,
    TaskAssignee,
    TaskDeadlineHistory,
    TaskReview,
    TaskStatusHistory,
)
from app.models.user import UserProfile
from app.services.errors import (
    EvidenceSubmissionError,
    OperationalBlockerError,
    OperationalBlockerNotFoundError,
    PermissionDeniedError,
    ReviewError,
    ScopeIntegrityError,
    SelfReviewError,
    TaskAssigneeError,
    TaskError,
    TaskNotFoundError,
    TaskWorkflowError,
)
from app.services.permissions import (
    ACTION_ASSIGN_TASK,
    ACTION_CHANGE_DEADLINE,
    ACTION_CREATE_BLOCKER,
    ACTION_CREATE_TASK,
    ACTION_RESOLVE_BLOCKER,
    ACTION_REVIEW_PROOF,
    ACTION_SUBMIT_PROOF,
    ACTION_UPDATE_TASK,
    ACTION_VIEW_BLOCKER,
    ACTION_VIEW_TASK,
    can_perform,
    require_permission,
    validate_target_resource_scope,
)
from app.services.timezones import is_valid_timezone

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_BLOCKER_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_SCOPES = {"organization", "program", "event", "department"}


def validate_evidence_url(url: str) -> str:
    """
    Validates an evidence URL strictly for Slice 4A (Section 5).
    Accepts only valid absolute HTTP or HTTPS URLs with non-empty hostname.
    Rejects unsupported schemes (file, javascript, data) and malformed URLs.
    Does not perform any server-side network fetches.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Evidence URL cannot be empty.")
    clean = url.strip()
    if not clean:
        raise ValueError("Evidence URL cannot be empty.")
    if len(clean) > 2048:
        raise ValueError("Evidence URL exceeds maximum allowed length of 2048 characters.")
    parsed = urllib.parse.urlparse(clean)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Evidence URL must use HTTP or HTTPS scheme, got: '{parsed.scheme}'.")
    if not parsed.netloc:
        raise ValueError(f"Evidence URL is malformed or missing hostname/domain: '{clean}'.")
    return clean


def _resolve_task_hierarchy(
    db: Session,
    organization_id: uuid.UUID,
    scope_type: str,
    scope_id: Optional[uuid.UUID],
) -> tuple[Optional[uuid.UUID], Optional[uuid.UUID], Optional[uuid.UUID]]:
    """
    Resolves and verifies explicit parent program_id, event_id, and department_id
    from the given scope_type and scope_id, enforcing organization tenancy and non-archival.
    """
    program_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None

    if scope_type == "organization":
        if scope_id is not None and scope_id != organization_id:
            raise ScopeIntegrityError("Organization-scoped task must not specify an alien scope_id.")
    elif scope_type == "program":
        if scope_id is None:
            raise ScopeIntegrityError("Program-scoped task requires a non-null scope_id.")
        prog = db.get(Program, scope_id)
        if not prog or prog.archived_at is not None or prog.organization_id != organization_id:
            raise ScopeIntegrityError(f"Target program '{scope_id}' not found, archived, or belongs to another organization.")
        program_id = prog.id
    elif scope_type == "event":
        if scope_id is None:
            raise ScopeIntegrityError("Event-scoped task requires a non-null scope_id.")
        ev = db.get(Event, scope_id)
        if not ev or ev.archived_at is not None or ev.organization_id != organization_id:
            raise ScopeIntegrityError(f"Target event '{scope_id}' not found, archived, or belongs to another organization.")
        if ev.program_id is not None:
            parent_prog = db.get(Program, ev.program_id)
            if not parent_prog or parent_prog.archived_at is not None or parent_prog.organization_id != organization_id:
                raise ScopeIntegrityError(f"Parent program of target event '{scope_id}' is archived or belongs to another organization.")
        event_id = ev.id
        program_id = ev.program_id
    elif scope_type == "department":
        if scope_id is None:
            raise ScopeIntegrityError("Department-scoped task requires a non-null scope_id.")
        dept = db.get(Department, scope_id)
        if not dept or dept.archived_at is not None or dept.organization_id != organization_id:
            raise ScopeIntegrityError(f"Target department '{scope_id}' not found, archived, or belongs to another organization.")
        if dept.program_id is not None:
            parent_prog = db.get(Program, dept.program_id)
            if not parent_prog or parent_prog.archived_at is not None or parent_prog.organization_id != organization_id:
                raise ScopeIntegrityError(f"Parent program of target department '{scope_id}' is archived or belongs to another organization.")
        if dept.standalone_event_id is not None:
            parent_ev = db.get(Event, dept.standalone_event_id)
            if not parent_ev or parent_ev.archived_at is not None or parent_ev.organization_id != organization_id:
                raise ScopeIntegrityError(f"Parent event of target department '{scope_id}' is archived or belongs to another organization.")
        department_id = dept.id
        program_id = dept.program_id
        event_id = dept.standalone_event_id
    else:
        raise ValueError(f"Invalid task scope_type '{scope_type}'. Must be one of: {sorted(VALID_SCOPES)}")

    return program_id, event_id, department_id


def create_task(
    db: Session,
    creator: UserProfile,
    organization_id: uuid.UUID,
    title: str,
    due_date: date,
    scope_type: str = "organization",
    scope_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
    priority: str = "medium",
    proof_required: bool = True,
    due_time: Optional[time] = None,
    timezone_name: str = "Asia/Kolkata",
    assignee_membership_id: Optional[uuid.UUID] = None,
) -> Task:
    """
    Creates a new operational task with an explicit mandatory deadline (CO-FR-005).
    Enforces verified organization status, tenant boundary validation, and auditable status logging.
    """
    # 0. User identity & org integrity
    if not creator or creator.account_status != "active" or creator.email_verified_at is None:
        raise PermissionDeniedError("Creator account is not active or email is unverified.")

    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise ScopeIntegrityError(f"Organization '{organization_id}' not found or archived.")
    if org.verification_status != "verified":
        raise PermissionDeniedError("Organization must be verified before operational tasks can be created.")

    # 1. Resolve parent hierarchy and validate scope integrity
    program_id, event_id, department_id = _resolve_task_hierarchy(
        db, organization_id=organization_id, scope_type=scope_type, scope_id=scope_id
    )

    # 2. Permission check
    require_permission(
        db,
        user=creator,
        action=ACTION_CREATE_TASK,
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )

    # 3. Input invariants
    clean_title = title.strip() if title else ""
    if not clean_title:
        raise ValueError("Task title cannot be empty.")
    if len(clean_title) > 200:
        raise ValueError("Task title cannot exceed 200 characters.")

    clean_priority = priority.strip().lower() if priority else "medium"
    if clean_priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{clean_priority}'. Must be one of: {sorted(VALID_PRIORITIES)}")

    clean_tz = timezone_name.strip() if timezone_name else "Asia/Kolkata"
    if not is_valid_timezone(clean_tz):
        raise ValueError(f"Invalid timezone identifier: '{clean_tz}'. Must be a valid IANA timezone.")

    if due_date is None:
        raise ValueError("Task deadline (due_date) is required and cannot be omitted.")

    now = datetime.now(timezone.utc)
    task = Task(
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
        program_id=program_id,
        event_id=event_id,
        department_id=department_id,
        title=clean_title,
        description=description.strip() if description else None,
        priority=clean_priority,
        status="not_started",
        proof_required=proof_required,
        due_date=due_date,
        due_time=due_time,
        timezone=clean_tz,
        created_by_user_id=creator.id,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()

    # Initial status history
    history = TaskStatusHistory(
        task_id=task.id,
        previous_status=None,
        new_status="not_started",
        reason="Task created",
        changed_by_user_id=creator.id,
        created_at=now,
    )
    db.add(history)

    # Optional initial assignment
    if assignee_membership_id is not None:
        _perform_task_assignment(
            db=db,
            actor=creator,
            task=task,
            assignee_membership_id=assignee_membership_id,
            now=now,
        )

    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


def get_task(
    db: Session,
    task_id: uuid.UUID,
    user: Optional[UserProfile] = None,
    organization_id: Optional[uuid.UUID] = None,
) -> Task:
    """Retrieves a task, enforcing organization tenancy and permission check if user is specified."""
    task = db.get(Task, task_id)
    if not task or task.archived_at is not None:
        raise TaskNotFoundError(f"Task '{task_id}' not found.")

    if organization_id and task.organization_id != organization_id:
        raise ScopeIntegrityError("Task belongs to a different organization.")

    if user:
        require_permission(
            db,
            user=user,
            action=ACTION_VIEW_TASK,
            organization_id=task.organization_id,
            scope_type="task",
            scope_id=task.id,
        )

    return task


def _perform_task_assignment(
    db: Session,
    actor: UserProfile,
    task: Task,
    assignee_membership_id: uuid.UUID,
    now: datetime,
) -> TaskAssignee:
    """Internal atomic assignment / reassignment engine preserving history."""
    membership = db.get(OrganizationMembership, assignee_membership_id)
    if not membership or membership.membership_status != "active" or membership.removed_at is not None:
        raise TaskAssigneeError(f"Target member '{assignee_membership_id}' is not an active member.")
    if membership.organization_id != task.organization_id:
        raise ScopeIntegrityError("Assignee belongs to a different organization.")

    target_user = membership.user
    if not target_user or target_user.account_status != "active" or target_user.email_verified_at is None:
        raise TaskAssigneeError("Target member user account is not active or email is unverified.")

    # Check existing active assignees
    active_assignees = [a for a in task.assignees if a.assignment_status == "active"]
    for existing in active_assignees:
        if existing.membership_id == assignee_membership_id:
            raise TaskAssigneeError(f"Member '{assignee_membership_id}' is already actively assigned to this task.")
        # Mark previous active assignment as unassigned (reassignment audit)
        existing.assignment_status = "unassigned"
        existing.unassigned_at = now
        existing.unassigned_by_user_id = actor.id

    new_assignment = TaskAssignee(
        task_id=task.id,
        organization_id=task.organization_id,
        membership_id=assignee_membership_id,
        assignment_status="active",
        assigned_by_user_id=actor.id,
        assigned_at=now,
    )
    db.add(new_assignment)

    # Transition status to 'assigned' if currently 'not_started'
    if task.status == "not_started":
        task.status = "assigned"
        task.updated_at = now
        hist = TaskStatusHistory(
            task_id=task.id,
            previous_status="not_started",
            new_status="assigned",
            reason=f"Assigned to member '{assignee_membership_id}'",
            changed_by_user_id=actor.id,
            created_at=now,
        )
        db.add(hist)

    # Emit in-app notification
    notification = Notification(
        organization_id=task.organization_id,
        user_id=target_user.id,
        event_type="task_assigned",
        related_entity_type="task",
        related_entity_id=task.id,
        title=f"Task Assigned: {task.title}",
        message=f"You have been assigned to task '{task.title}' with deadline {task.due_date}.",
        created_at=now,
    )
    db.add(notification)
    return new_assignment


def assign_task(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    assignee_membership_id: uuid.UUID,
) -> TaskAssignee:
    """Assigns or reassigns an operational task to an active workspace member (CO-FR-011)."""
    task = get_task(db, task_id)
    if task.status in ("completed", "cancelled"):
        raise TaskWorkflowError(f"Cannot assign or reassign task in terminal status '{task.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_ASSIGN_TASK,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    now = datetime.now(timezone.utc)
    assignment = _perform_task_assignment(
        db=db,
        actor=user,
        task=task,
        assignee_membership_id=assignee_membership_id,
        now=now,
    )

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except Exception:
        db.rollback()
        raise


def start_task(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
) -> Task:
    """Transitions a task from 'not_started' or 'assigned' to 'in_progress'."""
    task = get_task(db, task_id)

    # Caller must be an active assignee or authorized task manager
    is_assignee = any(
        a.assignment_status == "active" and a.membership.user_id == user.id
        for a in task.assignees
        if a.membership
    )
    if not is_assignee:
        require_permission(
            db,
            user=user,
            action=ACTION_UPDATE_TASK,
            organization_id=task.organization_id,
            scope_type=task.scope_type,
            scope_id=task.scope_id,
        )

    if task.status not in ("not_started", "assigned", "changes_requested"):
        raise TaskWorkflowError(
            f"Cannot start task currently in status '{task.status}'. Must be 'not_started', 'assigned', or 'changes_requested'."
        )

    now = datetime.now(timezone.utc)
    prev_status = task.status
    task.status = "in_progress"
    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=prev_status,
        new_status="in_progress",
        reason="Work started by assignee",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


def change_task_deadline(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    new_due_date: date,
    new_due_time: Optional[time] = None,
    reason: str = "",
) -> TaskDeadlineHistory:
    """
    Adjusts a task deadline with strict authorization and auditable history preservation (Section 4).
    Enforces non-empty reason and preserves previous due date/time and actor.
    """
    task = get_task(db, task_id)
    if task.status in ("completed", "cancelled"):
        raise TaskWorkflowError(f"Cannot change deadline for task in terminal status '{task.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_CHANGE_DEADLINE,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    if new_due_date is None:
        raise ValueError("New deadline (due_date) cannot be omitted.")

    clean_reason = reason.strip() if reason else ""
    if not clean_reason:
        raise ValueError("A meaningful reason is mandatory when changing a task deadline.")

    now = datetime.now(timezone.utc)
    deadline_history = TaskDeadlineHistory(
        task_id=task.id,
        previous_due_date=task.due_date,
        previous_due_time=task.due_time,
        new_due_date=new_due_date,
        new_due_time=new_due_time,
        reason=clean_reason,
        changed_by_user_id=user.id,
        changed_at=now,
    )
    db.add(deadline_history)

    task.due_date = new_due_date
    task.due_time = new_due_time
    task.updated_at = now

    # Notify active assignees of deadline change
    for a in task.assignees:
        if a.assignment_status == "active" and a.membership and a.membership.user:
            notif = Notification(
                organization_id=task.organization_id,
                user_id=a.membership.user_id,
                event_type="task_deadline_changed",
                related_entity_type="task",
                related_entity_id=task.id,
                title=f"Deadline Changed: {task.title}",
                message=f"Deadline for '{task.title}' was updated to {new_due_date}. Reason: {clean_reason}",
                created_at=now,
            )
            db.add(notif)

    try:
        db.commit()
        db.refresh(deadline_history)
        return deadline_history
    except Exception:
        db.rollback()
        raise


def submit_task_evidence(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    evidence_urls: List[str],
    submitter_note: Optional[str] = None,
) -> EvidenceSubmission:
    """
    Submits completion evidence (HTTP/HTTPS URLs) for an assigned task (CO-FR-007).
    Validates URL safety, creates versioned EvidenceSubmission and artifacts,
    and transitions task to 'submitted_for_review'.
    """
    task = get_task(db, task_id)

    # Caller must be an active assignee
    active_assignment = next(
        (a for a in task.assignees if a.assignment_status == "active" and a.membership.user_id == user.id),
        None,
    )
    if not active_assignment:
        raise PermissionDeniedError("Only active assignees can submit evidence for this task.")

    if task.status not in ("assigned", "in_progress", "changes_requested"):
        raise TaskWorkflowError(
            f"Cannot submit evidence for task in status '{task.status}'. "
            "Must be 'assigned', 'in_progress', or 'changes_requested'."
        )

    # Evidence requirement enforcement
    if task.proof_required:
        if not evidence_urls or len(evidence_urls) == 0:
            raise EvidenceSubmissionError("This task requires completion proof; at least one evidence URL must be provided.")

    validated_urls = [validate_evidence_url(u) for u in (evidence_urls or [])]

    now = datetime.now(timezone.utc)
    sub_count = len(task.submissions)
    submission = EvidenceSubmission(
        task_id=task.id,
        submitted_by_user_id=user.id,
        submitted_by_membership_id=active_assignment.membership_id,
        submission_number=sub_count + 1,
        submitter_note=submitter_note.strip() if submitter_note else None,
        status="pending_review",
        submitted_at=now,
    )
    db.add(submission)
    db.flush()

    for url in validated_urls:
        artifact = EvidenceArtifact(
            submission_id=submission.id,
            artifact_type="url",
            url=url,
            file_reference=None,
            created_at=now,
        )
        db.add(artifact)

    prev_status = task.status
    task.status = "submitted_for_review"
    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=prev_status,
        new_status="submitted_for_review",
        reason=f"Evidence submission #{submission.submission_number} submitted",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(submission)
        return submission
    except Exception:
        db.rollback()
        raise


def review_task_submission(
    db: Session,
    user: UserProfile,
    submission_id: uuid.UUID,
    decision: str,
    review_note: Optional[str] = None,
) -> TaskReview:
    """
    Formally approves or requests changes for an evidence submission (CO-FR-007).
    Enforces:
    - Reviewer authority within task scope.
    - Strict self-review prohibition (submitter or active assignee cannot review own work).
    - Mandatory non-empty note on changes_requested / rejection.
    - Atomic status transition with concurrency race protection.
    """
    submission = db.get(EvidenceSubmission, submission_id)
    if not submission:
        raise TaskNotFoundError(f"Evidence submission '{submission_id}' not found.")

    task = submission.task
    if not task or task.archived_at is not None:
        raise TaskNotFoundError("Parent task not found or archived.")

    clean_decision = decision.strip().lower() if decision else ""
    if clean_decision not in ("approved", "changes_requested"):
        raise ValueError(f"Invalid review decision '{clean_decision}'. Must be 'approved' or 'changes_requested'.")

    # 1. Strict Self-Review Prohibition (Submitter or active assignee cannot review own work)
    if user.id == submission.submitted_by_user_id:
        raise SelfReviewError("Assignee / submitter cannot review or approve their own task submission.")

    active_assignee_user_ids = {
        a.membership.user_id
        for a in task.assignees
        if a.assignment_status == "active" and a.membership
    }
    if user.id in active_assignee_user_ids:
        raise SelfReviewError("Assignee cannot review or approve work on their own assigned task.")

    # 2. Authority check
    require_permission(
        db,
        user=user,
        action=ACTION_REVIEW_PROOF,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    # 3. Mandatory note on rejection
    clean_note = review_note.strip() if review_note else None
    if clean_decision == "changes_requested" and not clean_note:
        raise ValueError("A meaningful rejection reason / review note is mandatory when requesting changes.")

    # 4. Resolve reviewer membership in this organization
    rev_mb = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == task.organization_id,
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.removed_at == None,
        )
    ).scalar_one_or_none()
    if not rev_mb:
        raise PermissionDeniedError("Reviewer does not hold an active membership in this organization.")

    now = datetime.now(timezone.utc)

    # 5. Atomic state update to prevent concurrent double-review races
    atomic_update = (
        update(EvidenceSubmission)
        .where(
            EvidenceSubmission.id == submission.id,
            EvidenceSubmission.status == "pending_review",
        )
        .values(status=clean_decision)
    )
    result = db.execute(atomic_update)
    if result.rowcount == 0:
        raise TaskWorkflowError("Evidence submission is not pending review or was concurrently reviewed.")

    submission.status = clean_decision

    # 6. Create TaskReview
    review = TaskReview(
        evidence_submission_id=submission.id,
        task_id=task.id,
        reviewer_user_id=user.id,
        reviewer_membership_id=rev_mb.id,
        decision=clean_decision,
        review_note=clean_note,
        reviewed_at=now,
    )
    db.add(review)

    # 7. Update Task Status
    prev_status = task.status
    if clean_decision == "approved":
        task.status = "completed"
        task.completed_at = now
    else:
        task.status = "changes_requested"
        task.completed_at = None

    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=prev_status,
        new_status=task.status,
        reason=clean_note or f"Submission #{submission.submission_number} {clean_decision}",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    # 8. In-app notification to submitter
    notif = Notification(
        organization_id=task.organization_id,
        user_id=submission.submitted_by_user_id,
        event_type="proof_reviewed",
        related_entity_type="evidence_submission",
        related_entity_id=submission.id,
        title=f"Task Submission {clean_decision.replace('_', ' ').title()}: {task.title}",
        message=f"Your submission for task '{task.title}' was {clean_decision}. Note: {clean_note or 'No notes'}",
        created_at=now,
    )
    db.add(notif)

    try:
        db.commit()
        db.refresh(review)
        return review
    except Exception:
        db.rollback()
        raise


def complete_task_without_proof(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    completion_note: Optional[str] = None,
) -> Task:
    """
    Directly completes a task that has proof_required == False.
    Tasks requiring proof strictly forbid direct completion and must pass review.
    """
    task = get_task(db, task_id)
    if task.proof_required:
        raise TaskWorkflowError("This task requires evidence submission and formal review; cannot be directly completed.")
    if task.status in ("completed", "cancelled"):
        raise TaskWorkflowError(f"Cannot complete task currently in terminal status '{task.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_REVIEW_PROOF,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    now = datetime.now(timezone.utc)
    prev_status = task.status
    task.status = "completed"
    task.completed_at = now
    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=prev_status,
        new_status="completed",
        reason=completion_note.strip() if completion_note else "Completed without proof requirement",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


def cancel_task(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    cancellation_reason: str,
) -> Task:
    """Cancels an active task with mandatory reason and status audit (CO-FR-005)."""
    task = get_task(db, task_id)
    if task.status in ("completed", "cancelled"):
        raise TaskWorkflowError(f"Cannot cancel task already in terminal status '{task.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_UPDATE_TASK,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    clean_reason = cancellation_reason.strip() if cancellation_reason else ""
    if not clean_reason:
        raise ValueError("A meaningful cancellation reason is mandatory when cancelling a task.")

    now = datetime.now(timezone.utc)
    prev_status = task.status
    task.status = "cancelled"
    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=prev_status,
        new_status="cancelled",
        reason=clean_reason,
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


def archive_task(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
) -> Task:
    """Non-destructively archives a task, preventing further operational mutations."""
    task = get_task(db, task_id)
    require_permission(
        db,
        user=user,
        action=ACTION_CREATE_TASK,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    now = datetime.now(timezone.utc)
    task.archived_at = now
    task.updated_at = now

    hist = TaskStatusHistory(
        task_id=task.id,
        previous_status=task.status,
        new_status=task.status,
        reason="Task archived",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


# =========================================================================
# Operational Blockers Domain Services (CO-FR-012)
# =========================================================================

def create_operational_blocker(
    db: Session,
    creator: UserProfile,
    organization_id: uuid.UUID,
    title: str,
    description: str,
    scope_type: str = "organization",
    scope_id: Optional[uuid.UUID] = None,
    task_id: Optional[uuid.UUID] = None,
    event_id: Optional[uuid.UUID] = None,
    priority: str = "medium",
    owner_membership_id: Optional[uuid.UUID] = None,
) -> OperationalBlocker:
    """
    Records an internal staff-only operational blocker (CO-FR-012).
    Enforces scope integrity, verified org status, and non-participant isolation.
    """
    if not creator or creator.account_status != "active" or creator.email_verified_at is None:
        raise PermissionDeniedError("Creator account is not active or email is unverified.")

    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise ScopeIntegrityError(f"Organization '{organization_id}' not found or archived.")
    if org.verification_status != "verified":
        raise PermissionDeniedError("Organization must be verified before operational blockers can be recorded.")

    # 1. Scope and referenced entity integrity
    if scope_type == "organization":
        if scope_id is not None and scope_id != organization_id:
            raise ScopeIntegrityError("Organization-scoped blocker must not specify an alien scope_id.")
    elif scope_type == "program":
        if scope_id is None:
            raise ScopeIntegrityError("Program-scoped blocker requires a non-null scope_id.")
        prog = db.get(Program, scope_id)
        if not prog or prog.archived_at is not None or prog.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced program '{scope_id}' not found, archived, or belongs to another organization.")
    elif scope_type == "event":
        if scope_id is None:
            raise ScopeIntegrityError("Event-scoped blocker requires a non-null scope_id.")
        ev = db.get(Event, scope_id)
        if not ev or ev.archived_at is not None or ev.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced event '{scope_id}' not found, archived, or belongs to another organization.")
    elif scope_type == "department":
        if scope_id is None:
            raise ScopeIntegrityError("Department-scoped blocker requires a non-null scope_id.")
        dept = db.get(Department, scope_id)
        if not dept or dept.archived_at is not None or dept.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced department '{scope_id}' not found, archived, or belongs to another organization.")
    elif scope_type == "task":
        if scope_id is None:
            raise ScopeIntegrityError("Task-scoped blocker requires a non-null scope_id.")
        t = db.get(Task, scope_id)
        if not t or t.archived_at is not None or t.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced task '{scope_id}' not found, archived, or belongs to another organization.")
    else:
        raise ValueError(f"Invalid blocker scope_type '{scope_type}'. Must be one of: {sorted(VALID_SCOPES | {'task'})}")

    if task_id:
        t = db.get(Task, task_id)
        if not t or t.archived_at is not None or t.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced task '{task_id}' not found, archived, or belongs to another organization.")

    if event_id:
        ev = db.get(Event, event_id)
        if not ev or ev.archived_at is not None or ev.organization_id != organization_id:
            raise ScopeIntegrityError(f"Referenced event '{event_id}' not found, archived, or belongs to another organization.")

    if owner_membership_id:
        mb = db.get(OrganizationMembership, owner_membership_id)
        if not mb or mb.membership_status != "active" or mb.organization_id != organization_id:
            raise ScopeIntegrityError("Blocker owner must be an active member of the organization.")

    # 2. Permission check
    require_permission(
        db,
        user=creator,
        action=ACTION_CREATE_BLOCKER,
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )

    clean_title = title.strip() if title else ""
    if not clean_title:
        raise ValueError("Blocker title cannot be empty.")
    if len(clean_title) > 200:
        raise ValueError("Blocker title cannot exceed 200 characters.")

    clean_desc = description.strip() if description else ""
    if not clean_desc:
        raise ValueError("Blocker description cannot be empty.")

    clean_priority = priority.strip().lower() if priority else "medium"
    if clean_priority not in VALID_BLOCKER_PRIORITIES:
        raise ValueError(f"Invalid blocker priority '{clean_priority}'. Must be one of: {sorted(VALID_BLOCKER_PRIORITIES)}")

    now = datetime.now(timezone.utc)
    blocker = OperationalBlocker(
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
        task_id=task_id,
        event_id=event_id,
        title=clean_title,
        description=clean_desc,
        priority=clean_priority,
        status="open",
        created_by_user_id=creator.id,
        owner_membership_id=owner_membership_id,
        created_at=now,
        updated_at=now,
    )
    db.add(blocker)
    db.flush()

    hist = OperationalBlockerHistory(
        blocker_id=blocker.id,
        previous_status=None,
        new_status="open",
        note="Blocker opened",
        changed_by_user_id=creator.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(blocker)
        return blocker
    except Exception:
        db.rollback()
        raise


def get_operational_blocker(
    db: Session,
    blocker_id: uuid.UUID,
    user: Optional[UserProfile] = None,
    organization_id: Optional[uuid.UUID] = None,
) -> OperationalBlocker:
    """Retrieves an operational blocker, checking permissions if user is provided."""
    blocker = db.get(OperationalBlocker, blocker_id)
    if not blocker:
        raise OperationalBlockerNotFoundError(f"Operational blocker '{blocker_id}' not found.")

    if organization_id and blocker.organization_id != organization_id:
        raise ScopeIntegrityError("Blocker belongs to a different organization.")

    if user:
        require_permission(
            db,
            user=user,
            action=ACTION_VIEW_BLOCKER,
            organization_id=blocker.organization_id,
            scope_type=blocker.scope_type,
            scope_id=blocker.scope_id,
        )

    return blocker


def resolve_operational_blocker(
    db: Session,
    user: UserProfile,
    blocker_id: uuid.UUID,
    resolution_note: str,
    status: str = "resolved",
) -> OperationalBlocker:
    """Resolves an operational blocker with mandatory resolution note and actor audit."""
    blocker = get_operational_blocker(db, blocker_id)
    if blocker.status in ("resolved", "wont_fix"):
        raise OperationalBlockerError(f"Blocker '{blocker_id}' is already in status '{blocker.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_RESOLVE_BLOCKER,
        organization_id=blocker.organization_id,
        scope_type=blocker.scope_type,
        scope_id=blocker.scope_id,
    )

    clean_status = status.strip().lower() if status else "resolved"
    if clean_status not in ("resolved", "wont_fix"):
        raise ValueError(f"Resolution status must be 'resolved' or 'wont_fix', got '{clean_status}'.")

    clean_note = resolution_note.strip() if resolution_note else ""
    if not clean_note:
        raise ValueError("A meaningful resolution note is mandatory when resolving a blocker.")

    now = datetime.now(timezone.utc)
    prev_status = blocker.status
    blocker.status = clean_status
    blocker.resolution_note = clean_note
    blocker.resolved_by_user_id = user.id
    blocker.resolved_at = now
    blocker.updated_at = now

    hist = OperationalBlockerHistory(
        blocker_id=blocker.id,
        previous_status=prev_status,
        new_status=clean_status,
        note=clean_note,
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    # In-app notification to creator
    notif = Notification(
        organization_id=blocker.organization_id,
        user_id=blocker.created_by_user_id,
        event_type="blocker_resolved",
        related_entity_type="operational_blocker",
        related_entity_id=blocker.id,
        title=f"Blocker Resolved: {blocker.title}",
        message=f"Blocker '{blocker.title}' marked {clean_status}. Resolution: {clean_note}",
        created_at=now,
    )
    db.add(notif)

    try:
        db.commit()
        db.refresh(blocker)
        return blocker
    except Exception:
        db.rollback()
        raise


def reopen_operational_blocker(
    db: Session,
    user: UserProfile,
    blocker_id: uuid.UUID,
    reason: str,
) -> OperationalBlocker:
    """Reopens a resolved or won't fix blocker."""
    blocker = get_operational_blocker(db, blocker_id)
    if blocker.status not in ("resolved", "wont_fix"):
        raise OperationalBlockerError(f"Cannot reopen blocker currently in status '{blocker.status}'. Must be 'resolved' or 'wont_fix'.")

    require_permission(
        db,
        user=user,
        action=ACTION_RESOLVE_BLOCKER,
        organization_id=blocker.organization_id,
        scope_type=blocker.scope_type,
        scope_id=blocker.scope_id,
    )

    clean_reason = reason.strip() if reason else ""
    if not clean_reason:
        raise ValueError("A meaningful reason is mandatory when reopening a blocker.")

    now = datetime.now(timezone.utc)
    prev_status = blocker.status
    blocker.status = "open"
    blocker.resolved_by_user_id = None
    blocker.resolved_at = None
    blocker.resolution_note = None
    blocker.updated_at = now

    hist = OperationalBlockerHistory(
        blocker_id=blocker.id,
        previous_status=prev_status,
        new_status="open",
        note=f"Reopened: {clean_reason}",
        changed_by_user_id=user.id,
        created_at=now,
    )
    db.add(hist)

    try:
        db.commit()
        db.refresh(blocker)
        return blocker
    except Exception:
        db.rollback()
        raise


# =========================================================================
# Notifications Query Helpers (CO-FR-019)
# =========================================================================

def list_notifications(
    db: Session,
    user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
    unread_only: bool = False,
) -> List[Notification]:
    """Lists in-app notifications for a user."""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if organization_id:
        stmt = stmt.where(Notification.organization_id == organization_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def mark_notification_as_read(
    db: Session,
    user: UserProfile,
    notification_id: uuid.UUID,
) -> Notification:
    """Marks a notification as read by the recipient."""
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != user.id:
        raise ValueError("Notification not found or access denied.")

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)
    return notif


def get_notification(
    db: Session,
    user: UserProfile,
    notification_id: uuid.UUID,
) -> Notification:
    """Retrieves an in-app notification for the recipient."""
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != user.id:
        raise ValueError("Notification not found or access denied.")
    return notif


# =========================================================================
# Task Query & Metadata Helpers (Slice 4B)
# =========================================================================

def list_tasks(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[uuid.UUID] = None,
    assigned_to_me: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> List[Task]:
    """
    Lists operational tasks within an organization that the caller is authorized to view.
    Enforces scope-based isolation (e.g. event leads only see their event, department leads only see their department).
    """
    stmt = select(Task).where(
        Task.organization_id == organization_id,
        Task.archived_at == None,
    )

    if status:
        stmt = stmt.where(Task.status == status)
    if scope_type:
        stmt = stmt.where(Task.scope_type == scope_type)
    if scope_id:
        stmt = stmt.where(Task.scope_id == scope_id)

    if assigned_to_me:
        stmt = (
            stmt.join(TaskAssignee, Task.id == TaskAssignee.task_id)
            .join(OrganizationMembership, TaskAssignee.membership_id == OrganizationMembership.id)
            .where(
                TaskAssignee.assignment_status == "active",
                OrganizationMembership.user_id == user.id,
            )
        )

    stmt = stmt.order_by(Task.due_date.asc(), Task.created_at.desc())
    candidates = list(db.execute(stmt).scalars().all())

    # Authorization filter: caller must have ACTION_VIEW_TASK on each individual task item
    authorized_tasks = [
        t for t in candidates
        if can_perform(
            db,
            user=user,
            action=ACTION_VIEW_TASK,
            organization_id=organization_id,
            scope_type="task",
            scope_id=t.id,
        )
    ]

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    return authorized_tasks[safe_offset : safe_offset + safe_limit]


def update_task(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
) -> Task:
    """Updates permitted metadata (title, description, priority) on an active operational task."""
    task = get_task(db, task_id)
    if task.status in ("completed", "cancelled"):
        raise TaskWorkflowError(f"Cannot update task in terminal status '{task.status}'.")

    require_permission(
        db,
        user=user,
        action=ACTION_UPDATE_TASK,
        organization_id=task.organization_id,
        scope_type=task.scope_type,
        scope_id=task.scope_id,
    )

    if title is not None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        task.title = clean_title

    if description is not None:
        task.description = description.strip() if description else None

    if priority is not None:
        clean_priority = priority.strip().lower()
        if clean_priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of {sorted(VALID_PRIORITIES)}.")
        task.priority = clean_priority

    now = datetime.now(timezone.utc)
    task.updated_at = now
    try:
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


def list_task_submissions(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
) -> List[EvidenceSubmission]:
    """Lists evidence submissions for an authorized task."""
    task = get_task(db, task_id, user=user)
    return list(task.submissions)


def get_task_history(
    db: Session,
    user: UserProfile,
    task_id: uuid.UUID,
) -> Dict[str, Any]:
    """Retrieves full status history, deadline history, and assignment history for a task."""
    task = get_task(db, task_id, user=user)
    return {
        "status_history": list(task.status_history),
        "deadline_history": list(task.deadline_history),
        "assignees": list(task.assignees),
    }


# =========================================================================
# Operational Blocker Query Helpers (Slice 4B)
# =========================================================================

def list_operational_blockers(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[uuid.UUID] = None,
    task_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OperationalBlocker]:
    """Lists internal operational blockers within the caller's authorized scope."""
    stmt = select(OperationalBlocker).where(
        OperationalBlocker.organization_id == organization_id,
    )

    if status:
        stmt = stmt.where(OperationalBlocker.status == status)
    if scope_type:
        stmt = stmt.where(OperationalBlocker.scope_type == scope_type)
    if scope_id:
        stmt = stmt.where(OperationalBlocker.scope_id == scope_id)
    if task_id:
        stmt = stmt.where(OperationalBlocker.task_id == task_id)

    stmt = stmt.order_by(OperationalBlocker.created_at.desc())
    candidates = list(db.execute(stmt).scalars().all())

    authorized_blockers = [
        b for b in candidates
        if can_perform(
            db,
            user=user,
            action=ACTION_VIEW_BLOCKER,
            organization_id=organization_id,
            scope_type=b.scope_type,
            scope_id=b.scope_id,
        )
    ]

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    return authorized_blockers[safe_offset : safe_offset + safe_limit]


def update_operational_blocker(
    db: Session,
    user: UserProfile,
    blocker_id: uuid.UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    owner_membership_id: Optional[uuid.UUID] = None,
) -> OperationalBlocker:
    """Updates permitted fields on an open/in_progress operational blocker."""
    blocker = get_operational_blocker(db, blocker_id)
    if blocker.status in ("resolved", "wont_fix"):
        raise OperationalBlockerError(f"Cannot update blocker in closed status '{blocker.status}'. Reopen it first.")

    require_permission(
        db,
        user=user,
        action=ACTION_CREATE_BLOCKER,
        organization_id=blocker.organization_id,
        scope_type=blocker.scope_type,
        scope_id=blocker.scope_id,
    )

    if title is not None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Blocker title cannot be empty.")
        blocker.title = clean_title

    if description is not None:
        clean_desc = description.strip()
        if not clean_desc:
            raise ValueError("Blocker description cannot be empty.")
        blocker.description = clean_desc

    if priority is not None:
        clean_priority = priority.strip().lower()
        if clean_priority not in VALID_BLOCKER_PRIORITIES:
            raise ValueError(f"Invalid blocker priority '{priority}'. Must be one of {sorted(VALID_BLOCKER_PRIORITIES)}.")
        blocker.priority = clean_priority

    if owner_membership_id is not None:
        owner_mb = db.get(OrganizationMembership, owner_membership_id)
        if not owner_mb or owner_mb.organization_id != blocker.organization_id or owner_mb.membership_status != "active":
            raise ScopeIntegrityError("Blocker owner must hold an active membership in the same organization.")
        blocker.owner_membership_id = owner_membership_id

    now = datetime.now(timezone.utc)
    blocker.updated_at = now
    try:
        db.commit()
        db.refresh(blocker)
        return blocker
    except Exception:
        db.rollback()
        raise

