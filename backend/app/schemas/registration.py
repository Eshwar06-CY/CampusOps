from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# =========================================================================
# Public Registration & Pass Discovery Schemas
# =========================================================================

class PublicEventRegistrationResponse(BaseModel):
    """Publicly accessible metadata for self-service event registration."""
    model_config = ConfigDict(from_attributes=True)

    public_registration_key: str
    event_id: uuid.UUID
    event_name: str
    description: Optional[str] = None
    event_date: str
    event_end_date: Optional[str] = None
    venue: Optional[str] = None
    timezone: str
    registration_status: str  # "open", "closed", "not_yet_open", "ended"
    registration_format: str  # "solo_only", "team_only", "both"
    team_size_min: int
    team_size_max: int
    capacity_available: bool


class ParticipantCreateRequest(BaseModel):
    """Individual attendee details within a public or walk-in registration submission."""
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., min_length=3, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    college_name: Optional[str] = Field(None, max_length=200)
    student_id: Optional[str] = Field(None, max_length=50)
    custom_answers: Optional[Dict[str, Any]] = None
    is_primary_contact: bool = False
    team_role: Optional[str] = Field("member", max_length=50)


class PublicRegistrationRequest(BaseModel):
    """Payload for self-service or staff walk-in participant registration."""
    model_config = ConfigDict(extra="forbid")

    registration_type: str = Field(..., pattern="^(individual|team)$")
    team_name: Optional[str] = Field(None, max_length=150)
    contact_email: str = Field(..., min_length=3, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    participants: List[ParticipantCreateRequest] = Field(..., min_length=1)
    access_code: Optional[str] = Field(None, max_length=100)
    idempotency_key: Optional[str] = Field(None, max_length=128)


class IssuedPassResponse(BaseModel):
    """Single admission pass issued to an attendee."""
    model_config = ConfigDict(from_attributes=True)

    participant_id: uuid.UUID
    participant_name: str
    ticket_reference: str
    pass_code: str  # Raw unguessable credential token (or redacted placeholder on replay)
    pass_url: Optional[str] = None


class PublicRegistrationResponse(BaseModel):
    """Response returned upon submission of an individual or team registration."""
    model_config = ConfigDict(from_attributes=True)

    registration_id: uuid.UUID
    confirmation_code: str
    registration_status: str  # "confirmed", "waitlisted"
    registration_type: str    # "individual", "team"
    team_name: Optional[str] = None
    is_waitlisted: bool = False
    passes: List[IssuedPassResponse]


class PublicPassVerifyRequest(BaseModel):
    """Secure request body for pass verification without exposing bearer tokens in URL paths."""
    model_config = ConfigDict(extra="forbid")

    pass_code: str = Field(..., min_length=1, max_length=255)


class PublicPassDisplayResponse(BaseModel):
    """Attendee digital pass display and QR verification payload (zero PII)."""
    model_config = ConfigDict(from_attributes=True)

    ticket_reference: str
    pass_code: str
    event_name: str
    participant_name: str
    status: str
    issued_at: datetime
    used_at: Optional[datetime] = None
    qr_payload: str
    instructions: str


class PublicRegistrationLookupRequest(BaseModel):
    """Secure request body for registration status lookup without exposing confirmation code in URL."""
    model_config = ConfigDict(extra="forbid")

    confirmation_code: str = Field(..., min_length=1, max_length=100)


class PublicRegistrationStatusResponse(BaseModel):
    """Unguessable capability-based status lookup for an attendee submission."""
    model_config = ConfigDict(from_attributes=True)

    confirmation_code: str
    registration_status: str
    registration_type: str
    team_name: Optional[str] = None
    participant_count: int
    created_at: datetime
    participants: List[Dict[str, Any]]


class PublicRegistrationCancelRequest(BaseModel):
    """Self-service cancellation request using unguessable capability and contact email."""
    model_config = ConfigDict(extra="forbid")

    cancellation_reason: str = Field(..., min_length=5, max_length=500)
    contact_email: str = Field(..., min_length=3, max_length=255)


class PublicRegistrationCancelBodyRequest(BaseModel):
    """Secure request body for cancellation without exposing confirmation code in URL."""
    model_config = ConfigDict(extra="forbid")

    confirmation_code: str = Field(..., min_length=1, max_length=100)
    contact_email: str = Field(..., min_length=3, max_length=255)
    cancellation_reason: str = Field(..., min_length=5, max_length=500)


class PublicRegistrationCancelResponse(BaseModel):
    """Response returned when an attendee cancels their registration."""
    model_config = ConfigDict(from_attributes=True)

    confirmation_code: str
    registration_status: str
    cancelled_at: datetime
    message: str


# =========================================================================
# Staff Settings & Capacity Management Schemas
# =========================================================================

class EventRegistrationSettingsResponse(BaseModel):
    """Staff view of event registration settings and real-time counters."""
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    organization_id: uuid.UUID
    is_open: bool
    registration_format: str
    capacity_limit: Optional[int] = None
    current_confirmed_count: int
    current_attended_count: int
    waitlist_enabled: bool
    team_size_min: int
    team_size_max: int
    registration_open_at: Optional[datetime] = None
    registration_close_at: Optional[datetime] = None
    has_registration_key: bool
    has_access_code: bool
    public_registration_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EventRegistrationSettingsUpdateRequest(BaseModel):
    """Staff payload to update registration settings and capacity parameters."""
    model_config = ConfigDict(extra="forbid")

    is_open: Optional[bool] = None
    registration_format: Optional[str] = Field(None, pattern="^(solo_only|team_only|both)$")
    capacity_limit: Optional[int] = Field(None, ge=0)
    waitlist_enabled: Optional[bool] = None
    team_size_min: Optional[int] = Field(None, ge=1)
    team_size_max: Optional[int] = Field(None, ge=1)
    registration_open_at: Optional[datetime] = None
    registration_close_at: Optional[datetime] = None
    access_code: Optional[str] = Field(None, max_length=100)
    registration_key: Optional[str] = Field(None, max_length=100)
    rotate_registration_key: bool = False


# =========================================================================
# Staff Roster & Registration Management Schemas
# =========================================================================

class StaffRegistrationSummaryResponse(BaseModel):
    """Summary of a registration transaction header for staff listing."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    registration_type: str
    registration_status: str
    registration_channel: str
    team_name: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    confirmation_code: str
    participant_count: int
    created_at: datetime
    cancelled_at: Optional[datetime] = None


class StaffCancelRegistrationRequest(BaseModel):
    """Staff payload to cancel a registration transaction."""
    model_config = ConfigDict(extra="forbid")

    cancellation_reason: str = Field(..., min_length=5, max_length=500)


class StaffParticipantRosterItemResponse(BaseModel):
    """Single attendee roster item for staff view, respecting contact masking."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    registration_id: uuid.UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    college_name: Optional[str] = None
    student_id: Optional[str] = None
    status: str
    is_primary_contact: bool
    team_role: Optional[str] = None
    team_name: Optional[str] = None
    ticket_status: Optional[str] = None
    ticket_reference: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    created_at: datetime


class StaffParticipantDetailResponse(BaseModel):
    """Detailed attendee record with complete ticket history and check-in state."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    registration_id: uuid.UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    college_name: Optional[str] = None
    student_id: Optional[str] = None
    status: str
    custom_answers: Optional[Dict[str, Any]] = None
    is_primary_contact: bool
    team_role: Optional[str] = None
    team_name: Optional[str] = None
    tickets: List[Dict[str, Any]]
    check_in: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class StaffParticipantUpdateRequest(BaseModel):
    """Staff payload to correct an attendee's personal details."""
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    college_name: Optional[str] = Field(None, max_length=200)
    student_id: Optional[str] = Field(None, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=50)


class StaffReissuePassRequest(BaseModel):
    """Staff payload to revoke prior passes and issue a fresh pass credential."""
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=5, max_length=500)


