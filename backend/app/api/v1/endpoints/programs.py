from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization
from app.models.user import UserProfile
from app.schemas.department import DepartmentResponse
from app.schemas.event import EventCreateRequest, EventResponse
from app.schemas.program import (
    ProgramCreateRequest,
    ProgramResponse,
    ProgramUpdateRequest,
)
from app.services.errors import (
    EventNotFoundError,
    PermissionDeniedError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.event import (
    archive_program,
    create_event,
    create_program,
    get_program,
    list_departments,
    list_events,
    list_programs,
    update_program,
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
    # Check caller membership
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
    "/organizations/{organization_id}/programs",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org_program(
    organization_id: uuid.UUID,
    payload: ProgramCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramResponse:
    """Creates a multi-event program umbrella within an organization workspace."""
    _ensure_org_access(db, current_user, organization_id)

    try:
        program = create_program(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            planned_start_date=payload.planned_start_date,
            planned_end_date=payload.planned_end_date,
        )
        return program
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/organizations/{organization_id}/programs",
    response_model=List[ProgramResponse],
)
def list_org_programs(
    organization_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ProgramResponse]:
    """Lists active programs for the organization."""
    _ensure_org_access(db, current_user, organization_id)
    return list_programs(db, organization_id=organization_id)


@router.get(
    "/organizations/{organization_id}/programs/{program_id}",
    response_model=ProgramResponse,
)
def get_org_program(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramResponse:
    """Retrieves program details."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_program(db, program_id=program_id, organization_id=organization_id)
    except (ProgramNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")


@router.patch(
    "/organizations/{organization_id}/programs/{program_id}",
    response_model=ProgramResponse,
)
def update_org_program(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    payload: ProgramUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramResponse:
    """Updates program metadata or date ranges."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return update_program(
            db=db,
            user=current_user,
            organization_id=organization_id,
            program_id=program_id,
            name=payload.name,
            description=payload.description,
            planned_start_date=payload.planned_start_date,
            planned_end_date=payload.planned_end_date,
        )
    except (ProgramNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/organizations/{organization_id}/programs/{program_id}/archive",
    response_model=ProgramResponse,
)
def archive_org_program(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramResponse:
    """Non-destructively archives a program."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_program(db, program_id=program_id, organization_id=organization_id)
        return archive_program(db=db, user=current_user, program_id=program_id)
    except (ProgramNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))


@router.get(
    "/organizations/{organization_id}/programs/{program_id}/events",
    response_model=List[EventResponse],
)
def list_program_child_events(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EventResponse]:
    """Lists child events belonging to a program."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_program(db, program_id=program_id, organization_id=organization_id)
    except (ProgramNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    return list_events(db, organization_id=organization_id, program_id=program_id)


@router.post(
    "/organizations/{organization_id}/programs/{program_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_program_child_event(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    payload: EventCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Convenience endpoint to create a child event under a program."""
    _ensure_org_access(db, current_user, organization_id)
    if payload.program_id is not None and payload.program_id != program_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload program_id must match the path program_id.",
        )
    try:
        return create_event(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            program_id=program_id,
            event_date=payload.event_date,
            event_end_date=payload.event_end_date,
            planned_start_time=payload.planned_start_time,
            planned_end_time=payload.planned_end_time,
            venue=payload.venue,
            event_format=payload.event_format,
            registration_mode=payload.registration_mode,
            timezone_name=payload.timezone,
        )
    except (ProgramNotFoundError, ScopeIntegrityError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/organizations/{organization_id}/programs/{program_id}/departments",
    response_model=List[DepartmentResponse],
)
def list_program_shared_departments(
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DepartmentResponse]:
    """Lists shared departments defined at the program level."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_program(db, program_id=program_id, organization_id=organization_id)
    except (ProgramNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found.")
    return list_departments(db, organization_id=organization_id, program_id=program_id)

