from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.user import UserProfile
from app.schemas.blocker import (
    OperationalBlockerCreateRequest,
    OperationalBlockerDetailResponse,
    OperationalBlockerReopenRequest,
    OperationalBlockerResolveRequest,
    OperationalBlockerResponse,
    OperationalBlockerUpdateRequest,
)
from app.services.errors import (
    OperationalBlockerError,
    OperationalBlockerNotFoundError,
    PermissionDeniedError,
    ScopeIntegrityError,
)
from app.services.platform import is_active_platform_admin
from app.services.task import (
    create_operational_blocker,
    get_operational_blocker,
    list_operational_blockers,
    reopen_operational_blocker,
    resolve_operational_blocker,
    update_operational_blocker,
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


@router.post(
    "/organizations/{organization_id}/blockers",
    response_model=OperationalBlockerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_blocker(
    organization_id: uuid.UUID,
    payload: OperationalBlockerCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationalBlockerResponse:
    """Creates a staff-only internal operational blocker."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return create_operational_blocker(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            title=payload.title,
            description=payload.description,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            task_id=payload.task_id,
            event_id=payload.event_id,
            priority=payload.priority,
            owner_membership_id=payload.owner_membership_id,
        )
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ScopeIntegrityError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/organizations/{organization_id}/blockers",
    response_model=List[OperationalBlockerResponse],
)
def list_organization_blockers(
    organization_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[uuid.UUID] = Query(None),
    task_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OperationalBlockerResponse]:
    """Lists operational blockers within the caller's authorized scope."""
    _ensure_org_access(db, current_user, organization_id)
    return list_operational_blockers(
        db=db,
        user=current_user,
        organization_id=organization_id,
        status=status_filter,
        scope_type=scope_type,
        scope_id=scope_id,
        task_id=task_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/organizations/{organization_id}/blockers/{blocker_id}",
    response_model=OperationalBlockerDetailResponse,
)
def get_organization_blocker(
    organization_id: uuid.UUID,
    blocker_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationalBlockerDetailResponse:
    """Retrieves an operational blocker with its audit history."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_operational_blocker(
            db=db,
            blocker_id=blocker_id,
            user=current_user,
            organization_id=organization_id,
        )
    except (OperationalBlockerNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocker not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch(
    "/organizations/{organization_id}/blockers/{blocker_id}",
    response_model=OperationalBlockerResponse,
)
def update_organization_blocker(
    organization_id: uuid.UUID,
    blocker_id: uuid.UUID,
    payload: OperationalBlockerUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationalBlockerResponse:
    """Updates permitted metadata on an open operational blocker."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return update_operational_blocker(
            db=db,
            user=current_user,
            blocker_id=blocker_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            owner_membership_id=payload.owner_membership_id,
        )
    except (OperationalBlockerNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocker not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OperationalBlockerError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/blockers/{blocker_id}/resolve",
    response_model=OperationalBlockerResponse,
)
def resolve_organization_blocker(
    organization_id: uuid.UUID,
    blocker_id: uuid.UUID,
    payload: OperationalBlockerResolveRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationalBlockerResponse:
    """Resolves an operational blocker with mandatory resolution note."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return resolve_operational_blocker(
            db=db,
            user=current_user,
            blocker_id=blocker_id,
            resolution_note=payload.resolution_note,
            status=payload.status,
        )
    except (OperationalBlockerNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocker not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OperationalBlockerError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/organizations/{organization_id}/blockers/{blocker_id}/reopen",
    response_model=OperationalBlockerResponse,
)
def reopen_organization_blocker(
    organization_id: uuid.UUID,
    blocker_id: uuid.UUID,
    payload: OperationalBlockerReopenRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperationalBlockerResponse:
    """Reopens a resolved or wont_fix operational blocker."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return reopen_operational_blocker(
            db=db,
            user=current_user,
            blocker_id=blocker_id,
            reason=payload.reason,
        )
    except (OperationalBlockerNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocker not found.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (OperationalBlockerError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

