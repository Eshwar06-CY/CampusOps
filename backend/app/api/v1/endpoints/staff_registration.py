from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.event import Event, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.registration import (
    CheckIn,
    EventRegistrationSettings,
    Participant,
    Registration,
    RegistrationParticipant,
    Ticket,
)
from app.models.user import UserProfile
from app.schemas.registration import (
    AttendanceSummaryResponse,
    CheckInLookupItemResponse,
    CheckInRequest,
    CheckInResponse,
    CheckInVoidRequest,
    CheckInVoidResponse,
    EventRegistrationSettingsResponse,
    EventRegistrationSettingsUpdateRequest,
    IssuedPassResponse,
    PublicRegistrationRequest,
    PublicRegistrationResponse,
    StaffCancelRegistrationRequest,
    StaffParticipantDetailResponse,
    StaffParticipantRosterItemResponse,
    StaffParticipantUpdateRequest,
    StaffRegistrationSummaryResponse,
    StaffReissuePassRequest,
)
from app.services.errors import (
    AlreadyCheckedInError,
    CapacityExhaustedError,
    CheckInCorrectionError,
    CheckInError,
    CheckInNotFoundError,
    DuplicateRegistrationError,
    EventNotFoundError,
    IdempotencyConflictError,
    InvalidTeamSizeError,
    PermissionDeniedError,
    RegistrationClosedError,
    RegistrationError,
    RegistrationNotFoundError,
    RegistrationWindowError,
    ScopeIntegrityError,
    TicketError,
    TicketInvalidError,
    TicketNotFoundError,
    TicketRevokedError,
)
from app.services.permissions import (
    ACTION_CHECK_IN,
    ACTION_CORRECT_CHECK_IN,
    ACTION_EXPORT_PARTICIPANTS,
    ACTION_MANAGE_REGISTRATION_SETTINGS,
    ACTION_VIEW_ATTENDEE_CONTACT,
    ACTION_VIEW_REGISTRATIONS,
    can_perform,
    is_active_platform_admin,
    require_permission,
)
from app.services.registration import (
    cancel_registration,
    check_in_participant,
    correct_or_void_check_in,
    create_individual_registration,
    create_team_registration,
    export_event_roster_csv,
    get_event_attendance_summary,
    get_or_create_registration_settings,
    get_participant_detail,
    issue_replacement_ticket,
    list_event_participants,
    list_event_registrations,
    lookup_for_check_in,
    update_participant,
    update_registration_settings,
)

router = APIRouter()


def _ensure_org_and_event(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Tuple[Organization, Event]:
    """Ensures organization and event exist, are active, and caller belongs to organization."""
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
        OrganizationMembership.removed_at.is_(None),
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if not membership and not is_active_platform_admin(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    event = db.get(Event, event_id)
    if not event or event.organization_id != organization_id or event.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found in this organization.",
        )

    if event.program_id is not None:
        prog = db.get(Program, event.program_id)
        if prog and prog.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent program has been archived.",
            )

    return org, event


# =========================================================================
# 1. Staff Settings & Capacity Management
# =========================================================================

