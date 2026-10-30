"""
CampusOps — Slice 5B: Participant Registration, Ticketing & Check-In Domain Foundation Test Suite

Validates:
1. Individual registration lifecycle (registration, participant, ticket issuance, capacity reservation).
2. Team registration lifecycle (distinct participants, individual admission passes, atomic team capacity).
3. Shared email policy (Section 3 of Prompt 19 & PRD v1.1 FA-007: no merging solely on email).
4. Intra-team duplicate rejection.
5. Team size boundaries (min/max validation).
6. Capacity limits, atomic conditional reservation, full-team admission or complete rejection.
7. Waitlist enablement when capacity is exhausted.
8. Registration temporal windows and master kill-switch closure.
9. Registration cancellation and capacity restoration.
10. Idempotency handling for repeated submissions.
11. Ticket credential hashing, absence of raw token persistence, and constant-time verification.
12. Ticket revocation, invalidation, and replacement pass issuance.
13. Individual attendance rule for team members (checking in one member leaves others unchecked).
14. Duplicate scan idempotency (second scan returns already checked in without inflating counter).
15. Manual search check-in path.
16. Check-in void permissions (desk staff denied; manager permitted with >=10 char reason, audit ledger).
17. Tiered privacy disclosure and contact information masking.
18. Multi-tenant and sibling-event scope isolation.
19. Direct database engine constraint enforcement (composite FKs, partial unique indexes, checks).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event, EventLeadAssignment, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.registration import (
    CheckIn,
    CheckInCorrection,
    EventRegistrationSettings,
    Participant,
    Registration,
    RegistrationParticipant,
    Ticket,
)
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.services.errors import (
    AlreadyCheckedInError,
    CapacityExhaustedError,
    CheckInCorrectionError,
    CheckInError,
    CheckInNotFoundError,
    DuplicateRegistrationError,
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
    cancel_registration,
    check_in_participant,
    correct_or_void_check_in,
    create_individual_registration,
    create_team_registration,
    get_event_roster_participants,
    get_or_create_registration_settings,
    issue_replacement_ticket,
    revoke_ticket,
    update_registration_settings,
    verify_ticket_pass,
)


# =========================================================================
# Test Helpers & Fixtures
# =========================================================================

def _create_user(db: Session, email: str, display_name: str) -> UserProfile:
    user = UserProfile(
        auth_subject_id=f"auth0|{uuid.uuid4()}",
        email_normalized=email.lower().strip(),
        display_name=display_name,
        account_status="active",
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()
    return user


def _create_org(db: Session, creator: UserProfile, club_name: str = "Test Club") -> Organization:
    org = Organization(
        college_name="Apex University",
        club_name=club_name,
        verification_status="verified",
        created_by_user_id=creator.id,
    )
    db.add(org)
    db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        membership_status="active",
    )
    db.add(membership)
    db.flush()

    role = RoleAssignment(
        membership_id=membership.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
        scope_id=None,
    )
    db.add(role)
    db.flush()
    return org


def _add_member(
    db: Session, org: Organization, user: UserProfile, role_name: str, scope_type: str = "organization", scope_id: uuid.UUID = None
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        membership_status="active",
    )
    db.add(membership)
    db.flush()

    role = RoleAssignment(
        membership_id=membership.id,
        role_name=role_name,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    db.add(role)
    db.flush()
    return membership


def _create_event(db: Session, org: Organization, creator: UserProfile, name: str = "Tech Fest 2026") -> Event:
    event = Event(
        organization_id=org.id,
        name=name,
        status="published",
        created_by_user_id=creator.id,
        timezone="Asia/Kolkata",
    )
    db.add(event)
    db.flush()
    return event


# =========================================================================
# 1. Individual Registration Lifecycle
# =========================================================================

def test_individual_registration_lifecycle(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10)

    result = create_individual_registration(
        db,
        organization_id=org.id,
        event_id=event.id,
        full_name="Aarav Sharma",
        email="aarav@univ.edu",
        phone_number="+91 9876543210",
        college_name="Engineering College",
        student_id="CS-2026-001",
    )

    assert result.is_waitlisted is False
    assert result.registration.registration_status == "confirmed"
    assert result.registration.registration_type == "individual"
    assert result.registration.contact_email == "aarav@univ.edu"
    assert result.registration.confirmation_code.startswith("REG-")

    assert len(result.participants) == 1
    p = result.participants[0]
    assert p.full_name == "Aarav Sharma"
    assert p.email_normalized == "aarav@univ.edu"
    assert p.status == "registered"

    assert len(result.issued_tickets) == 1
    ticket_dto = result.issued_tickets[0]
    assert ticket_dto.raw_pass_token.startswith("CO-PASS-")
    assert ticket_dto.ticket.status == "issued"
    assert len(ticket_dto.ticket.pass_code_hash) == 64

    # Verify raw token is NOT in database
    db_ticket = db.get(Ticket, ticket_dto.ticket.id)
    assert not hasattr(db_ticket, "pass_code")
    assert db_ticket.pass_code_hash == ticket_dto.ticket.pass_code_hash

    # Verify capacity accounting
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 1
    assert settings.current_attended_count == 0


# =========================================================================
# 2. Team Registration Lifecycle
# =========================================================================

def test_team_registration_lifecycle(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10, team_size_min=2, team_size_max=4)

    members_payload = [
        {"full_name": "Rohan Gupta", "email": "rohan@univ.edu", "is_primary_contact": True, "team_role": "leader"},
        {"full_name": "Priya Nair", "email": "priya@univ.edu", "team_role": "member"},
        {"full_name": "Vikram Patel", "email": "vikram@univ.edu", "team_role": "member"},
    ]

    result = create_team_registration(
        db,
        organization_id=org.id,
        event_id=event.id,
        team_name="CyberWarriors",
        members=members_payload,
        contact_email="rohan@univ.edu",
    )

    assert result.is_waitlisted is False
    assert result.registration.registration_status == "confirmed"
    assert result.registration.registration_type == "team"
    assert result.registration.team_name == "CyberWarriors"

    assert len(result.participants) == 3
    # Check that each participant has an individual unique ID
    part_ids = {p.id for p in result.participants}
    assert len(part_ids) == 3

    assert len(result.issued_tickets) == 3
    ticket_ids = {t.ticket.id for t in result.issued_tickets}
    assert len(ticket_ids) == 3

    # Verify capacity accounting: 3 slots consumed
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 3


# =========================================================================
# 3. Shared Email Policy (PRD v1.1 FA-007 & Prompt 19 Section 3)
# =========================================================================

def test_shared_email_creates_distinct_participants(db: Session):
    """
    Verifies that distinct humans sharing an email address (family, lab, or mentor)
    receive separate, individually identifiable participant records and tickets.
    System must NEVER merge two participants solely on email.
    """
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10)

    # Participant 1
    res1 = create_individual_registration(
        db,
        organization_id=org.id,
        event_id=event.id,
        full_name="Alice Smith",
        email="family.shared@example.com",
    )
    p1 = res1.participants[0]

    # Participant 2 with the same email
    res2 = create_individual_registration(
        db,
        organization_id=org.id,
        event_id=event.id,
        full_name="Bob Smith",
        email="family.shared@example.com",
    )
    p2 = res2.participants[0]

    # Must be distinct participants
    assert p1.id != p2.id
    assert p1.full_name == "Alice Smith"
    assert p2.full_name == "Bob Smith"
    assert p1.email_normalized == p2.email_normalized

    # Both must hold separate admission passes
    assert res1.issued_tickets[0].ticket.id != res2.issued_tickets[0].ticket.id

    # Capacity must reflect both individuals
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 2


# =========================================================================
# 4. Intra-Team Duplicate Rejection
# =========================================================================

def test_intra_team_duplicate_member_rejected(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10)

    members_payload = [
        {"full_name": "Rohan Gupta", "email": "rohan@univ.edu"},
        {"full_name": "Rohan Gupta", "email": "rohan@univ.edu"},  # Duplicate
    ]

    with pytest.raises(DuplicateRegistrationError, match="Duplicate team member detected"):
        create_team_registration(
            db,
            organization_id=org.id,
            event_id=event.id,
            team_name="Duos",
            members=members_payload,
            contact_email="rohan@univ.edu",
        )


# =========================================================================
# 5. Team Size Boundary Validation
# =========================================================================

def test_team_size_boundaries(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, team_size_min=2, team_size_max=3)

    # 1 member -> below min 2
    with pytest.raises(InvalidTeamSizeError, match="outside allowed bounds"):
        create_team_registration(
            db,
            organization_id=org.id,
            event_id=event.id,
            team_name="SoloTeam",
            members=[{"full_name": "Alice", "email": "a@univ.edu"}],
            contact_email="a@univ.edu",
        )

    # 4 members -> above max 3
    with pytest.raises(InvalidTeamSizeError, match="outside allowed bounds"):
        create_team_registration(
            db,
            organization_id=org.id,
            event_id=event.id,
            team_name="LargeTeam",
            members=[
                {"full_name": "Alice", "email": "a@univ.edu"},
                {"full_name": "Bob", "email": "b@univ.edu"},
                {"full_name": "Charlie", "email": "c@univ.edu"},
                {"full_name": "Dave", "email": "d@univ.edu"},
            ],
            contact_email="a@univ.edu",
        )


# =========================================================================
# 6. Capacity Limit & Full-Team Admission
# =========================================================================

def test_capacity_limit_and_atomic_reservation(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    # Capacity limit is 3, waitlist disabled
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=3, waitlist_enabled=False)

    # Register solo 1 -> capacity 1/3
    create_individual_registration(db, org.id, event.id, "Alice", "alice@univ.edu")

    # Team of 3 requires 3 slots, but only 2 remain -> must be completely rejected (never partial!)
    members = [
        {"full_name": "Bob", "email": "b@univ.edu"},
        {"full_name": "Charlie", "email": "c@univ.edu"},
        {"full_name": "Dave", "email": "d@univ.edu"},
    ]
    with pytest.raises(CapacityExhaustedError, match="capacity cannot accommodate 3 participant"):
        create_team_registration(db, org.id, event.id, "Team3", members, "b@univ.edu")

    # Confirmed count remains 1
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 1

    # Team of 2 fits exactly -> capacity 3/3
    team2 = [
        {"full_name": "Bob", "email": "b@univ.edu"},
        {"full_name": "Charlie", "email": "c@univ.edu"},
    ]
    res_team = create_team_registration(db, org.id, event.id, "Team2", team2, "b@univ.edu")
    assert res_team.registration.registration_status == "confirmed"

    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 3

    # Event is now full; next registration rejected
    with pytest.raises(CapacityExhaustedError):
        create_individual_registration(db, org.id, event.id, "Eve", "eve@univ.edu")


# =========================================================================
# 7. Waitlist Enablement
# =========================================================================

def test_waitlist_when_capacity_reached(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    # Capacity 1, waitlist enabled
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=1, waitlist_enabled=True)

    # First registration confirmed
    res1 = create_individual_registration(db, org.id, event.id, "Alice", "alice@univ.edu")
    assert res1.is_waitlisted is False
    assert len(res1.issued_tickets) == 1

    # Second registration waitlisted; no ticket issued
    res2 = create_individual_registration(db, org.id, event.id, "Bob", "bob@univ.edu")
    assert res2.is_waitlisted is True
    assert res2.registration.registration_status == "waitlisted"
    assert len(res2.issued_tickets) == 0

    # Confirmed count remains 1
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 1


# =========================================================================
# 8. Registration Temporal Windows & Master Switch
# =========================================================================

def test_registration_windows_and_closure(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)

    # 1. Closed switch
    get_or_create_registration_settings(db, org.id, event.id, is_open=False)
    with pytest.raises(RegistrationClosedError, match="currently closed"):
        create_individual_registration(db, org.id, event.id, "Alice", "a@univ.edu")

    # 2. Window in future
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    update_registration_settings(db, org.id, event.id, admin, is_open=True, registration_open_at=future_time)
    with pytest.raises(RegistrationWindowError, match="not yet opened"):
        create_individual_registration(db, org.id, event.id, "Alice", "a@univ.edu")

    # 3. Window in past
    past_open = datetime.now(timezone.utc) - timedelta(days=5)
    past_close = datetime.now(timezone.utc) - timedelta(days=1)
    update_registration_settings(db, org.id, event.id, admin, registration_open_at=past_open, registration_close_at=past_close)
    with pytest.raises(RegistrationWindowError, match="already closed"):
        create_individual_registration(db, org.id, event.id, "Alice", "a@univ.edu")


# =========================================================================
# 9. Registration Cancellation & Capacity Restoration
# =========================================================================

def test_registration_cancellation_restores_capacity(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=5)

    res = create_team_registration(
        db,
        org.id,
        event.id,
        "TeamAlpha",
        [{"full_name": "A", "email": "a@univ.edu"}, {"full_name": "B", "email": "b@univ.edu"}],
        "a@univ.edu",
    )
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 2

    # Cancel registration
    cancel_registration(db, org.id, event.id, res.registration.id, "Team requested withdrawal")

    # Confirmed count restored to 0
    db.refresh(settings)
    assert settings.current_confirmed_count == 0

    # Tickets and participants marked cancelled
    db.refresh(res.registration)
    assert res.registration.registration_status == "cancelled"
    for ticket in res.registration.tickets:
        db.refresh(ticket)
        assert ticket.status == "cancelled"
    for rp in res.registration.registration_participants:
        db.refresh(rp.participant)
        assert rp.participant.status == "cancelled"


# =========================================================================
# 10. Idempotent Registration Resubmission
# =========================================================================

def test_idempotent_registration_resubmission(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10)

    res1 = create_individual_registration(
        db, org.id, event.id, "Aarav", "aarav@univ.edu", idempotency_key="req-unique-99"
    )

    # Re-submit with same idempotency key
    res2 = create_individual_registration(
        db, org.id, event.id, "Aarav", "aarav@univ.edu", idempotency_key="req-unique-99"
    )

    assert res1.registration.id == res2.registration.id
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_confirmed_count == 1  # Did NOT double count


# =========================================================================
# 11. Admission Pass Verification & Constant-Time Security
# =========================================================================

def test_ticket_pass_verification(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event1 = _create_event(db, org, admin, "Event 1")
    event2 = _create_event(db, org, admin, "Event 2")
    get_or_create_registration_settings(db, org.id, event1.id)
    get_or_create_registration_settings(db, org.id, event2.id)

    res = create_individual_registration(db, org.id, event1.id, "Aarav", "aarav@univ.edu")
    raw_token = res.issued_tickets[0].raw_pass_token

    # 1. Valid token against event 1
    ticket, participant = verify_ticket_pass(db, org.id, event1.id, raw_token)
    assert ticket.id == res.issued_tickets[0].ticket.id
    assert participant.full_name == "Aarav"

    # 2. Token presented at Event 2 -> Rejected
    with pytest.raises(TicketNotFoundError):
        verify_ticket_pass(db, org.id, event2.id, raw_token)

    # 3. Tampered token -> Rejected
    with pytest.raises(TicketNotFoundError):
        verify_ticket_pass(db, org.id, event1.id, raw_token + "TAMPER")


# =========================================================================
# 12. Ticket Revocation and Replacement
# =========================================================================

def test_ticket_revocation_and_replacement(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)

    res = create_individual_registration(db, org.id, event.id, "Aarav", "aarav@univ.edu")
    orig_ticket = res.issued_tickets[0].ticket
    orig_token = res.issued_tickets[0].raw_pass_token

    # Revoke ticket
    revoke_ticket(db, org.id, event.id, orig_ticket.id, "Compromised pass", admin)
    with pytest.raises(TicketRevokedError, match="Ticket has been revoked"):
        verify_ticket_pass(db, org.id, event.id, orig_token)

    # Issue replacement
    replacement = issue_replacement_ticket(db, org.id, event.id, res.participants[0].id, admin, "Issued new QR")
    assert replacement.ticket.id != orig_ticket.id
    assert replacement.raw_pass_token != orig_token

    # Verify replacement works
    t, p = verify_ticket_pass(db, org.id, event.id, replacement.raw_pass_token)
    assert t.id == replacement.ticket.id


# =========================================================================
# 13. Individual Attendance Rule for Team Members (CO-FR-009, FA-005)
# =========================================================================

def test_individual_check_in_for_team_member(db: Session):
    """
    Verifies that checking in one team member marks ONLY that specific individual
    as attended. Other team members remain unchecked.
    """
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    volunteer = _create_user(db, "desk@univ.edu", "Desk Volunteer")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id, capacity_limit=10)

    # Assign desk volunteer REGISTRATION_STAFF role for this event
    _add_member(db, org, volunteer, "REGISTRATION_STAFF", scope_type="event", scope_id=event.id)

    res = create_team_registration(
        db,
        org.id,
        event.id,
        "Hackers",
        [{"full_name": "Member1", "email": "m1@univ.edu"}, {"full_name": "Member2", "email": "m2@univ.edu"}],
        "m1@univ.edu",
    )
    m1_ticket_dto = res.issued_tickets[0]
    m2_ticket_dto = res.issued_tickets[1]

    # Check in Member 1
    check_in, is_dup = check_in_participant(
        db, org.id, event.id, volunteer, raw_token=m1_ticket_dto.raw_pass_token, station_id="NORTH-DESK"
    )

    assert is_dup is False
    assert check_in.check_in_status == "valid"
    assert check_in.participant_id == res.participants[0].id

    # Member 1 status updated
    db.refresh(res.participants[0])
    assert res.participants[0].status == "attended"

    # Member 2 MUST REMAIN registered (not attended!)
    db.refresh(res.participants[1])
    assert res.participants[1].status == "registered"

    # Settings attended counter is 1
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_attended_count == 1


# =========================================================================
# 14. Duplicate Scan Idempotency
# =========================================================================

def test_duplicate_scan_idempotency(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)

    res = create_individual_registration(db, org.id, event.id, "Aarav", "aarav@univ.edu")
    raw_token = res.issued_tickets[0].raw_pass_token

    # First scan
    ci1, dup1 = check_in_participant(db, org.id, event.id, admin, raw_token=raw_token)
    assert dup1 is False
    assert ci1.check_in_status == "valid"

    # Second scan with same token
    ci2, dup2 = check_in_participant(db, org.id, event.id, admin, raw_token=raw_token)
    assert dup2 is True
    assert ci2.id == ci1.id

    # Attended count must remain 1
    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_attended_count == 1


# =========================================================================
# 15. Manual Search Check-In
# =========================================================================

def test_manual_search_check_in(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)

    res = create_individual_registration(db, org.id, event.id, "Aarav", "aarav@univ.edu")
    participant_id = res.participants[0].id

    # Manual search check in without QR token
    check_in, is_dup = check_in_participant(
        db, org.id, event.id, admin, participant_id=participant_id, method="manual_search"
    )
    assert is_dup is False
    assert check_in.method == "manual_search"
    assert check_in.check_in_status == "valid"


# =========================================================================
# 16. Check-In Void Permissions & Audit Ledger (D-SLICE5-04)
# =========================================================================

def test_check_in_void_permission_and_audit(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    volunteer = _create_user(db, "desk@univ.edu", "Desk Volunteer")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)

    # Assign volunteer REGISTRATION_STAFF
    _add_member(db, org, volunteer, "REGISTRATION_STAFF", scope_type="event", scope_id=event.id)

    res = create_individual_registration(db, org.id, event.id, "Aarav", "aarav@univ.edu")
    ci, _ = check_in_participant(db, org.id, event.id, volunteer, raw_token=res.issued_tickets[0].raw_pass_token)

    settings = db.get(EventRegistrationSettings, event.id)
    assert settings.current_attended_count == 1

    # 1. Desk Volunteer attempts to void -> REJECTED (PermissionDeniedError)
    with pytest.raises(PermissionDeniedError):
        correct_or_void_check_in(db, org.id, event.id, ci.id, "Accidental scan", volunteer)

    # 2. Manager with short reason (< 10 chars) -> REJECTED (CheckInCorrectionError)
    with pytest.raises(CheckInCorrectionError, match="at least 10 characters"):
        correct_or_void_check_in(db, org.id, event.id, ci.id, "Mistake", admin)

    # 3. Manager voids with valid explanation (>= 10 chars) -> SUCCEEDS
    voided_ci, correction = correct_or_void_check_in(
        db, org.id, event.id, ci.id, "Accidental manual check-in of wrong attendee; attendee not present.", admin
    )

    assert voided_ci.check_in_status == "voided"
    assert voided_ci.voided_by_user_id == admin.id
    assert correction.previous_status == "valid"
    assert correction.new_status == "voided"
    assert correction.corrected_by_user_id == admin.id

    # Ticket and participant reverted
    db.refresh(res.participants[0])
    assert res.participants[0].status == "registered"

    # Attended count decremented back to 0
    db.refresh(settings)
    assert settings.current_attended_count == 0

    # Attendee can now be legitimately checked in again
    ci_new, dup_new = check_in_participant(db, org.id, event.id, admin, raw_token=res.issued_tickets[0].raw_pass_token)
    assert dup_new is False
    assert ci_new.check_in_status == "valid"
    assert ci_new.id != ci.id


# =========================================================================
# 17. Tiered Privacy Disclosure & Contact Masking
# =========================================================================

def test_roster_privacy_and_contact_masking(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    volunteer = _create_user(db, "desk@univ.edu", "Desk Volunteer")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)

    _add_member(db, org, volunteer, "REGISTRATION_STAFF", scope_type="event", scope_id=event.id)

    create_individual_registration(
        db, org.id, event.id, "Aarav Sharma", "aarav.sharma@example.com", phone_number="+91 9876543210"
    )

    # 1. Volunteer view: contact info is masked
    roster_volunteer = get_event_roster_participants(db, org.id, event.id, volunteer, include_unmasked_contact=False)
    assert len(roster_volunteer) == 1
    assert roster_volunteer[0]["full_name"] == "Aarav Sharma"
    assert roster_volunteer[0]["email"] == "a***a@example.com"
    assert "*" in roster_volunteer[0]["phone_number"]

    # 2. Volunteer requesting unmasked contact -> still masked because volunteer lacks ACTION_VIEW_ATTENDEE_CONTACT
    roster_volunteer_unmasked = get_event_roster_participants(db, org.id, event.id, volunteer, include_unmasked_contact=True)
    assert roster_volunteer_unmasked[0]["email"] == "a***a@example.com"

    # 3. Admin view with unmasked contact enabled -> full contact info exposed
    roster_admin = get_event_roster_participants(db, org.id, event.id, admin, include_unmasked_contact=True)
    assert roster_admin[0]["email"] == "aarav.sharma@example.com"
    assert roster_admin[0]["phone_number"] == "+91 9876543210"


# =========================================================================
# 18. Multi-Tenant and Sibling-Event Scope Isolation
# =========================================================================

def test_sibling_event_and_alien_organization_isolation(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    lead_user = _create_user(db, "lead@univ.edu", "Event Lead User")
    org = _create_org(db, admin)

    prog = Program(
        organization_id=org.id,
        name="Annual Fest",
        created_by_user_id=admin.id,
    )
    db.add(prog)
    db.flush()

    event1 = Event(organization_id=org.id, program_id=prog.id, name="Hackathon", created_by_user_id=admin.id)
    event2 = Event(organization_id=org.id, program_id=prog.id, name="Robotics", created_by_user_id=admin.id)
    db.add_all([event1, event2])
    db.flush()

    # Assign lead to event1 only
    lead_mem = _add_member(db, org, lead_user, "EVENT_LEAD", scope_type="event", scope_id=event1.id)
    lead_assign = EventLeadAssignment(
        organization_id=org.id,
        event_id=event1.id,
        membership_id=lead_mem.id,
        assigned_by_user_id=admin.id,
    )
    db.add(lead_assign)
    db.flush()

    get_or_create_registration_settings(db, org.id, event1.id)
    get_or_create_registration_settings(db, org.id, event2.id)

    # Lead can manage registration settings for event1
    update_registration_settings(db, org.id, event1.id, lead_user, capacity_limit=25)

    # Lead CANNOT manage registration settings for sibling event2 (PermissionDeniedError)
    with pytest.raises(PermissionDeniedError):
        update_registration_settings(db, org.id, event2.id, lead_user, capacity_limit=50)

    # Lead CANNOT view roster for sibling event2
    with pytest.raises(PermissionDeniedError):
        get_event_roster_participants(db, org.id, event2.id, lead_user)


# =========================================================================
# 19. Direct Database Engine Constraints
# =========================================================================

def test_database_constraints_direct(db: Session):
    admin = _create_user(db, "admin@univ.edu", "Admin User")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin)
    get_or_create_registration_settings(db, org.id, event.id)
    res = create_individual_registration(db, org.id, event.id, "Aarav", "aarav@univ.edu")
    participant = res.participants[0]
    ticket = res.issued_tickets[0].ticket

    # 1. Partial Unique Index: uq_ticket_participant_active
    # Attempting to insert a second active ('issued') ticket directly for the same participant must fail
    dup_ticket = Ticket(
        organization_id=org.id,
        event_id=event.id,
        participant_id=participant.id,
        registration_id=res.registration.id,
        ticket_reference="TKT-DUP",
        pass_code_hash="hash-dup-1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
        status="issued",
    )
    with db.begin_nested():
        db.add(dup_ticket)
        with pytest.raises(IntegrityError):
            db.flush()

    # 2. Check constraint: check_in_corrections.reason minimum length (>= 10 chars)
    ci = CheckIn(
        organization_id=org.id,
        event_id=event.id,
        participant_id=participant.id,
        ticket_id=ticket.id,
        check_in_status="valid",
        checked_in_by_user_id=admin.id,
    )
    db.add(ci)
    db.flush()

    invalid_correction = CheckInCorrection(
        check_in_id=ci.id,
        previous_status="valid",
        new_status="voided",
        reason="Short",  # < 10 chars
        corrected_by_user_id=admin.id,
    )
    with db.begin_nested():
        db.add(invalid_correction)
        with pytest.raises(IntegrityError):
            db.flush()

    # 3. Partial Unique Index: uq_check_in_event_participant
    # Attempting to insert a second valid check-in for the same participant in the same event must fail
    dup_ci = CheckIn(
        organization_id=org.id,
        event_id=event.id,
        participant_id=participant.id,
        ticket_id=ticket.id,
        check_in_status="valid",
        checked_in_by_user_id=admin.id,
    )
    with db.begin_nested():
        db.add(dup_ci)
        with pytest.raises(IntegrityError):
            db.flush()

    # 4. Composite Foreign Key: mismatched organization_id between event and registration
    alien_org = _create_org(db, admin, club_name="Alien Club")
    mismatched_reg = Registration(
        organization_id=alien_org.id,  # Alien organization
        event_id=event.id,              # Event belongs to org.id
        registration_type="individual",
        registration_status="confirmed",
        contact_email="alien@univ.edu",
        confirmation_code="REG-MISMATCH",
    )
    with db.begin_nested():
        db.add(mismatched_reg)
        with pytest.raises(IntegrityError):
            db.flush()
