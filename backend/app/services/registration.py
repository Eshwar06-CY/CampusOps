import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.organization import Organization
from app.models.registration import (
    CheckIn,
    CheckInCorrection,
    EventRegistrationSettings,
    Participant,
    Registration,
    RegistrationParticipant,
    Ticket,
)
from app.models.user import UserProfile
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
    require_permission,
)


@dataclass(frozen=True)
class IssuedTicketDTO:
    """Carries a newly issued Ticket along with its raw, high-entropy admission pass token."""
    ticket: Ticket
    raw_pass_token: str


@dataclass(frozen=True)
class RegistrationResultDTO:
    """Outcome of a successful individual or team registration submission."""
    registration: Registration
    participants: List[Participant]
    issued_tickets: List[IssuedTicketDTO]
    is_waitlisted: bool


# =========================================================================
# Security, Credential & Masking Helpers
# =========================================================================

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures a datetime has UTC tzinfo, normalizing offset-naive datetimes from SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def generate_ticket_credential() -> Tuple[str, str]:
    """
    Generates a cryptographically unguessable raw admission pass token and its SHA-256 digest.
    Raw token format: CO-PASS-<32-hex-random>
    Returns: (raw_pass_token, pass_code_hash)
    """
    token = f"CO-PASS-{secrets.token_hex(16).upper()}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def generate_registration_key() -> Tuple[str, str]:
    """
    Generates a cryptographically unguessable public registration key slug and its SHA-256 digest.
    Raw key format: reg_<32-hex-random>
    Returns: (raw_key, key_hash)
    """
    raw_key = f"reg_{secrets.token_hex(16)}"
    key_hash = hash_credential(raw_key)
    return raw_key, key_hash


def hash_credential(secret: str) -> str:
    """Computes a SHA-256 digest of an access code or registration key."""
    return hashlib.sha256(secret.strip().encode("utf-8")).hexdigest()


def generate_confirmation_code() -> str:
    """Generates an alphanumeric confirmation reference for registrant lookup."""
    return f"REG-{secrets.token_hex(4).upper()}"


def generate_ticket_reference() -> str:
    """Generates a short human-readable non-secret ticket reference serial."""
    return f"TKT-{secrets.token_hex(4).upper()}"