@router.get(
    "/organizations/{organization_id}/events/{event_id}/registration-settings",
    response_model=EventRegistrationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get registration settings and capacity parameters for an event",
)
def get_staff_registration_settings(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> EventRegistrationSettingsResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        require_permission(
            db,
            current_user,
            ACTION_VIEW_REGISTRATIONS,
            organization_id=organization_id,
            scope_type="event",
            scope_id=event_id,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view registration settings.",
        )

    settings = get_or_create_registration_settings(db, organization_id, event_id)

    return EventRegistrationSettingsResponse(
        event_id=settings.event_id,
        organization_id=settings.organization_id,
        is_open=settings.is_open,
        registration_format=settings.registration_format,
        capacity_limit=settings.capacity_limit,
        current_confirmed_count=settings.current_confirmed_count,
        current_attended_count=settings.current_attended_count,
        waitlist_enabled=settings.waitlist_enabled,
        team_size_min=settings.team_size_min,
        team_size_max=settings.team_size_max,
        registration_open_at=settings.registration_open_at,
        registration_close_at=settings.registration_close_at,
        has_registration_key=bool(settings.registration_key_hash),
        has_access_code=bool(settings.access_code_hash),
        public_registration_key=None,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.put(
    "/organizations/{organization_id}/events/{event_id}/registration-settings",
    response_model=EventRegistrationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update event registration settings and capacity rules",
)
def update_staff_registration_settings(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: EventRegistrationSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> EventRegistrationSettingsResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        with db.begin_nested():
            settings = update_registration_settings(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                actor_user=current_user,
                is_open=payload.is_open,
                registration_format=payload.registration_format,
                capacity_limit=payload.capacity_limit,
                waitlist_enabled=payload.waitlist_enabled,
                team_size_min=payload.team_size_min,
                team_size_max=payload.team_size_max,
                registration_open_at=payload.registration_open_at,
                registration_close_at=payload.registration_close_at,
                access_code=payload.access_code,
                registration_key=payload.registration_key,
                rotate_registration_key=payload.rotate_registration_key,
            )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage registration settings.",
        )
    except (RegistrationError, InvalidTeamSizeError, RegistrationClosedError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    transient_key = getattr(settings, "_transient_registration_key", None)
    return EventRegistrationSettingsResponse(
        event_id=settings.event_id,
        organization_id=settings.organization_id,
        is_open=settings.is_open,
        registration_format=settings.registration_format,
        capacity_limit=settings.capacity_limit,
        current_confirmed_count=settings.current_confirmed_count,
        current_attended_count=settings.current_attended_count,
        waitlist_enabled=settings.waitlist_enabled,
        team_size_min=settings.team_size_min,
        team_size_max=settings.team_size_max,
        registration_open_at=settings.registration_open_at,
        registration_close_at=settings.registration_close_at,
        has_registration_key=bool(settings.registration_key_hash),
        has_access_code=bool(settings.access_code_hash),
        public_registration_key=transient_key or (payload.registration_key if payload.registration_key else None),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


# =========================================================================
# 2. Staff Registration Listing, Walk-Ins & Cancellations
# =========================================================================

@router.get(
    "/organizations/{organization_id}/events/{event_id}/registrations",
    response_model=List[StaffRegistrationSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List registration transactions for an event",
)
def list_registrations(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    registration_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> List[StaffRegistrationSummaryResponse]:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        items = list_event_registrations(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user=current_user,
            status=status_filter,
            registration_type=registration_type,
            limit=limit,
            offset=offset,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view registrations.",
        )

    return [StaffRegistrationSummaryResponse(**item) for item in items]


@router.post(
    "/organizations/{organization_id}/events/{event_id}/registrations/walk-in",
    response_model=PublicRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff-assisted walk-in registration at the event desk",
)
def create_walk_in_registration(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: PublicRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> PublicRegistrationResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        require_permission(
            db,
            current_user,
            ACTION_CHECK_IN,
            organization_id=organization_id,
            scope_type="event",
            scope_id=event_id,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create walk-in registrations.",
        )

    try:
        with db.begin_nested():
            if payload.registration_type == "individual":
                if len(payload.participants) != 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Individual walk-in registration must contain exactly one participant.",
                    )
                p = payload.participants[0]
                result = create_individual_registration(
                    db=db,
                    organization_id=organization_id,
                    event_id=event_id,
                    full_name=p.full_name,
                    email=p.email,
                    phone_number=p.phone_number or payload.contact_phone,
                    college_name=p.college_name,
                    student_id=p.student_id,
                    custom_answers=p.custom_answers,
                    idempotency_key=payload.idempotency_key,
                    access_code=payload.access_code,
                    channel="walk_in",
                )
            elif payload.registration_type == "team":
                if not payload.team_name or not payload.team_name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="team_name is required for team walk-in registration.",
                    )
                members_data = [
                    {
                        "full_name": m.full_name,
                        "email": m.email,
                        "phone_number": m.phone_number,
                        "college_name": m.college_name,
                        "student_id": m.student_id,
                        "custom_answers": m.custom_answers,
                        "is_primary_contact": m.is_primary_contact,
                        "team_role": m.team_role,
                    }
                    for m in payload.participants
                ]
                result = create_team_registration(
                    db=db,
                    organization_id=organization_id,
                    event_id=event_id,
                    team_name=payload.team_name,
                    members=members_data,
                    contact_email=payload.contact_email,
                    contact_phone=payload.contact_phone,
                    idempotency_key=payload.idempotency_key,
                    access_code=payload.access_code,
                    channel="walk_in",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported registration type: {payload.registration_type}",
                )

        part_by_id = {p.id: p for p in result.participants}
        passes = []
        for dto in result.issued_tickets:
            part = part_by_id.get(dto.ticket.participant_id)
            part_name = part.full_name if part else "Attendee"
            passes.append(
                IssuedPassResponse(
                    participant_id=dto.ticket.participant_id,
                    participant_name=part_name,
                    ticket_reference=dto.ticket.ticket_reference,
                    pass_code=dto.raw_pass_token,
                    pass_url=None,
                )
            )

        return PublicRegistrationResponse(
            registration_id=result.registration.id,
            confirmation_code=result.registration.confirmation_code,
            registration_status=result.registration.registration_status,
            registration_type=result.registration.registration_type,
            team_name=result.registration.team_name,
            is_waitlisted=result.is_waitlisted,
            passes=passes,
        )

    except HTTPException:
        raise
    except IdempotencyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except (CapacityExhaustedError, RegistrationClosedError, RegistrationWindowError, DuplicateRegistrationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InvalidTeamSizeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except (RegistrationError, ScopeIntegrityError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/organizations/{organization_id}/events/{event_id}/registrations/{registration_id}/cancel",
    response_model=StaffRegistrationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a registration transaction and release capacity",
)
def cancel_staff_registration(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    registration_id: uuid.UUID,
    payload: StaffCancelRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> StaffRegistrationSummaryResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        require_permission(
            db,
            current_user,
            ACTION_MANAGE_REGISTRATION_SETTINGS,
            organization_id=organization_id,
            scope_type="event",
            scope_id=event_id,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel registrations.",
        )

    try:
        with db.begin_nested():
            reg = cancel_registration(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                registration_id=registration_id,
                reason=payload.cancellation_reason,
                actor_user=current_user,
            )
    except RegistrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found.",
        )
    except RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    p_count = db.execute(
        select(func.count(RegistrationParticipant.id)).where(
            RegistrationParticipant.registration_id == reg.id
        )
    ).scalar() or 0

    return StaffRegistrationSummaryResponse(
        id=reg.id,
        registration_type=reg.registration_type,
        registration_status=reg.registration_status,
        registration_channel=reg.registration_channel,
        team_name=reg.team_name,
        contact_email=reg.contact_email,
        contact_phone=reg.contact_phone,
        confirmation_code=reg.confirmation_code,
        participant_count=p_count,
        created_at=reg.created_at,
        cancelled_at=reg.cancelled_at,
    )


# =========================================================================
# 3. Staff Roster & Attendee Participant Management
# =========================================================================

@router.get(
    "/organizations/{organization_id}/events/{event_id}/participants",
    response_model=List[StaffParticipantRosterItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List attendee roster records with tiered privacy masking",
)
def list_participants(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> List[StaffParticipantRosterItemResponse]:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        items = list_event_participants(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user=current_user,
            search=search,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view attendee roster.",
        )

    return [StaffParticipantRosterItemResponse(**item) for item in items]


@router.get(
    "/organizations/{organization_id}/events/{event_id}/participants/{participant_id}",
    response_model=StaffParticipantDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed attendee record and ticket pass history",
)
def get_participant(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> StaffParticipantDetailResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        data = get_participant_detail(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            participant_id=participant_id,
            actor_user=current_user,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view attendee details.",
        )
    except ScopeIntegrityError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found in this event.",
        )

    return StaffParticipantDetailResponse(**data)


@router.patch(
    "/organizations/{organization_id}/events/{event_id}/participants/{participant_id}",
    response_model=StaffParticipantDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update attendee details (name, college, student ID)",
)
def patch_participant(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    payload: StaffParticipantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> StaffParticipantDetailResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        with db.begin_nested():
            update_participant(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                participant_id=participant_id,
                actor_user=current_user,
                full_name=payload.full_name,
                college_name=payload.college_name,
                student_id=payload.student_id,
                phone_number=payload.phone_number,
            )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update attendee records.",
        )
    except ScopeIntegrityError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found in this event.",
        )
    except RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    data = get_participant_detail(
        db=db,
        organization_id=organization_id,
        event_id=event_id,
        participant_id=participant_id,
        actor_user=current_user,
    )
    return StaffParticipantDetailResponse(**data)


@router.post(
    "/organizations/{organization_id}/events/{event_id}/participants/{participant_id}/reissue-pass",
    response_model=IssuedPassResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke existing admission pass and issue a fresh pass credential",
)
def reissue_pass(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    payload: StaffReissuePassRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> IssuedPassResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        with db.begin_nested():
            dto = issue_replacement_ticket(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                participant_id=participant_id,
                actor_user=current_user,
                reason=payload.reason,
            )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reissue admission passes.",
        )
    except ScopeIntegrityError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found in this event.",
        )
    except (TicketError, TicketInvalidError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    part = dto.ticket.participant
    part_name = part.full_name if part else "Attendee"

    return IssuedPassResponse(
        participant_id=dto.ticket.participant_id,
        participant_name=part_name,
        ticket_reference=dto.ticket.ticket_reference,
        pass_code=dto.raw_pass_token,
        pass_url=None,
    )


# =========================================================================
# 4. Staff Attendance Check-In, Lookup & Corrections
# =========================================================================

@router.post(
    "/organizations/{organization_id}/events/{event_id}/check-ins",
    response_model=CheckInResponse,
    status_code=status.HTTP_200_OK,
    summary="Record verified attendee check-in via QR scan or manual search",
)
def check_in_attendee(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> CheckInResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        with db.begin_nested():
            ci, is_duplicate = check_in_participant(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                actor_user=current_user,
                raw_token=payload.pass_code,
                participant_id=payload.participant_id,
                station_id=payload.station_id,
                method=payload.method,
            )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to check in attendees.",
        )
    except (TicketNotFoundError, CheckInNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission pass or participant not found.",
        )
    except ScopeIntegrityError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant does not belong to this event.",
        )
    except (TicketRevokedError, TicketInvalidError, CheckInError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    part = ci.participant
    part_name = part.full_name if part else "Attendee"

    reg_part = db.execute(
        select(RegistrationParticipant, Registration)
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .where(RegistrationParticipant.participant_id == ci.participant_id)
    ).first()
    team_name = reg_part[1].team_name if reg_part else None

    msg = (
        f"Attendee was already checked in at {ci.checked_in_at.strftime('%H:%M:%S')}."
        if is_duplicate
        else "Check-in verified successfully."
    )

    return CheckInResponse(
        check_in_id=ci.id,
        status="already_checked_in" if is_duplicate else "verified",
        participant_id=ci.participant_id,
        participant_name=part_name,
        team_name=team_name,
        checked_in_at=ci.checked_in_at,
        station_id=ci.station_id,
        message=msg,
    )


@router.get(
    "/organizations/{organization_id}/events/{event_id}/check-in-lookup",
    response_model=List[CheckInLookupItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Search attendee roster for desk verification and manual check-in",
)
def lookup_check_in(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> List[CheckInLookupItemResponse]:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        items = lookup_for_check_in(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user=current_user,
            query_str=q,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to search attendee check-in records.",
        )

    return [CheckInLookupItemResponse(**item) for item in items]


@router.post(
    "/organizations/{organization_id}/events/{event_id}/check-ins/{check_in_id}/void",
    response_model=CheckInVoidResponse,
    status_code=status.HTTP_200_OK,
    summary="Manager-authorized void/correction of an accidental check-in",
)
def void_check_in(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    check_in_id: uuid.UUID,
    payload: CheckInVoidRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> CheckInVoidResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        with db.begin_nested():
            ci, correction = correct_or_void_check_in(
                db=db,
                organization_id=organization_id,
                event_id=event_id,
                check_in_id=check_in_id,
                reason=payload.reason,
                actor_user=current_user,
            )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to void check-ins. Managerial authority required.",
        )
    except CheckInNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in record not found.",
        )
    except CheckInCorrectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return CheckInVoidResponse(
        check_in_id=ci.id,
        check_in_status=ci.check_in_status,
        voided_at=ci.voided_at or datetime.now(timezone.utc),
        reason=correction.reason,
    )


# =========================================================================
# 5. Staff Attendance Reporting & CSV Export
# =========================================================================

@router.get(
    "/organizations/{organization_id}/events/{event_id}/attendance-summary",
    response_model=AttendanceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real-time operational attendance metrics and team stats",
)
def get_attendance_summary(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> AttendanceSummaryResponse:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        data = get_event_attendance_summary(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user=current_user,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view attendance summaries.",
        )

    return AttendanceSummaryResponse(**data)


@router.get(
    "/organizations/{organization_id}/events/{event_id}/roster-export",
    status_code=status.HTTP_200_OK,
    summary="Export normalized participant and attendance roster as CSV",
)
def export_roster(
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    org, event = _ensure_org_and_event(db, current_user, organization_id, event_id)

    try:
        csv_content = export_event_roster_csv(
            db=db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user=current_user,
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export attendee roster.",
        )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="roster_{event_id}.csv"'
        },
    )
