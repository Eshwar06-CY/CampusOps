from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization
from app.models.user import UserProfile
from app.schemas.department import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)
from app.services.errors import (
    DepartmentNotFoundError,
    EventNotFoundError,
    PermissionDeniedError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.event import (
    archive_department,
    create_department,
    get_department,
    list_departments,
    update_department,
)

router = APIRouter()


def _ensure_org_access(db: Session, user: UserProfile, organization_id: uuid.UUID) -> Organization:
    """Verifies that the organization exists and caller is an active member or platform admin."""
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    from app.models.organization import OrganizationMembership
    from sqlalchemy import select
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.membership_status == "active",
        OrganizationMembership.removed_at == None,
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if not membership:
        from app.services.platform import is_active_platform_admin
        if not is_active_platform_admin(db, user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
    return org


@router.post(
    "/organizations/{organization_id}/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org_department(
    organization_id: uuid.UUID,
    payload: DepartmentCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Creates a department for a program or standalone event (exclusive parentage)."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return create_department(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            program_id=payload.program_id,
            standalone_event_id=payload.standalone_event_id,
        )
    except (ProgramNotFoundError, EventNotFoundError, ScopeIntegrityError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/organizations/{organization_id}/departments",
    response_model=List[DepartmentResponse],
)
def list_org_departments(
    organization_id: uuid.UUID,
    program_id: Optional[uuid.UUID] = Query(None),
    standalone_event_id: Optional[uuid.UUID] = Query(None),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DepartmentResponse]:
    """Lists departments for an organization, optionally filtered by program or standalone event."""
    _ensure_org_access(db, current_user, organization_id)
    return list_departments(
        db,
        organization_id=organization_id,
        program_id=program_id,
        standalone_event_id=standalone_event_id,
    )


@router.get(
    "/organizations/{organization_id}/departments/{department_id}",
    response_model=DepartmentResponse,
)
def get_org_department(
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Retrieves department details."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_department(db, department_id=department_id, organization_id=organization_id)
    except (DepartmentNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")


@router.patch(
    "/organizations/{organization_id}/departments/{department_id}",
    response_model=DepartmentResponse,
)
def update_org_department(
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Updates department name or description."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return update_department(
            db=db,
            user=current_user,
            organization_id=organization_id,
            department_id=department_id,
            name=payload.name,
            description=payload.description,
        )
    except (DepartmentNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/organizations/{organization_id}/departments/{department_id}/archive",
    response_model=DepartmentResponse,
)
def archive_org_department(
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Non-destructively archives a department."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_department(db, department_id=department_id, organization_id=organization_id)
        return archive_department(db=db, user=current_user, department_id=department_id)
    except (DepartmentNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