# =========================================================================
# Attendance Check-In & Audit Correction Schemas
# =========================================================================

class CheckInRequest(BaseModel):
    """Payload to record an attendee's arrival via QR scan or manual search."""
    model_config = ConfigDict(extra="forbid")

    pass_code: Optional[str] = Field(None, max_length=100)
    participant_id: Optional[uuid.UUID] = None
    method: str = Field("qr_scan", pattern="^(qr_scan|manual_search|walk_in_direct)$")
    station_id: Optional[str] = Field(None, max_length=50)


class CheckInResponse(BaseModel):
    """Outcome of an attendance check-in scan or manual arrival."""
    model_config = ConfigDict(from_attributes=True)

    check_in_id: uuid.UUID
    status: str  # "verified" or "already_checked_in"
    participant_id: uuid.UUID
    participant_name: str
    team_name: Optional[str] = None
    checked_in_at: datetime
    station_id: Optional[str] = None
    message: Optional[str] = None


class CheckInLookupItemResponse(BaseModel):
    """Result item when desk staff search the roster for manual verification."""
    model_config = ConfigDict(from_attributes=True)

    participant_id: uuid.UUID
    full_name: str
    email: str
    college_name: Optional[str] = None
    student_id: Optional[str] = None
    team_name: Optional[str] = None
    status: str
    is_eligible_for_check_in: bool
    already_checked_in: bool
    ticket_reference: Optional[str] = None
    ticket_status: Optional[str] = None


class CheckInVoidRequest(BaseModel):
    """Manager-only payload to void a mistaken check-in with mandatory explanation."""
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=10, max_length=1000)


class CheckInVoidResponse(BaseModel):
    """Confirmation of an audited check-in void."""
    model_config = ConfigDict(from_attributes=True)

    check_in_id: uuid.UUID
    check_in_status: str  # "voided"
    voided_at: datetime
    reason: str


# =========================================================================
# Attendance Reporting Schemas
# =========================================================================

class AttendanceSummaryResponse(BaseModel):
    """Operational attendance metrics and team check-in breakdown."""
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    capacity_limit: Optional[int] = None
    current_confirmed_count: int
    current_attended_count: int
    attendance_percentage: float
    total_individual_registrations: int
    total_team_registrations: int
    total_participants_registered: int
    teams_fully_attended: int
    teams_partially_attended: int
    teams_absent: int

