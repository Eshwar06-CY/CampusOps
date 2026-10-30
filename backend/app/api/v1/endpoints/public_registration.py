from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.registration import (
    IssuedPassResponse,
    PublicEventRegistrationResponse,
    PublicPassDisplayResponse,
    PublicPassVerifyRequest,
    PublicRegistrationCancelBodyRequest,
    PublicRegistrationCancelResponse,
    PublicRegistrationLookupRequest,
    PublicRegistrationRequest,
    PublicRegistrationResponse,
    PublicRegistrationStatusResponse,
)
from app.services.errors import (
    CapacityExhaustedError,
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
from app.services.registration import (
    cancel_public_registration,
    create_individual_registration,
    create_team_registration,
    ensure_utc,
    get_public_event_by_registration_key,
    get_public_registration_status,
    verify_ticket_pass,
)

router = APIRouter()


@router.get(
    "/public/events/{registration_key}",
    response_model=PublicEventRegistrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public event registration details and availability",
)
def get_public_event_registration(
    registration_key: str,
    db: Session = Depends(get_db),
) -> PublicEventRegistrationResponse:
    """Public endpoint to discover event details, registration format, and capacity availability."""
    try:
        event, settings = get_public_event_by_registration_key(db, registration_key)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or registration key invalid.",
        )

    now = datetime.now(timezone.utc)
    open_at = ensure_utc(settings.registration_open_at)
    close_at = ensure_utc(settings.registration_close_at)

    if not settings.is_open:
        reg_status = "closed"
    elif open_at and now < open_at:
        reg_status = "not_yet_open"
    elif close_at and now > close_at:
        reg_status = "ended"
    else:
        reg_status = "open"

    capacity_avail = (
        settings.capacity_limit is None
        or settings.current_confirmed_count < settings.capacity_limit
    )

    return PublicEventRegistrationResponse(
        public_registration_key=registration_key,
        event_id=event.id,
        event_name=event.name,
        description=event.description,
        event_date=event.event_date.isoformat() if hasattr(event.event_date, "isoformat") else str(event.event_date),
        event_end_date=event.event_end_date.isoformat() if event.event_end_date and hasattr(event.event_end_date, "isoformat") else (str(event.event_end_date) if event.event_end_date else None),
        venue=event.venue,
        timezone=event.timezone,
        registration_status=reg_status,
        registration_format=settings.registration_format,
        team_size_min=settings.team_size_min,
        team_size_max=settings.team_size_max,
        capacity_available=capacity_avail,
    )


@router.post(
    "/public/events/{registration_key}/registrations",
    response_model=PublicRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a public native registration (individual or team)",
)
def submit_public_registration(
    registration_key: str,
    payload: PublicRegistrationRequest,
    db: Session = Depends(get_db),
) -> PublicRegistrationResponse:
    """
    Submits a native self-service attendee registration.
    Issues cryptographically unguessable digital admission passes for every confirmed participant.
    """
    try:
        event, settings = get_public_event_by_registration_key(db, registration_key)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or registration key invalid.",
        )

    try:
        with db.begin_nested():
            if payload.registration_type == "individual":
                if len(payload.participants) != 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Individual registration must contain exactly one participant.",
                    )
                p = payload.participants[0]
                result = create_individual_registration(
                    db=db,
                    organization_id=event.organization_id,
                    event_id=event.id,
                    full_name=p.full_name,
                    email=p.email,
                    phone_number=p.phone_number or payload.contact_phone,
                    college_name=p.college_name,
                    student_id=p.student_id,
                    custom_answers=p.custom_answers,
                    idempotency_key=payload.idempotency_key,
                    access_code=payload.access_code,
                    channel="native_web",
                )
            elif payload.registration_type == "team":
                if not payload.team_name or not payload.team_name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="team_name is required for team registration.",
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
                    organization_id=event.organization_id,
                    event_id=event.id,
                    team_name=payload.team_name,
                    members=members_data,
                    contact_email=payload.contact_email,
                    contact_phone=payload.contact_phone,
                    idempotency_key=payload.idempotency_key,
                    access_code=payload.access_code,
                    channel="native_web",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported registration type: {payload.registration_type}",
                )

        # Map issued ticket DTOs to participant passes
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
    except (PermissionDeniedError, RegistrationError, ScopeIntegrityError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/public/events/{registration_key}/passes/verify",
    response_model=PublicPassDisplayResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify an attendee digital admission pass via request body (prevents URL token leakage)",
)
def verify_public_pass(
    registration_key: str,
    payload: PublicPassVerifyRequest,
    db: Session = Depends(get_db),
) -> PublicPassDisplayResponse:
    """
    Renders attendee pass details and verification payload using request body.
    Protects bearer credential token from browser history, access logs, and HTTP referer leakage.
    Ensures zero participant PII is encoded in the QR payload.
    """
    try:
        event, settings = get_public_event_by_registration_key(db, registration_key)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or registration key invalid.",
        )

    try:
        ticket, participant = verify_ticket_pass(
            db=db,
            organization_id=event.organization_id,
            event_id=event.id,
            raw_token=payload.pass_code,
        )
    except (TicketNotFoundError, TicketInvalidError, TicketRevokedError, ScopeIntegrityError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission pass not found or invalid.",
        )

    return PublicPassDisplayResponse(
        ticket_reference=ticket.ticket_reference,
        pass_code=payload.pass_code,
        event_name=event.name,
        participant_name=participant.full_name,
        status=ticket.status,
        issued_at=ticket.issued_at,
        used_at=ticket.used_at,
        qr_payload=payload.pass_code,
        instructions="Present this digital pass at the registration desk for individual check-in.",
    )


@router.post(
    "/public/events/{registration_key}/registrations/lookup",
    response_model=PublicRegistrationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check public registration status via request body (prevents URL code leakage)",
)
def lookup_public_registration(
    registration_key: str,
    payload: PublicRegistrationLookupRequest,
    db: Session = Depends(get_db),
) -> PublicRegistrationStatusResponse:
    """Status lookup using request body. Protects attendee confirmation codes from log leakage."""
    try:
        event, settings = get_public_event_by_registration_key(db, registration_key)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or registration key invalid.",
        )

    try:
        data = get_public_registration_status(db, event.id, payload.confirmation_code)
    except RegistrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found.",
        )

    return PublicRegistrationStatusResponse(**data)


@router.post(
    "/public/events/{registration_key}/registrations/cancel",
    response_model=PublicRegistrationCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Public self-service cancellation via request body (prevents URL code leakage)",
)
def cancel_public_registration_by_body(
    registration_key: str,
    payload: PublicRegistrationCancelBodyRequest,
    db: Session = Depends(get_db),
) -> PublicRegistrationCancelResponse:
    """Cancels a registration via request body, releasing capacity and invalidating issued passes."""
    try:
        event, settings = get_public_event_by_registration_key(db, registration_key)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or registration key invalid.",
        )

    try:
        with db.begin_nested():
            reg = cancel_public_registration(
                db=db,
                event_id=event.id,
                confirmation_code=payload.confirmation_code,
                contact_email=payload.contact_email,
                reason=payload.cancellation_reason,
            )
    except RegistrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found or contact email mismatch.",
        )
    except RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return PublicRegistrationCancelResponse(
        confirmation_code=reg.confirmation_code,
        registration_status=reg.registration_status,
        cancelled_at=reg.cancelled_at or datetime.now(timezone.utc),
        message="Registration successfully cancelled and admission passes invalidated.",
    )