def mask_email(email: str) -> str:
    """Masks an email address for privacy: e.g. 'aarav.sharma@example.com' -> 'a***a@example.com'."""
    if not email or "@" not in email:
        return "***"
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + "***"
    else:
        masked_local = local_part[0] + "***" + local_part[-1]
    return f"{masked_local}@{domain}"


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Masks a telephone number: e.g. '+91 9876543210' -> '+91 ******3210'."""
    if not phone:
        return None
    cleaned = phone.strip()
    if len(cleaned) <= 4:
        return "***"
    return cleaned[:3] + " " + "*" * max(1, len(cleaned) - 7) + cleaned[-4:]


def sanitize_csv_cell(val: Optional[str]) -> str:
    """
    Sanitizes user-supplied string data against CSV / Spreadsheet formula injection (CWE-1236).
    If a string begins with dangerous prefix characters (=, +, -, @, \t, \r), prepends a single quote (').
    """
    if val is None:
        return ""
    text = str(val)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


# =========================================================================
# Registration Settings Services
# =========================================================================

def get_or_create_registration_settings(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    is_open: bool = True,
    registration_format: str = "both",
    capacity_limit: Optional[int] = None,
    waitlist_enabled: bool = False,
    team_size_min: int = 2,
    team_size_max: int = 4,
    registration_open_at: Optional[datetime] = None,
    registration_close_at: Optional[datetime] = None,
    registration_key: Optional[str] = None,
    access_code: Optional[str] = None,
    auto_generate_key: bool = True,
) -> EventRegistrationSettings:
    """Retrieves existing registration settings or initializes them for an event."""
    event = db.get(Event, event_id)
    if not event or event.organization_id != organization_id:
        raise EventNotFoundError(f"Event '{event_id}' not found in organization '{organization_id}'")
    if event.archived_at is not None:
        raise RegistrationClosedError("Cannot configure registration for an archived event.")
    if event.program_id is not None:
        from app.models.event import Program
        prog = db.get(Program, event.program_id)
        if prog and prog.archived_at is not None:
            raise RegistrationClosedError("Cannot configure registration for an event under an archived program.")

    settings = db.get(EventRegistrationSettings, event_id)
    if settings:
        return settings

    if registration_format not in ("solo_only", "team_only", "both"):
        raise RegistrationError(f"Invalid registration_format '{registration_format}'")
    if team_size_min < 1 or team_size_max < team_size_min:
        raise InvalidTeamSizeError(f"Invalid team size bounds: min={team_size_min}, max={team_size_max}")
    if capacity_limit is not None and capacity_limit < 0:
        raise RegistrationError("capacity_limit must be non-negative or None")

    if registration_key:
        key_hash = hash_credential(registration_key)
    elif auto_generate_key:
        _, key_hash = generate_registration_key()
    else:
        key_hash = None

    code_hash = hash_credential(access_code) if access_code else None

    settings = EventRegistrationSettings(
        event_id=event_id,
        organization_id=organization_id,
        is_open=is_open,
        registration_format=registration_format,
        capacity_limit=capacity_limit,
        current_confirmed_count=0,
        current_attended_count=0,
        waitlist_enabled=waitlist_enabled,
        team_size_min=team_size_min,
        team_size_max=team_size_max,
        registration_open_at=registration_open_at,
        registration_close_at=registration_close_at,
        registration_key_hash=key_hash,
        access_code_hash=code_hash,
    )
    db.add(settings)
    db.flush()
    return settings


def update_registration_settings(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    is_open: Optional[bool] = None,
    registration_format: Optional[str] = None,
    capacity_limit: Optional[int] = None,
    waitlist_enabled: Optional[bool] = None,
    team_size_min: Optional[int] = None,
    team_size_max: Optional[int] = None,
    registration_open_at: Optional[datetime] = None,
    registration_close_at: Optional[datetime] = None,
    access_code: Optional[str] = None,
    registration_key: Optional[str] = None,
    rotate_registration_key: bool = False,
) -> EventRegistrationSettings:
    """Updates registration settings for an event under authorized manager permission."""
    require_permission(
        db,
        actor_user,
        ACTION_MANAGE_REGISTRATION_SETTINGS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    event = db.get(Event, event_id)
    if not event or event.organization_id != organization_id:
        raise EventNotFoundError(f"Event '{event_id}' not found in organization '{organization_id}'")

    if is_open is True:
        if event.archived_at is not None:
            raise RegistrationClosedError("Cannot open registration for an archived event.")
        if event.program_id is not None:
            from app.models.event import Program
            prog = db.get(Program, event.program_id)
            if prog and prog.archived_at is not None:
                raise RegistrationClosedError("Cannot open registration for an event under an archived program.")

    settings = get_or_create_registration_settings(db, organization_id, event_id)

    if registration_format is not None:
        if registration_format not in ("solo_only", "team_only", "both"):
            raise RegistrationError(f"Invalid registration_format '{registration_format}'")
        settings.registration_format = registration_format

    new_min = team_size_min if team_size_min is not None else settings.team_size_min
    new_max = team_size_max if team_size_max is not None else settings.team_size_max
    if new_min < 1 or new_max < new_min:
        raise InvalidTeamSizeError(f"Invalid team size bounds: min={new_min}, max={new_max}")
    settings.team_size_min = new_min
    settings.team_size_max = new_max

    if capacity_limit is not None and capacity_limit < 0:
        raise RegistrationError("capacity_limit must be non-negative or None")
    if capacity_limit is not None:
        settings.capacity_limit = capacity_limit

    if is_open is not None:
        settings.is_open = is_open
    if waitlist_enabled is not None:
        settings.waitlist_enabled = waitlist_enabled
    if registration_open_at is not None:
        settings.registration_open_at = registration_open_at
    if registration_close_at is not None:
        settings.registration_close_at = registration_close_at
    if access_code is not None:
        settings.access_code_hash = hash_credential(access_code) if access_code.strip() else None

    if rotate_registration_key:
        raw_key, key_hash = generate_registration_key()
        settings.registration_key_hash = key_hash
        settings._transient_registration_key = raw_key
    elif registration_key is not None:
        settings.registration_key_hash = hash_credential(registration_key) if registration_key.strip() else None
        settings._transient_registration_key = registration_key.strip() if registration_key.strip() else None

    settings.updated_at = datetime.now(timezone.utc)
    db.flush()
    return settings


# =========================================================================
# Registration & Capacity Reservation Engine
# =========================================================================

def _validate_event_and_settings_for_registration(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    access_code: Optional[str] = None,
) -> Tuple[Event, EventRegistrationSettings]:
    """Validates that an event exists, is active, registration is open, and temporal windows match."""
    event = db.get(Event, event_id)
    if not event or event.organization_id != organization_id:
        raise EventNotFoundError(f"Event '{event_id}' not found in organization '{organization_id}'")
    if event.archived_at is not None:
        raise RegistrationClosedError("Cannot register for an archived event.")

    if event.program_id is not None:
        from app.models.event import Program
        prog = db.get(Program, event.program_id)
        if prog and prog.archived_at is not None:
            raise RegistrationClosedError("Cannot register for an event under an archived program.")

    settings = db.get(EventRegistrationSettings, event_id)
    if not settings or not settings.is_open:
        raise RegistrationClosedError("Registration is currently closed for this event.")

    now = datetime.now(timezone.utc)
    open_at = ensure_utc(settings.registration_open_at)
    close_at = ensure_utc(settings.registration_close_at)
    if open_at and now < open_at:
        raise RegistrationWindowError("Registration for this event has not yet opened.")
    if close_at and now > close_at:
        raise RegistrationWindowError("Registration for this event has already closed.")

    # Access code verification if restricted
    if settings.access_code_hash:
        if not access_code:
            raise PermissionDeniedError("Access code is required for this private event.")
        if not hmac.compare_digest(hash_credential(access_code), settings.access_code_hash):
            raise PermissionDeniedError("Invalid access code provided.")

    return event, settings


def _reserve_capacity_slots_atomic(
    db: Session,
    event_id: uuid.UUID,
    slots_needed: int,
    waitlist_enabled: bool,
) -> bool:
    """
    Atomically attempts to reserve capacity slots using a conditional database update (D-SLICE5-01).
    Returns True if confirmed slots were reserved, or False if waitlisted.
    Raises CapacityExhaustedError if full and waitlist is disabled.
    """
    stmt = (
        update(EventRegistrationSettings)
        .where(EventRegistrationSettings.event_id == event_id)
        .where(
            or_(
                EventRegistrationSettings.capacity_limit.is_(None),
                EventRegistrationSettings.current_confirmed_count + slots_needed <= EventRegistrationSettings.capacity_limit,
            )
        )
        .values(
            current_confirmed_count=EventRegistrationSettings.current_confirmed_count + slots_needed,
            updated_at=datetime.now(timezone.utc),
        )
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        if waitlist_enabled:
            return False  # Waitlisted
        raise CapacityExhaustedError(
            f"Event capacity cannot accommodate {slots_needed} participant(s). Registration rejected."
        )
    return True  # Confirmed slots reserved


def create_individual_registration(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    full_name: str,
    email: str,
    phone_number: Optional[str] = None,
    college_name: Optional[str] = None,
    student_id: Optional[str] = None,
    custom_answers: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
    access_code: Optional[str] = None,
    channel: str = "native_web",
) -> RegistrationResultDTO:
    """
    Submits a native individual participant registration (CO-FR-008, FA-005).
    Issues an individual admission pass credential with zero PII in the pass token.
    Enforces atomic individual capacity reservation.
    """
    cleaned_name = full_name.strip()
    cleaned_email = email.strip().lower()
    if not cleaned_name:
        raise RegistrationError("Participant full_name is required.")
    if not cleaned_email or "@" not in cleaned_email:
        raise RegistrationError("A valid email address is required.")

    # Idempotency check
    if idempotency_key:
        existing_reg = db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if existing_reg:
            if existing_reg.registration_type != "individual" or existing_reg.contact_email.lower() != cleaned_email:
                raise IdempotencyConflictError("Idempotency key reused with different registration payload.")
            parts = [rp.participant for rp in existing_reg.registration_participants]
            if not parts or parts[0].full_name.strip().lower() != cleaned_name.lower():
                raise IdempotencyConflictError("Idempotency key reused with different participant details.")
            # When replaying an existing registration, raw token cannot be retrieved from DB
            issued_dtos = [IssuedTicketDTO(ticket=t, raw_pass_token="<REDACTED_AFTER_ISSUANCE>") for t in existing_reg.tickets]
            return RegistrationResultDTO(
                registration=existing_reg,
                participants=parts,
                issued_tickets=issued_dtos,
                is_waitlisted=(existing_reg.registration_status == "waitlisted"),
            )

    event, settings = _validate_event_and_settings_for_registration(
        db, organization_id, event_id, access_code
    )

    if settings.registration_format == "team_only":
        raise RegistrationError("This event requires team registration; individual registrations are not permitted.")

    # Reserve 1 capacity slot atomically
    is_confirmed = _reserve_capacity_slots_atomic(db, event_id, slots_needed=1, waitlist_enabled=settings.waitlist_enabled)
    status = "confirmed" if is_confirmed else "waitlisted"

    # Create Registration header
    registration = Registration(
        organization_id=organization_id,
        event_id=event_id,
        registration_type="individual",
        registration_status=status,
        registration_channel=channel,
        contact_email=cleaned_email,
        contact_phone=phone_number.strip() if phone_number else None,
        confirmation_code=generate_confirmation_code(),
        idempotency_key=idempotency_key,
        source_type="native",
    )
    db.add(registration)
    db.flush()

    # Create distinct Participant record
    participant = Participant(
        organization_id=organization_id,
        event_id=event_id,
        full_name=cleaned_name,
        email_normalized=cleaned_email,
        phone_number=phone_number.strip() if phone_number else None,
        college_name=college_name.strip() if college_name else None,
        student_id=student_id.strip() if student_id else None,
        status="registered",
        custom_answers=custom_answers,
    )
    db.add(participant)
    db.flush()

    # Link Participant to Registration
    reg_part = RegistrationParticipant(
        organization_id=organization_id,
        event_id=event_id,
        registration_id=registration.id,
        participant_id=participant.id,
        is_primary_contact=True,
        team_role="solo",
    )
    db.add(reg_part)
    db.flush()

    # Issue digital admission pass if confirmed
    issued_dtos: List[IssuedTicketDTO] = []
    if is_confirmed:
        raw_token, token_hash = generate_ticket_credential()
        ticket = Ticket(
            organization_id=organization_id,
            event_id=event_id,
            participant_id=participant.id,
            registration_id=registration.id,
            ticket_reference=generate_ticket_reference(),
            pass_code_hash=token_hash,
            status="issued",
        )
        db.add(ticket)
        db.flush()
        issued_dtos.append(IssuedTicketDTO(ticket=ticket, raw_pass_token=raw_token))

    return RegistrationResultDTO(
        registration=registration,
        participants=[participant],
        issued_tickets=issued_dtos,
        is_waitlisted=(not is_confirmed),
    )


def create_team_registration(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    team_name: str,
    members: List[Dict[str, Any]],
    contact_email: str,
    contact_phone: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    access_code: Optional[str] = None,
    channel: str = "native_web",
) -> RegistrationResultDTO:
    """
    Submits a native team registration (D-SLICE5-01, FA-005, FA-007).
    Validates team bounds and creates distinct Participant records for every member.
    Consumes N capacity slots atomically; if the full team cannot fit, the complete registration
    is rejected or waitlisted—never partially admitted.
    """
    cleaned_team_name = team_name.strip()
    cleaned_contact_email = contact_email.strip().lower()
    if not cleaned_team_name:
        raise RegistrationError("team_name is required for team registrations.")
    if not cleaned_contact_email or "@" not in cleaned_contact_email:
        raise RegistrationError("A valid contact_email is required.")
    if not members:
        raise RegistrationError("At least one member is required.")

    # Idempotency check
    if idempotency_key:
        existing_reg = db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if existing_reg:
            if existing_reg.registration_type != "team" or (existing_reg.team_name or "").strip().lower() != cleaned_team_name.lower() or existing_reg.contact_email.lower() != cleaned_contact_email:
                raise IdempotencyConflictError("Idempotency key reused with different team payload.")
            parts = [rp.participant for rp in existing_reg.registration_participants]
            if len(parts) != len(members):
                raise IdempotencyConflictError("Idempotency key reused with different number of team members.")
            issued_dtos = [IssuedTicketDTO(ticket=t, raw_pass_token="<REDACTED_AFTER_ISSUANCE>") for t in existing_reg.tickets]
            return RegistrationResultDTO(
                registration=existing_reg,
                participants=parts,
                issued_tickets=issued_dtos,
                is_waitlisted=(existing_reg.registration_status == "waitlisted"),
            )

    event, settings = _validate_event_and_settings_for_registration(
        db, organization_id, event_id, access_code
    )

    if settings.registration_format == "solo_only":
        raise RegistrationError("This event only permits individual registrations; team registrations are not allowed.")

    num_members = len(members)
    if num_members < settings.team_size_min or num_members > settings.team_size_max:
        raise InvalidTeamSizeError(
            f"Team size {num_members} outside allowed bounds [{settings.team_size_min}, {settings.team_size_max}]."
        )

    # Validate each member in payload and reject intra-team duplicates
    seen_member_identities = set()
    cleaned_members = []
    for m in members:
        m_name = (m.get("full_name") or "").strip()
        m_email = (m.get("email") or "").strip().lower()
        if not m_name:
            raise RegistrationError("All team members must have a full_name.")
        if not m_email or "@" not in m_email:
            raise RegistrationError(f"Team member '{m_name}' has an invalid email.")
        
        identity_key = (m_name.lower(), m_email)
        if identity_key in seen_member_identities:
            raise DuplicateRegistrationError(f"Duplicate team member detected in submission: '{m_name}' ({m_email})")
        seen_member_identities.add(identity_key)
        
        cleaned_members.append({
            "full_name": m_name,
            "email_normalized": m_email,
            "phone_number": (m.get("phone_number") or "").strip() or None,
            "college_name": (m.get("college_name") or "").strip() or None,
            "student_id": (m.get("student_id") or "").strip() or None,
            "custom_answers": m.get("custom_answers"),
            "is_primary_contact": bool(m.get("is_primary_contact", False)),
            "team_role": (m.get("team_role") or "member").strip(),
        })

    # Ensure at least one member is designated primary contact; default first if none flagged
    if not any(m["is_primary_contact"] for m in cleaned_members):
        cleaned_members[0]["is_primary_contact"] = True
        cleaned_members[0]["team_role"] = "leader"

    # Reserve N capacity slots atomically
    is_confirmed = _reserve_capacity_slots_atomic(
        db, event_id, slots_needed=num_members, waitlist_enabled=settings.waitlist_enabled
    )
    status = "confirmed" if is_confirmed else "waitlisted"

    # Create Registration header
    registration = Registration(
        organization_id=organization_id,
        event_id=event_id,
        registration_type="team",
        registration_status=status,
        registration_channel=channel,
        team_name=cleaned_team_name,
        contact_email=cleaned_contact_email,
        contact_phone=contact_phone.strip() if contact_phone else None,
        confirmation_code=generate_confirmation_code(),
        idempotency_key=idempotency_key,
        source_type="native",
    )
    db.add(registration)
    db.flush()

    participants_list: List[Participant] = []
    issued_dtos: List[IssuedTicketDTO] = []

    for m in cleaned_members:
        # Create individual Participant record
        participant = Participant(
            organization_id=organization_id,
            event_id=event_id,
            full_name=m["full_name"],
            email_normalized=m["email_normalized"],
            phone_number=m["phone_number"],
            college_name=m["college_name"],
            student_id=m["student_id"],
            status="registered",
            custom_answers=m["custom_answers"],
        )
        db.add(participant)
        db.flush()
        participants_list.append(participant)

        # Link Participant to Registration
        reg_part = RegistrationParticipant(
            organization_id=organization_id,
            event_id=event_id,
            registration_id=registration.id,
            participant_id=participant.id,
            is_primary_contact=m["is_primary_contact"],
            team_role=m["team_role"],
        )
        db.add(reg_part)
        db.flush()

        # Issue distinct Ticket pass for each team member if confirmed
        if is_confirmed:
            raw_token, token_hash = generate_ticket_credential()
            ticket = Ticket(
                organization_id=organization_id,
                event_id=event_id,
                participant_id=participant.id,
                registration_id=registration.id,
                ticket_reference=generate_ticket_reference(),
                pass_code_hash=token_hash,
                status="issued",
            )
            db.add(ticket)
            db.flush()
            issued_dtos.append(IssuedTicketDTO(ticket=ticket, raw_pass_token=raw_token))

    return RegistrationResultDTO(
        registration=registration,
        participants=participants_list,
        issued_tickets=issued_dtos,
        is_waitlisted=(not is_confirmed),
    )


def cancel_registration(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    registration_id: uuid.UUID,
    reason: str,
    actor_user: Optional[UserProfile] = None,
) -> Registration:
    """
    Cancels an individual or team registration.
    Reverts confirmed capacity slots atomically and revokes all issued ticket passes.
    """
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise RegistrationError("cancellation_reason is required.")

    registration = db.get(Registration, registration_id)
    if not registration or registration.event_id != event_id or registration.organization_id != organization_id:
        raise RegistrationNotFoundError(f"Registration '{registration_id}' not found in event '{event_id}'")

    if registration.registration_status == "cancelled":
        return registration

    now = datetime.now(timezone.utc)
    prior_status = registration.registration_status
    registration.registration_status = "cancelled"
    registration.cancelled_at = now
    registration.cancellation_reason = cleaned_reason
    registration.updated_at = now

    # Cancel all linked tickets and participants (unless already attended)
    slots_to_free = 0
    for rp in registration.registration_participants:
        part = rp.participant
        if part and part.status != "attended":
            part.status = "cancelled"
            part.updated_at = now

    for ticket in registration.tickets:
        if ticket.status == "issued":
            ticket.status = "cancelled"
            ticket.revoked_at = None
            ticket.revocation_reason = f"Registration cancelled: {cleaned_reason}"
            slots_to_free += 1

    # Restore capacity slots if registration was previously confirmed
    if prior_status == "confirmed" and slots_to_free > 0:
        db.execute(
            update(EventRegistrationSettings)
            .where(EventRegistrationSettings.event_id == event_id)
            .values(
                current_confirmed_count=func.max(0, EventRegistrationSettings.current_confirmed_count - slots_to_free),
                updated_at=now,
            )
        )

    db.flush()
    return registration


# =========================================================================
# Admission Pass Verification & Revocation
# =========================================================================

def verify_ticket_pass(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    raw_token: str,
) -> Tuple[Ticket, Participant]:
    """
    Verifies a presented raw pass token against an Event.
    Uses constant-time digest comparison. Rejects revoked, cancelled, invalid, or cross-event passes.
    """
    token_str = raw_token.strip()
    if not token_str:
        raise TicketInvalidError("Credential token cannot be empty.")

    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    ticket = db.execute(
        select(Ticket).where(
            Ticket.event_id == event_id,
            Ticket.organization_id == organization_id,
            Ticket.pass_code_hash == token_hash,
        )
    ).scalar_one_or_none()

    if not ticket:
        raise TicketNotFoundError("No valid admission pass found matching this credential.")

    if not hmac.compare_digest(ticket.pass_code_hash, token_hash):
        raise TicketInvalidError("Tampered or invalid credential.")

    if ticket.status == "revoked":
        raise TicketRevokedError(f"Ticket has been revoked: {ticket.revocation_reason or 'No reason provided'}")
    if ticket.status == "cancelled":
        raise TicketInvalidError("Ticket has been cancelled due to registration cancellation.")

    participant = db.get(Participant, ticket.participant_id)
    if not participant or participant.event_id != event_id or participant.organization_id != organization_id:
        raise ScopeIntegrityError("Participant is not associated with this event.")
    if participant.status == "cancelled":
        raise TicketInvalidError("Participant registration has been cancelled.")

    return ticket, participant


def revoke_ticket(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    ticket_id: uuid.UUID,
    reason: str,
    actor_user: UserProfile,
) -> Ticket:
    """Revokes an individual admission pass credential with an audit explanation."""
    require_permission(
        db,
        actor_user,
        ACTION_MANAGE_REGISTRATION_SETTINGS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise TicketError("revocation_reason is required.")

    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.event_id != event_id or ticket.organization_id != organization_id:
        raise TicketNotFoundError(f"Ticket '{ticket_id}' not found in event '{event_id}'")

    if ticket.status == "revoked":
        return ticket

    now = datetime.now(timezone.utc)
    ticket.status = "revoked"
    ticket.revoked_at = now
    ticket.revocation_reason = cleaned_reason
    db.flush()
    return ticket


def issue_replacement_ticket(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    actor_user: UserProfile,
    reason: str,
) -> IssuedTicketDTO:
    """Revokes any existing active pass and issues a fresh admission pass for a participant."""
    require_permission(
        db,
        actor_user,
        ACTION_MANAGE_REGISTRATION_SETTINGS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    participant = db.get(Participant, participant_id)
    if not participant or participant.event_id != event_id or participant.organization_id != organization_id:
        raise ScopeIntegrityError("Participant not found in event.")
    if participant.status == "cancelled":
        raise TicketInvalidError("Cannot issue pass for a cancelled participant.")

    # Find registration
    reg_part = db.execute(
        select(RegistrationParticipant).where(
            RegistrationParticipant.participant_id == participant_id,
            RegistrationParticipant.event_id == event_id,
        )
    ).scalar_one_or_none()
    if not reg_part:
        raise ScopeIntegrityError("Registration link not found for participant.")

    # Revoke any currently active or used pass for this participant
    prior_tickets = list(
        db.execute(
            select(Ticket).where(
                Ticket.participant_id == participant_id,
                Ticket.event_id == event_id,
                Ticket.status.in_(["issued", "used"]),
            )
        ).scalars().all()
    )
    now = datetime.now(timezone.utc)
    for pt in prior_tickets:
        pt.status = "revoked"
        pt.revoked_at = now
        pt.revocation_reason = f"Replacement issued: {reason.strip()}"
    if prior_tickets:
        db.flush()

    # Generate new pass
    raw_token, token_hash = generate_ticket_credential()
    new_ticket = Ticket(
        organization_id=organization_id,
        event_id=event_id,
        participant_id=participant_id,
        registration_id=reg_part.registration_id,
        ticket_reference=generate_ticket_reference(),
        pass_code_hash=token_hash,
        status="issued",
    )
    db.add(new_ticket)
    db.flush()
    return IssuedTicketDTO(ticket=new_ticket, raw_pass_token=raw_token)


# =========================================================================
# Attendance Check-In & Audit Corrections
# =========================================================================

def check_in_participant(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    raw_token: Optional[str] = None,
    participant_id: Optional[uuid.UUID] = None,
    station_id: Optional[str] = None,
    method: str = "qr_scan",
) -> Tuple[CheckIn, bool]:
    """
    Records physical attendance arrival for an individual attendee (CO-FR-009, FA-005).
    Authorized for registration staff or leads (ACTION_CHECK_IN).
    Enforces strictly at most one valid check-in per participant per event.
    Returns: (CheckIn, is_duplicate)
    """
    require_permission(
        db,
        actor_user,
        ACTION_CHECK_IN,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    if method not in ("qr_scan", "manual_search", "walk_in_direct"):
        raise CheckInError(f"Invalid check-in method '{method}'")

    if raw_token:
        ticket, participant = verify_ticket_pass(db, organization_id, event_id, raw_token)
    elif participant_id:
        participant = db.get(Participant, participant_id)
        if not participant or participant.event_id != event_id or participant.organization_id != organization_id:
            raise ScopeIntegrityError("Participant not found in this event.")
        if participant.status == "cancelled":
            raise CheckInError("Participant registration has been cancelled.")
        
        ticket = db.execute(
            select(Ticket).where(
                Ticket.participant_id == participant_id,
                Ticket.event_id == event_id,
                Ticket.status == "issued",
            )
        ).scalar_one_or_none()
        if not ticket:
            ticket = db.execute(
                select(Ticket).where(
                    Ticket.participant_id == participant_id,
                    Ticket.event_id == event_id,
                    Ticket.status == "used",
                )
            ).scalars().first()
        if not ticket:
            raise TicketNotFoundError("No valid admission pass found for participant.")
        method = "manual_search"
    else:
        raise CheckInError("Either raw_token or participant_id must be provided for check-in.")

    # Check for existing valid check-in (idempotency rule per FA-005)
    existing_check_in = db.execute(
        select(CheckIn).where(
            CheckIn.event_id == event_id,
            CheckIn.participant_id == participant.id,
            CheckIn.check_in_status == "valid",
        )
    ).scalar_one_or_none()

    if existing_check_in:
        # Attendee already checked in; return existing record idempotently without incrementing counters
        return existing_check_in, True

    now = datetime.now(timezone.utc)
    check_in = CheckIn(
        organization_id=organization_id,
        event_id=event_id,
        participant_id=participant.id,
        ticket_id=ticket.id,
        check_in_status="valid",
        method=method,
        station_id=station_id.strip() if station_id else None,
        checked_in_by_user_id=actor_user.id,
        checked_in_at=now,
    )
    db.add(check_in)

    # Transition ticket and participant state
    ticket.status = "used"
    ticket.used_at = now
    participant.status = "attended"
    participant.updated_at = now

    # Atomically increment current_attended_count on settings
    db.execute(
        update(EventRegistrationSettings)
        .where(EventRegistrationSettings.event_id == event_id)
        .values(
            current_attended_count=EventRegistrationSettings.current_attended_count + 1,
            updated_at=now,
        )
    )

    db.flush()
    return check_in, False


def correct_or_void_check_in(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    check_in_id: uuid.UUID,
    reason: str,
    actor_user: UserProfile,
) -> Tuple[CheckIn, CheckInCorrection]:
    """
    Corrects or voids a mistaken check-in record (D-SLICE5-04).
    Restricted exclusively to managers holding ACTION_CORRECT_CHECK_IN.
    Requires minimum 10-character explanation and preserves full historical audit evidence.
    """
    require_permission(
        db,
        actor_user,
        ACTION_CORRECT_CHECK_IN,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    cleaned_reason = reason.strip()
    if len(cleaned_reason) < 10:
        raise CheckInCorrectionError("Correction reason must be at least 10 characters.")

    check_in = db.get(CheckIn, check_in_id)
    if not check_in or check_in.event_id != event_id or check_in.organization_id != organization_id:
        raise CheckInNotFoundError(f"Check-in '{check_in_id}' not found in event '{event_id}'")

    if check_in.check_in_status != "valid":
        raise CheckInCorrectionError(f"Check-in is already in '{check_in.check_in_status}' status.")

    now = datetime.now(timezone.utc)
    check_in.check_in_status = "voided"
    check_in.voided_at = now
    check_in.voided_by_user_id = actor_user.id

    # Create immutable audit record
    correction = CheckInCorrection(
        check_in_id=check_in.id,
        previous_status="valid",
        new_status="voided",
        reason=cleaned_reason,
        corrected_by_user_id=actor_user.id,
        corrected_at=now,
    )
    db.add(correction)

    # Revert ticket and participant status so they can be re-admitted if appropriate
    ticket = check_in.ticket
    if ticket and ticket.status == "used":
        ticket.status = "issued"
        ticket.used_at = None

    participant = check_in.participant
    if participant and participant.status == "attended":
        participant.status = "registered"
        participant.updated_at = now

    # Atomically decrement current_attended_count
    db.execute(
        update(EventRegistrationSettings)
        .where(EventRegistrationSettings.event_id == event_id)
        .values(
            current_attended_count=func.max(0, EventRegistrationSettings.current_attended_count - 1),
            updated_at=now,
        )
    )

    db.flush()
    return check_in, correction


# =========================================================================
# Privacy & Roster Query Boundary
# =========================================================================

def get_event_roster_participants(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    include_unmasked_contact: bool = False,
) -> List[Dict[str, Any]]:
    """
    Roster discovery boundary enforcing tiered privacy disclosure.
    Desk volunteers with ACTION_VIEW_REGISTRATIONS inspect only masked contact info.
    Unmasked contact details require elevated ACTION_VIEW_ATTENDEE_CONTACT.
    """
    require_permission(
        db,
        actor_user,
        ACTION_VIEW_REGISTRATIONS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    can_view_unmasked = False
    if include_unmasked_contact:
        can_view_unmasked = can_perform(
            db,
            actor_user,
            ACTION_VIEW_ATTENDEE_CONTACT,
            organization_id=organization_id,
            scope_type="event",
            scope_id=event_id,
        )

    stmt = (
        select(Participant)
        .where(
            Participant.event_id == event_id,
            Participant.organization_id == organization_id,
            Participant.status != "cancelled",
        )
        .order_by(Participant.full_name.asc())
    )
    participants = list(db.execute(stmt).scalars().all())

    roster = []
    for p in participants:
        roster.append({
            "id": p.id,
            "full_name": p.full_name,
            "status": p.status,
            "college_name": p.college_name,
            "student_id": p.student_id,
            "email": p.email_normalized if can_view_unmasked else mask_email(p.email_normalized),
            "phone_number": p.phone_number if can_view_unmasked else mask_phone(p.phone_number),
            "created_at": p.created_at,
        })
    return roster


# =========================================================================
# Diagnostic Reconciliation Engine
# =========================================================================

def reconcile_event_registration_counts(
    db: Session,
    event_id: uuid.UUID,
    auto_fix: bool = False,
) -> Dict[str, Any]:
    """
    Diagnostic audit query reconciling stored counters in EventRegistrationSettings
    against actual database records.
    Counts:
    - actual_confirmed_count: Count of active, non-cancelled participants in confirmed registrations
    - actual_attended_count: Count of valid check-ins for the event
    """
    settings = db.get(EventRegistrationSettings, event_id)
    if not settings:
        raise RegistrationError(f"Registration settings not found for event '{event_id}'")

    actual_confirmed_count = db.execute(
        select(func.count(RegistrationParticipant.id))
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .join(Participant, Participant.id == RegistrationParticipant.participant_id)
        .where(
            Registration.event_id == event_id,
            Registration.registration_status == "confirmed",
            Participant.status != "cancelled",
        )
    ).scalar() or 0

    actual_attended_count = db.execute(
        select(func.count(CheckIn.id))
        .where(
            CheckIn.event_id == event_id,
            CheckIn.check_in_status == "valid",
        )
    ).scalar() or 0

    discrepancy = {
        "event_id": str(event_id),
        "stored_confirmed_count": settings.current_confirmed_count,
        "actual_confirmed_count": actual_confirmed_count,
        "confirmed_reconciled": settings.current_confirmed_count == actual_confirmed_count,
        "stored_attended_count": settings.current_attended_count,
        "actual_attended_count": actual_attended_count,
        "attended_reconciled": settings.current_attended_count == actual_attended_count,
    }

    if auto_fix and (not discrepancy["confirmed_reconciled"] or not discrepancy["attended_reconciled"]):
        settings.current_confirmed_count = actual_confirmed_count
        settings.current_attended_count = actual_attended_count
        settings.updated_at = datetime.now(timezone.utc)
        db.flush()
        discrepancy["auto_fixed"] = True
    else:
        discrepancy["auto_fixed"] = False

    return discrepancy


# =========================================================================
# Slice 5C Service Functions for REST APIs
# =========================================================================

def get_public_event_by_registration_key(
    db: Session,
    registration_key: str,
) -> Tuple[Event, EventRegistrationSettings]:
    """Retrieves public event and registration settings by registration key."""
    key_hash = hash_credential(registration_key)
    settings = db.execute(
        select(EventRegistrationSettings).where(
            EventRegistrationSettings.registration_key_hash == key_hash
        )
    ).scalar_one_or_none()
    if not settings:
        raise EventNotFoundError("Event registration not found.")

    event = db.get(Event, settings.event_id)
    if not event or event.archived_at is not None:
        raise EventNotFoundError("Event registration not found.")

    if event.program_id is not None:
        from app.models.event import Program
        prog = db.get(Program, event.program_id)
        if prog and prog.archived_at is not None:
            raise EventNotFoundError("Event registration not found.")

    return event, settings


def get_public_registration_status(
    db: Session,
    event_id: uuid.UUID,
    confirmation_code: str,
) -> Dict[str, Any]:
    """Retrieves registration status via unguessable confirmation code without disclosing PII."""
    cleaned_code = confirmation_code.strip().upper()
    reg = db.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.confirmation_code == cleaned_code,
        )
    ).scalar_one_or_none()
    if not reg:
        raise RegistrationNotFoundError("Registration not found.")

    participants_info = []
    for rp in reg.registration_participants:
        p = rp.participant
        if p and p.status != "cancelled":
            participants_info.append({
                "full_name": p.full_name,
                "team_role": rp.team_role,
                "is_primary_contact": rp.is_primary_contact,
                "status": p.status,
            })

    return {
        "confirmation_code": reg.confirmation_code,
        "registration_status": reg.registration_status,
        "registration_type": reg.registration_type,
        "team_name": reg.team_name,
        "participant_count": len(participants_info),
        "created_at": reg.created_at,
        "participants": participants_info,
    }


def cancel_public_registration(
    db: Session,
    event_id: uuid.UUID,
    confirmation_code: str,
    contact_email: str,
    reason: str,
) -> Registration:
    """Cancels a registration via unguessable confirmation code and matching contact email."""
    cleaned_code = confirmation_code.strip().upper()
    cleaned_email = contact_email.strip().lower()

    reg = db.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.confirmation_code == cleaned_code,
        )
    ).scalar_one_or_none()
    if not reg or reg.contact_email.lower() != cleaned_email:
        raise RegistrationNotFoundError("Registration not found or email mismatch.")

    # Check if any attendee has already checked in
    for rp in reg.registration_participants:
        p = rp.participant
        if p and p.status == "attended":
            raise RegistrationError("Cannot cancel registration after attendees have already checked in.")

    return cancel_registration(
        db,
        organization_id=reg.organization_id,
        event_id=event_id,
        registration_id=reg.id,
        reason=reason,
    )


def list_event_registrations(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    status: Optional[str] = None,
    registration_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Lists registration transaction headers for staff review."""
    require_permission(
        db,
        actor_user,
        ACTION_VIEW_REGISTRATIONS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    can_view_unmasked = can_perform(
        db,
        actor_user,
        ACTION_VIEW_ATTENDEE_CONTACT,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    stmt = select(Registration).where(
        Registration.organization_id == organization_id,
        Registration.event_id == event_id,
    )
    if status:
        stmt = stmt.where(Registration.registration_status == status)
    if registration_type:
        stmt = stmt.where(Registration.registration_type == registration_type)

    stmt = stmt.order_by(Registration.created_at.desc()).limit(limit).offset(offset)
    regs = list(db.execute(stmt).scalars().all())

    results = []
    for r in regs:
        p_count = db.execute(
            select(func.count(RegistrationParticipant.id)).where(
                RegistrationParticipant.registration_id == r.id
            )
        ).scalar() or 0
        results.append({
            "id": r.id,
            "registration_type": r.registration_type,
            "registration_status": r.registration_status,
            "registration_channel": r.registration_channel,
            "team_name": r.team_name,
            "contact_email": r.contact_email if can_view_unmasked else mask_email(r.contact_email),
            "contact_phone": r.contact_phone if can_view_unmasked else mask_phone(r.contact_phone),
            "confirmation_code": r.confirmation_code,
            "participant_count": p_count,
            "created_at": r.created_at,
            "cancelled_at": r.cancelled_at,
        })
    return results


def list_event_participants(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Lists individual attendees with privacy-aware contact masking."""
    require_permission(
        db,
        actor_user,
        ACTION_VIEW_REGISTRATIONS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    can_view_unmasked = can_perform(
        db,
        actor_user,
        ACTION_VIEW_ATTENDEE_CONTACT,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    stmt = (
        select(Participant, RegistrationParticipant, Registration)
        .join(RegistrationParticipant, RegistrationParticipant.participant_id == Participant.id)
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .where(
            Participant.organization_id == organization_id,
            Participant.event_id == event_id,
        )
    )
    if status:
        stmt = stmt.where(Participant.status == status)
    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Participant.full_name).like(s),
                func.lower(Participant.email_normalized).like(s),
                func.lower(Participant.student_id).like(s),
            )
        )

    stmt = stmt.order_by(Participant.full_name.asc()).limit(limit).offset(offset)
    rows = db.execute(stmt).all()

    results = []
    for p, rp, reg in rows:
        ticket = db.execute(
            select(Ticket).where(
                Ticket.participant_id == p.id,
                Ticket.event_id == event_id,
            ).order_by(Ticket.created_at.desc())
        ).scalars().first()

        check_in = db.execute(
            select(CheckIn).where(
                CheckIn.participant_id == p.id,
                CheckIn.event_id == event_id,
                CheckIn.check_in_status == "valid",
            )
        ).scalar_one_or_none()

        results.append({
            "id": p.id,
            "registration_id": reg.id,
            "full_name": p.full_name,
            "email": p.email_normalized if can_view_unmasked else mask_email(p.email_normalized),
            "phone_number": p.phone_number if can_view_unmasked else mask_phone(p.phone_number),
            "college_name": p.college_name,
            "student_id": p.student_id,
            "status": p.status,
            "is_primary_contact": rp.is_primary_contact,
            "team_role": rp.team_role,
            "team_name": reg.team_name,
            "ticket_status": ticket.status if ticket else None,
            "ticket_reference": ticket.ticket_reference if ticket else None,
            "checked_in_at": check_in.checked_in_at if check_in else None,
            "created_at": p.created_at,
        })
    return results


def get_participant_detail(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    actor_user: UserProfile,
) -> Dict[str, Any]:
    """Retrieves detailed attendee record respecting contact masking permissions."""
    require_permission(
        db,
        actor_user,
        ACTION_VIEW_REGISTRATIONS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    can_view_unmasked = can_perform(
        db,
        actor_user,
        ACTION_VIEW_ATTENDEE_CONTACT,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    p = db.get(Participant, participant_id)
    if not p or p.event_id != event_id or p.organization_id != organization_id:
        raise ScopeIntegrityError("Participant not found in this event.")

    reg_part = db.execute(
        select(RegistrationParticipant, Registration)
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .where(
            RegistrationParticipant.participant_id == p.id,
            RegistrationParticipant.event_id == event_id,
        )
    ).first()

    reg_id = reg_part[1].id if reg_part else None
    team_name = reg_part[1].team_name if reg_part else None
    team_role = reg_part[0].team_role if reg_part else None
    is_primary = reg_part[0].is_primary_contact if reg_part else False

    tickets = list(
        db.execute(
            select(Ticket).where(
                Ticket.participant_id == p.id,
                Ticket.event_id == event_id,
            ).order_by(Ticket.created_at.desc())
        ).scalars().all()
    )

    tickets_info = [
        {
            "id": str(t.id),
            "ticket_reference": t.ticket_reference,
            "status": t.status,
            "issued_at": t.issued_at.isoformat() if t.issued_at else None,
            "used_at": t.used_at.isoformat() if t.used_at else None,
            "revoked_at": t.revoked_at.isoformat() if t.revoked_at else None,
        }
        for t in tickets
    ]

    check_in = db.execute(
        select(CheckIn).where(
            CheckIn.participant_id == p.id,
            CheckIn.event_id == event_id,
            CheckIn.check_in_status == "valid",
        )
    ).scalar_one_or_none()

    check_in_info = (
        {
            "id": str(check_in.id),
            "status": check_in.check_in_status,
            "method": check_in.method,
            "station_id": check_in.station_id,
            "checked_in_at": check_in.checked_in_at.isoformat(),
        }
        if check_in
        else None
    )

    return {
        "id": p.id,
        "registration_id": reg_id,
        "full_name": p.full_name,
        "email": p.email_normalized if can_view_unmasked else mask_email(p.email_normalized),
        "phone_number": p.phone_number if can_view_unmasked else mask_phone(p.phone_number),
        "college_name": p.college_name,
        "student_id": p.student_id,
        "status": p.status,
        "custom_answers": p.custom_answers,
        "is_primary_contact": is_primary,
        "team_role": team_role,
        "team_name": team_name,
        "tickets": tickets_info,
        "check_in": check_in_info,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def update_participant(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    participant_id: uuid.UUID,
    actor_user: UserProfile,
    full_name: Optional[str] = None,
    college_name: Optional[str] = None,
    student_id: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> Participant:
    """Updates attendee personal details under manager authorization."""
    require_permission(
        db,
        actor_user,
        ACTION_MANAGE_REGISTRATION_SETTINGS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    p = db.get(Participant, participant_id)
    if not p or p.event_id != event_id or p.organization_id != organization_id:
        raise ScopeIntegrityError("Participant not found in this event.")

    if full_name is not None:
        cleaned_name = full_name.strip()
        if not cleaned_name:
            raise RegistrationError("full_name cannot be empty.")
        p.full_name = cleaned_name

    if college_name is not None:
        p.college_name = college_name.strip() or None
    if student_id is not None:
        p.student_id = student_id.strip() or None
    if phone_number is not None:
        p.phone_number = phone_number.strip() or None

    p.updated_at = datetime.now(timezone.utc)
    db.flush()
    return p


def lookup_for_check_in(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
    query_str: str,
) -> List[Dict[str, Any]]:
    """Lookup candidates for desk check-in verification via ticket token, reference, name, or email prefix."""
    require_permission(
        db,
        actor_user,
        ACTION_CHECK_IN,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    q = query_str.strip()
    if not q:
        return []

    # If query looks like a pass token (e.g. CO-PASS-...)
    if q.upper().startswith("CO-PASS-"):
        token_hash = hashlib.sha256(q.encode("utf-8")).hexdigest()
        ticket = db.execute(
            select(Ticket).where(
                Ticket.event_id == event_id,
                Ticket.organization_id == organization_id,
                Ticket.pass_code_hash == token_hash,
            )
        ).scalar_one_or_none()
        if ticket:
            p = db.get(Participant, ticket.participant_id)
            if p:
                ci = db.execute(
                    select(CheckIn).where(
                        CheckIn.participant_id == p.id,
                        CheckIn.event_id == event_id,
                        CheckIn.check_in_status == "valid",
                    )
                ).scalar_one_or_none()
                reg_p = db.execute(
                    select(RegistrationParticipant, Registration)
                    .join(Registration, Registration.id == RegistrationParticipant.registration_id)
                    .where(RegistrationParticipant.participant_id == p.id)
                ).first()
                return [{
                    "participant_id": p.id,
                    "full_name": p.full_name,
                    "email": mask_email(p.email_normalized),
                    "college_name": p.college_name,
                    "student_id": p.student_id,
                    "team_name": reg_p[1].team_name if reg_p else None,
                    "status": p.status,
                    "is_eligible_for_check_in": (p.status != "cancelled" and ticket.status == "issued"),
                    "already_checked_in": (ci is not None),
                    "ticket_reference": ticket.ticket_reference,
                    "ticket_status": ticket.status,
                }]

    # General search by name, student_id, or email
    s = f"%{q.lower()}%"
    stmt = (
        select(Participant, RegistrationParticipant, Registration)
        .join(RegistrationParticipant, RegistrationParticipant.participant_id == Participant.id)
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .where(
            Participant.organization_id == organization_id,
            Participant.event_id == event_id,
            Participant.status != "cancelled",
            or_(
                func.lower(Participant.full_name).like(s),
                func.lower(Participant.email_normalized).like(s),
                func.lower(Participant.student_id).like(s),
            ),
        )
        .limit(20)
    )
    rows = db.execute(stmt).all()

    results = []
    for p, rp, reg in rows:
        ticket = db.execute(
            select(Ticket).where(
                Ticket.participant_id == p.id,
                Ticket.event_id == event_id,
            ).order_by(Ticket.created_at.desc())
        ).scalars().first()

        ci = db.execute(
            select(CheckIn).where(
                CheckIn.participant_id == p.id,
                CheckIn.event_id == event_id,
                CheckIn.check_in_status == "valid",
            )
        ).scalar_one_or_none()

        results.append({
            "participant_id": p.id,
            "full_name": p.full_name,
            "email": mask_email(p.email_normalized),
            "college_name": p.college_name,
            "student_id": p.student_id,
            "team_name": reg.team_name,
            "status": p.status,
            "is_eligible_for_check_in": (p.status != "cancelled" and ticket is not None and ticket.status == "issued"),
            "already_checked_in": (ci is not None),
            "ticket_reference": ticket.ticket_reference if ticket else None,
            "ticket_status": ticket.status if ticket else None,
        })
    return results


def get_event_attendance_summary(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
) -> Dict[str, Any]:
    """Computes operational attendance metrics and team attendance breakdown."""
    require_permission(
        db,
        actor_user,
        ACTION_VIEW_REGISTRATIONS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    settings = get_or_create_registration_settings(db, organization_id, event_id)

    total_indiv = db.execute(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.registration_type == "individual",
            Registration.registration_status == "confirmed",
        )
    ).scalar() or 0

    total_team = db.execute(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.registration_type == "team",
            Registration.registration_status == "confirmed",
        )
    ).scalar() or 0

    total_parts = db.execute(
        select(func.count(Participant.id)).where(
            Participant.event_id == event_id,
            Participant.status != "cancelled",
        )
    ).scalar() or 0

    # Team attendance breakdown
    team_regs = list(
        db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.registration_type == "team",
                Registration.registration_status == "confirmed",
            )
        ).scalars().all()
    )

    fully_attended = 0
    partially_attended = 0
    absent_teams = 0

    for tr in team_regs:
        member_statuses = [
            rp.participant.status
            for rp in tr.registration_participants
            if rp.participant and rp.participant.status != "cancelled"
        ]
        if not member_statuses:
            continue
        attended_count = sum(1 for s in member_statuses if s == "attended")
        if attended_count == len(member_statuses):
            fully_attended += 1
        elif attended_count > 0:
            partially_attended += 1
        else:
            absent_teams += 1

    pct = 0.0
    if settings.current_confirmed_count > 0:
        pct = round((settings.current_attended_count / settings.current_confirmed_count) * 100, 2)

    return {
        "event_id": event_id,
        "capacity_limit": settings.capacity_limit,
        "current_confirmed_count": settings.current_confirmed_count,
        "current_attended_count": settings.current_attended_count,
        "attendance_percentage": pct,
        "total_individual_registrations": total_indiv,
        "total_team_registrations": total_team,
        "total_participants_registered": total_parts,
        "teams_fully_attended": fully_attended,
        "teams_partially_attended": partially_attended,
        "teams_absent": absent_teams,
    }


def export_event_roster_csv(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    actor_user: UserProfile,
) -> str:
    """Exports full attendee roster as CSV string under ACTION_EXPORT_PARTICIPANTS."""
    require_permission(
        db,
        actor_user,
        ACTION_EXPORT_PARTICIPANTS,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    stmt = (
        select(Participant, RegistrationParticipant, Registration)
        .join(RegistrationParticipant, RegistrationParticipant.participant_id == Participant.id)
        .join(Registration, Registration.id == RegistrationParticipant.registration_id)
        .where(
            Participant.organization_id == organization_id,
            Participant.event_id == event_id,
        )
        .order_by(Participant.full_name.asc())
    )
    rows = db.execute(stmt).all()

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "participant_id",
        "full_name",
        "email",
        "phone_number",
        "college_name",
        "student_id",
        "registration_type",
        "team_name",
        "registration_status",
        "participant_status",
        "ticket_reference",
        "ticket_status",
        "check_in_status",
        "checked_in_at",
        "method",
        "station_id",
    ])

    for p, rp, reg in rows:
        ticket = db.execute(
            select(Ticket).where(
                Ticket.participant_id == p.id,
                Ticket.event_id == event_id,
            ).order_by(Ticket.created_at.desc())
        ).scalars().first()

        check_in = db.execute(
            select(CheckIn).where(
                CheckIn.participant_id == p.id,
                CheckIn.event_id == event_id,
                CheckIn.check_in_status == "valid",
            )
        ).scalar_one_or_none()

        writer.writerow([
            str(p.id),
            sanitize_csv_cell(p.full_name),
            sanitize_csv_cell(p.email_normalized),
            sanitize_csv_cell(p.phone_number),
            sanitize_csv_cell(p.college_name),
            sanitize_csv_cell(p.student_id),
            reg.registration_type,
            sanitize_csv_cell(reg.team_name),
            reg.registration_status,
            p.status,
            ticket.ticket_reference if ticket else "",
            ticket.status if ticket else "",
            check_in.check_in_status if check_in else "not_checked_in",
            check_in.checked_in_at.isoformat() if check_in else "",
            check_in.method if check_in else "",
            check_in.station_id if check_in else "",
        ])

    return output.getvalue()


