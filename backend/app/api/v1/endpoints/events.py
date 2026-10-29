from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization
from app.models.user import UserProfile
from app.schemas.department import DepartmentResponse
from app.schemas.event import (
    EventCreateRequest,
    EventLeadAssignRequest,
    EventLeadResponse,
    EventResponse,
    EventUpdateRequest,
)
from app.services.errors import (
    DuplicateEventLeadError,
    EventLeadError,
    EventNotFoundError,
    PermissionDeniedError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.event import (
    archive_event,
    assign_event_lead,
    create_event,
    get_active_event_leads,
    get_event,
    list_departments,
    list_events,
    revoke_event_lead,
    update_event,
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
    "/organizations/{organization_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org_event(
    organization_id: uuid.UUID,
    payload: EventCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Creates a standalone event or child event within a verified organization."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return create_event(
            db=db,
            creator=current_user,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            program_id=payload.program_id,
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
    "/organizations/{organization_id}/events",
    response_model=List[EventResponse],
)
def list_org_events(
    organization_id: uuid.UUID,
    program_id: Optional[uuid.UUID] = Query(None),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EventResponse]:
    """Lists events for an organization, optionally filtered by parent program."""
    _ensure_org_access(db, current_user, organization_id)
    return list_events(db, organization_id=organization_id, program_id=program_id)


@router.get(
    "/organizations/{organization_id}/events/{event_id}",
    response_model=EventResponse,
)
def get_org_event(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Retrieves details of a specific event."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_event(db, event_id=event_id, organization_id=organization_id)
    except (EventNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")


@router.patch(
    "/organizations/{organization_id}/events/{event_id}",
    response_model=EventResponse,
)
def update_org_event(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: EventUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Updates event details (timing, venue, format). Parentage is immutable."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return update_event(
            db=db,
            user=current_user,
            organization_id=organization_id,
            event_id=event_id,
            name=payload.name,
            description=payload.description,
            venue=payload.venue,
            event_format=payload.event_format,
            registration_mode=payload.registration_mode,
            timezone_name=payload.timezone,
            event_date=payload.event_date,
            event_end_date=payload.event_end_date,
            planned_start_time=payload.planned_start_time,
            planned_end_time=payload.planned_end_time,
        )
    except (EventNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/organizations/{organization_id}/events/{event_id}/archive",
    response_model=EventResponse,
)
def archive_org_event(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Non-destructively archives an event (D-SLICE3-04)."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_event(db, event_id=event_id, organization_id=organization_id)
        return archive_event(db=db, user=current_user, event_id=event_id)
    except (EventNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))


@router.get(
    "/organizations/{organization_id}/events/{event_id}/departments",
    response_model=List[DepartmentResponse],
)
def list_standalone_event_departments(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DepartmentResponse]:
    """Lists departments for a standalone event."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        ev = get_event(db, event_id=event_id, organization_id=organization_id)
        if ev.program_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Child events in a multi-event program share program departments and do not have standalone departments.",
            )
    except (EventNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return list_departments(db, organization_id=organization_id, standalone_event_id=event_id)


# =========================================================================
# Event Lead Assignment Endpoints (Section 7)
# =========================================================================


@router.get(
    "/organizations/{organization_id}/events/{event_id}/leads",
    response_model=List[EventLeadResponse],
)
def list_event_leads(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EventLeadResponse]:
    """Lists currently active Event Lead assignments for an event."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return get_active_event_leads(db=db, event_id=event_id, organization_id=organization_id)
    except (EventNotFoundError, ScopeIntegrityError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")


@router.post(
    "/organizations/{organization_id}/events/{event_id}/leads",
    response_model=EventLeadResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_lead_to_event(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: EventLeadAssignRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventLeadResponse:
    """Assigns an eligible workspace member as an Event Lead for an event."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        return assign_event_lead(
            db=db,
            assigner=current_user,
            organization_id=organization_id,
            event_id=event_id,
            membership_id=payload.membership_id,
        )
    except (EventNotFoundError, ScopeIntegrityError) as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except DuplicateEventLeadError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))
    except EventLeadError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))


@router.post(
    "/organizations/{organization_id}/events/{event_id}/leads/{assignment_id}/revoke",
    response_model=EventLeadResponse,
)
def revoke_lead_from_event(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventLeadResponse:
    """Revokes an active Event Lead assignment with audit trail."""
    _ensure_org_access(db, current_user, organization_id)
    try:
        get_event(db, event_id=event_id, organization_id=organization_id)
        return revoke_event_lead(
            db=db,
            revoker=current_user,
            organization_id=organization_id,
            assignment_id=assignment_id,
            event_id=event_id,
        )
    except (EventNotFoundError, ScopeIntegrityError) as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except EventLeadError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except PermissionDeniedError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

