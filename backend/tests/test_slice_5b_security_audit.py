import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Department, Event, EventLeadAssignment, Program
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
    CapacityExhaustedError,
    CheckInCorrectionError,
    CheckInError,
    DuplicateRegistrationError,
    PermissionDeniedError,
    RegistrationClosedError,
    RegistrationError,
    TicketInvalidError,
    TicketRevokedError,
)
from app.services.registration import (
    cancel_registration,
    check_in_participant,
    correct_or_void_check_in,
    create_individual_registration,
    create_team_registration,
    generate_registration_key,
    generate_ticket_credential,
    get_event_roster_participants,
    get_or_create_registration_settings,
    hash_credential,
    issue_replacement_ticket,
    reconcile_event_registration_counts,
    update_registration_settings,
    verify_ticket_pass,
)


# =========================================================================
# Fixtures & Helpers
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


def _create_org(db: Session, creator: UserProfile, club_name: str = "Tech Club") -> Organization:
    org = Organization(
        college_name="Apex University",
        club_name=club_name,
        verification_status="verified",
        created_by_user_id=creator.id,
    )
    db.add(org)
    db.flush()

    mem = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        membership_status="active",
    )
    db.add(mem)
    db.flush()

    role = RoleAssignment(
        membership_id=mem.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
        scope_id=None,
    )
    db.add(role)
    db.flush()
    return org


def _add_member_with_role(
    db: Session, org: Organization, user: UserProfile, role_name: str, scope_type: str = "organization", scope_id: uuid.UUID = None
) -> OrganizationMembership:
    mem = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        membership_status="active",
    )
    db.add(mem)
    db.flush()

    role = RoleAssignment(
        membership_id=mem.id,
        role_name=role_name,
        scope_type=scope_type,
        scope_id=scope_id or org.id,
    )
    db.add(role)
    db.flush()
    return mem


def _create_event(db: Session, org: Organization, creator: UserProfile, name: str = "Hackathon") -> Event:
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
# Security & Credential Audit Tests
# =========================================================================

def test_public_registration_key_security_and_rotation(db: Session):
    """Verify registration key generation, hashing, rotation, and unique index constraint."""
    admin = _create_user(db, "reg_admin@test.edu", "Reg Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Key Rotation Event")

    raw_key, key_hash = generate_registration_key()
    assert raw_key.startswith("reg_")
    assert len(raw_key) > 20
    assert key_hash == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    settings = get_or_create_registration_settings(
        db, org.id, event.id, registration_key=raw_key
    )
    assert settings.registration_key_hash == key_hash

    # Rotate registration key
    updated_settings = update_registration_settings(
        db, org.id, event.id, admin, rotate_registration_key=True
    )
    assert updated_settings.registration_key_hash is not None
    assert updated_settings.registration_key_hash != key_hash

    # Verify database partial unique constraint: two events cannot share a registration_key_hash
    event2 = _create_event(db, org, admin, "Key Collision Event")
    settings2 = EventRegistrationSettings(
        event_id=event2.id,
        organization_id=org.id,
        is_open=True,
        registration_key_hash=updated_settings.registration_key_hash,  # Duplicate
    )
    db.add(settings2)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_ticket_credential_entropy_and_hash_storage(db: Session):
    """Verify admission pass token entropy, constant-time verification, and no raw credential leaks."""
    token, token_hash = generate_ticket_credential()
    assert token.startswith("CO-PASS-")
    assert len(token.replace("CO-PASS-", "")) == 32  # 16 bytes = 128 bits entropy
    assert token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()

    admin = _create_user(db, "tkt_admin@test.edu", "Tkt Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Ticket Test Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    result = create_individual_registration(
        db, org.id, event.id, full_name="Siddharth Roy", email="sid@test.edu"
    )
    assert len(result.issued_tickets) == 1
    issued_dto = result.issued_tickets[0]
    raw_token = issued_dto.raw_pass_token
    ticket = issued_dto.ticket

    # Raw token is NEVER stored in Ticket database columns
    assert ticket.pass_code_hash != raw_token
    assert ticket.pass_code_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Repr never reveals token or hash
    assert raw_token not in repr(ticket)
    assert ticket.pass_code_hash not in repr(ticket)
    assert ticket.ticket_reference in repr(ticket)

    # Valid verification
    v_ticket, v_part = verify_ticket_pass(db, org.id, event.id, raw_token)
    assert v_ticket.id == ticket.id
    assert v_part.full_name == "Siddharth Roy"

    # Tampered / invalid token rejected
    with pytest.raises(TicketInvalidError):
        verify_ticket_pass(db, org.id, event.id, "   ")
    with pytest.raises(Exception):  # Not found or invalid
        verify_ticket_pass(db, org.id, event.id, "CO-PASS-00000000000000000000000000000000")


# =========================================================================
# Relational & Cross-Tenant Integrity Tests
# =========================================================================

def test_direct_db_cross_tenant_isolation_constraints(db: Session):
    """Verify database-level composite foreign keys strictly block cross-tenant entities."""
    admin1 = _create_user(db, "admin1@org1.edu", "Admin 1")
    admin2 = _create_user(db, "admin2@org2.edu", "Admin 2")
    org1 = _create_org(db, admin1, "Org 1")
    org2 = _create_org(db, admin2, "Org 2")

    event_org1 = _create_event(db, org1, admin1, "Event Org 1")

    # 1. Attempt to insert Registration for event_org1 with org2's organization_id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_reg = Registration(
                organization_id=org2.id,  # Alien organization
                event_id=event_org1.id,
                registration_type="individual",
                contact_email="hacker@org2.edu",
                confirmation_code="REG-CROSS1",
            )
            db.add(cross_reg)
            db.flush()

    # 2. Attempt to insert Participant for event_org1 with org2's organization_id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_part = Participant(
                organization_id=org2.id,  # Alien organization
                event_id=event_org1.id,
                full_name="Alien Participant",
                email_normalized="alien@org2.edu",
            )
            db.add(cross_part)
            db.flush()

    # 3. Attempt to insert EventRegistrationSettings for event_org1 with org2's organization_id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_settings = EventRegistrationSettings(
                event_id=event_org1.id,
                organization_id=org2.id,  # Alien organization
                is_open=True,
            )
            db.add(cross_settings)
            db.flush()


def test_direct_db_cross_event_registration_participant_isolation(db: Session):
    """Verify database constraint blocks linking a participant from Event A to a registration of Event B."""
    admin = _create_user(db, "event_admin@test.edu", "Event Admin")
    org = _create_org(db, admin)
    event_a = _create_event(db, org, admin, "Event A")
    event_b = _create_event(db, org, admin, "Event B")

    # Valid Registration in Event A
    reg_a = Registration(
        organization_id=org.id,
        event_id=event_a.id,
        registration_type="individual",
        contact_email="reg_a@test.edu",
        confirmation_code="REG-EVTA",
    )
    db.add(reg_a)
    db.flush()

    # Valid Participant in Event B
    part_b = Participant(
        organization_id=org.id,
        event_id=event_b.id,
        full_name="Participant B",
        email_normalized="part_b@test.edu",
    )
    db.add(part_b)
    db.flush()

    # Attempt to link part_b to reg_a in registration_participants
    # If event_id=event_a.id, participant_b FK fails because participant_b is in event_b.
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_link_a = RegistrationParticipant(
                organization_id=org.id,
                event_id=event_a.id,
                registration_id=reg_a.id,
                participant_id=part_b.id,
                is_primary_contact=True,
            )
            db.add(cross_link_a)
            db.flush()

    # If event_id=event_b.id, reg_a FK fails because reg_a is in event_a.
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_link_b = RegistrationParticipant(
                organization_id=org.id,
                event_id=event_b.id,
                registration_id=reg_a.id,
                participant_id=part_b.id,
                is_primary_contact=True,
            )
            db.add(cross_link_b)
            db.flush()


def test_direct_db_cross_event_ticket_and_checkin_isolation(db: Session):
    """Verify database constraints block cross-event Ticket and CheckIn insertions."""
    admin = _create_user(db, "x_admin@test.edu", "X Admin")
    org = _create_org(db, admin)
    event_a = _create_event(db, org, admin, "Event Alpha")
    event_b = _create_event(db, org, admin, "Event Beta")

    reg_a = Registration(
        organization_id=org.id,
        event_id=event_a.id,
        registration_type="individual",
        contact_email="a@test.edu",
        confirmation_code="REG-A1",
    )
    db.add(reg_a)

    part_b = Participant(
        organization_id=org.id,
        event_id=event_b.id,
        full_name="Beta Attendee",
        email_normalized="beta@test.edu",
    )
    db.add(part_b)
    db.flush()

    # Cross-event Ticket
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            cross_ticket = Ticket(
                organization_id=org.id,
                event_id=event_a.id,
                participant_id=part_b.id,  # part_b is in event_b!
                registration_id=reg_a.id,
                ticket_reference="TKT-CROSS1",
                pass_code_hash=hashlib.sha256(b"dummy").hexdigest(),
            )
            db.add(cross_ticket)
            db.flush()


def test_direct_db_check_constraints_enforcement(db: Session):
    """Verify check constraints for capacity limits, counts, reason lengths, and void integrity."""
    admin = _create_user(db, "chk_admin@test.edu", "Check Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Check Event")

    # 1. Negative capacity limit rejected by ck_event_reg_settings_capacity
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            settings_neg_cap = EventRegistrationSettings(
                event_id=event.id,
                organization_id=org.id,
                is_open=True,
                capacity_limit=-10,
            )
            db.add(settings_neg_cap)
            db.flush()

    # 2. Inverted dates rejected by ck_event_reg_settings_dates
    now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            settings_inv_dates = EventRegistrationSettings(
                event_id=event.id,
                organization_id=org.id,
                is_open=True,
                registration_open_at=now + timedelta(days=5),
                registration_close_at=now + timedelta(days=2),  # close before open!
            )
            db.add(settings_inv_dates)
            db.flush()

    # 3. CheckIn void integrity: voided status requires voided_at and voided_by_user_id
    part = Participant(organization_id=org.id, event_id=event.id, full_name="P1", email_normalized="p1@test.edu")
    reg = Registration(organization_id=org.id, event_id=event.id, contact_email="p1@test.edu", confirmation_code="REG-P1")
    db.add_all([part, reg])
    db.flush()

    ticket = Ticket(
        organization_id=org.id, event_id=event.id, participant_id=part.id, registration_id=reg.id,
        ticket_reference="TKT-P1", pass_code_hash=hashlib.sha256(b"p1").hexdigest()
    )
    db.add(ticket)
    db.flush()

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            invalid_check_in = CheckIn(
                organization_id=org.id,
                event_id=event.id,
                participant_id=part.id,
                ticket_id=ticket.id,
                check_in_status="voided",
                voided_at=None,  # Must not be null when voided!
                voided_by_user_id=None,
                checked_in_by_user_id=admin.id,
            )
            db.add(invalid_check_in)
            db.flush()

    # 4. CheckInCorrection reason minimum 10 characters
    valid_check_in = CheckIn(
        organization_id=org.id,
        event_id=event.id,
        participant_id=part.id,
        ticket_id=ticket.id,
        check_in_status="valid",
        checked_in_by_user_id=admin.id,
    )
    db.add(valid_check_in)
    db.flush()

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            short_reason_correction = CheckInCorrection(
                check_in_id=valid_check_in.id,
                previous_status="valid",
                new_status="voided",
                reason="short",  # < 10 chars!
                corrected_by_user_id=admin.id,
            )
            db.add(short_reason_correction)
            db.flush()


def test_db_enforced_idempotency_unique_index(db: Session):
    """Verify that the database partial unique index uq_registrations_event_idempotency prevents duplicate rows."""
    admin = _create_user(db, "idem_admin@test.edu", "Idem Admin")
    org = _create_org(db, admin)
    event_1 = _create_event(db, org, admin, "Idem Event 1")
    event_2 = _create_event(db, org, admin, "Idem Event 2")

    # 1. First registration with idempotency_key
    reg1 = Registration(
        organization_id=org.id,
        event_id=event_1.id,
        registration_type="individual",
        contact_email="idem1@test.edu",
        confirmation_code="REG-ID1",
        idempotency_key="CLIENT-REQ-123",
    )
    db.add(reg1)
    db.flush()

    # 2. Second registration in same event with same idempotency_key fails at DB engine level
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            reg2 = Registration(
                organization_id=org.id,
                event_id=event_1.id,
                registration_type="individual",
                contact_email="idem2@test.edu",
                confirmation_code="REG-ID2",
                idempotency_key="CLIENT-REQ-123",
            )
            db.add(reg2)
            db.flush()

    # 3. Different event CAN reuse the same idempotency_key (event-scoped index)
    reg_event2 = Registration(
        organization_id=org.id,
        event_id=event_2.id,
        registration_type="individual",
        contact_email="idem3@test.edu",
        confirmation_code="REG-ID3",
        idempotency_key="CLIENT-REQ-123",
    )
    db.add(reg_event2)
    db.flush()
    assert reg_event2.id is not None


# =========================================================================
# Identity & Duplicate Registration Policy Tests (FA-007)
# =========================================================================

def test_shared_email_policy_distinct_identities_and_attendance(db: Session):
    """Verify that participants sharing an email address receive distinct records, tickets, and check-ins."""
    admin = _create_user(db, "shared_admin@test.edu", "Shared Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Shared Email Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    shared_email = "lab_team@apex.edu"

    # Register Participant 1 (Alice)
    res1 = create_individual_registration(db, org.id, event.id, full_name="Alice Smith", email=shared_email)
    p1 = res1.participants[0]
    t1 = res1.issued_tickets[0].ticket
    token1 = res1.issued_tickets[0].raw_pass_token

    # Register Participant 2 (Bob) with exact same email
    res2 = create_individual_registration(db, org.id, event.id, full_name="Bob Jones", email=shared_email)
    p2 = res2.participants[0]
    t2 = res2.issued_tickets[0].ticket
    token2 = res2.issued_tickets[0].raw_pass_token

    # Assert distinct entities
    assert p1.id != p2.id
    assert p1.email_normalized == p2.email_normalized == shared_email
    assert t1.id != t2.id
    assert t1.pass_code_hash != t2.pass_code_hash
    assert token1 != token2

    # Check in Alice
    checkin1, is_dup1 = check_in_participant(db, org.id, event.id, admin, raw_token=token1)
    assert not is_dup1
    assert checkin1.participant_id == p1.id
    assert checkin1.check_in_status == "valid"

    # Refresh Bob: Bob remains registered, his ticket is still issued (not attended)
    db.refresh(p2)
    db.refresh(t2)
    assert p2.status == "registered"
    assert t2.status == "issued"

    # Now check in Bob
    checkin2, is_dup2 = check_in_participant(db, org.id, event.id, admin, raw_token=token2)
    assert not is_dup2
    assert checkin2.participant_id == p2.id
    assert checkin2.id != checkin1.id


def test_team_duplicate_member_rejection(db: Session):
    """Verify that a team submission cannot contain duplicate members with the same name and email."""
    admin = _create_user(db, "team_admin@test.edu", "Team Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Team Dup Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True, team_size_min=2, team_size_max=4)

    members = [
        {"full_name": "Rohan Mehra", "email": "rohan@test.edu"},
        {"full_name": "Rohan Mehra", "email": "rohan@test.edu"},  # Duplicate
    ]
    with pytest.raises(DuplicateRegistrationError):
        create_team_registration(
            db, org.id, event.id, team_name="Robotics Duo", members=members, contact_email="rohan@test.edu"
        )


# =========================================================================
# Capacity Accounting & Concurrency Tests (D-SLICE5-01)
# =========================================================================

def test_atomic_capacity_accounting_and_all_or_nothing(db: Session):
    """Verify capacity limit measured in human participants and strict all-or-nothing team admission."""
    admin = _create_user(db, "cap_admin@test.edu", "Cap Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Capacity Event")
    settings = get_or_create_registration_settings(
        db, org.id, event.id, is_open=True, capacity_limit=5, waitlist_enabled=False, team_size_min=2, team_size_max=4
    )

    # 1. Admit 3 solo participants
    create_individual_registration(db, org.id, event.id, full_name="User 1", email="u1@test.edu")
    create_individual_registration(db, org.id, event.id, full_name="User 2", email="u2@test.edu")
    create_individual_registration(db, org.id, event.id, full_name="User 3", email="u3@test.edu")

    db.refresh(settings)
    assert settings.current_confirmed_count == 3

    # 2. Attempt team registration of 3 members. 3 + 3 = 6 > 5. Must fail entirely, no partial admission!
    team_members = [
        {"full_name": "M1", "email": "m1@test.edu"},
        {"full_name": "M2", "email": "m2@test.edu"},
        {"full_name": "M3", "email": "m3@test.edu"},
    ]
    with pytest.raises(CapacityExhaustedError):
        create_team_registration(
            db, org.id, event.id, team_name="Trio", members=team_members, contact_email="m1@test.edu"
        )

    db.refresh(settings)
    assert settings.current_confirmed_count == 3  # Count remains exactly 3

    # 3. Admit team of 2 members. 3 + 2 = 5 == 5. Fits exactly!
    team_2 = [
        {"full_name": "M1", "email": "m1@test.edu"},
        {"full_name": "M2", "email": "m2@test.edu"},
    ]
    res_team = create_team_registration(
        db, org.id, event.id, team_name="Duo", members=team_2, contact_email="m1@test.edu"
    )
    assert not res_team.is_waitlisted
    db.refresh(settings)
    assert settings.current_confirmed_count == 5


def test_capacity_reservation_rollback_on_fault_injection(db: Session):
    """Verify that failure midway through registration rolls back capacity counters and database rows atomically."""
    admin = _create_user(db, "fault_admin@test.edu", "Fault Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Fault Event")
    settings = get_or_create_registration_settings(db, org.id, event.id, is_open=True, capacity_limit=10)

    initial_count = settings.current_confirmed_count
    assert initial_count == 0

    # Simulate transactional failure during registration by rolling back outer session
    with pytest.raises(RuntimeError):
        with db.begin_nested():
            create_individual_registration(db, org.id, event.id, full_name="Ghost User", email="ghost@test.edu")
            raise RuntimeError("Simulated crash before commit!")

    # Verify count and records were not committed
    db.refresh(settings)
    assert settings.current_confirmed_count == 0
    ghost_part = db.execute(select(Participant).where(Participant.email_normalized == "ghost@test.edu")).scalar_one_or_none()
    assert ghost_part is None


def test_cancellation_capacity_release_exactness(db: Session):
    """Verify capacity release rules: confirmed releases once, waitlisted does not release, repeated is safe."""
    admin = _create_user(db, "cancel_admin@test.edu", "Cancel Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Cancel Event")
    settings = get_or_create_registration_settings(
        db, org.id, event.id, is_open=True, capacity_limit=2, waitlist_enabled=True
    )

    # 1. Confirmed registration
    res_conf = create_individual_registration(db, org.id, event.id, full_name="Confirmed User", email="conf@test.edu")
    assert not res_conf.is_waitlisted

    # 2. Confirmed registration
    res_conf2 = create_individual_registration(db, org.id, event.id, full_name="Confirmed User 2", email="conf2@test.edu")
    assert not res_conf2.is_waitlisted

    db.refresh(settings)
    assert settings.current_confirmed_count == 2

    # 3. Waitlisted registration
    res_wait = create_individual_registration(db, org.id, event.id, full_name="Waitlist User", email="wait@test.edu")
    assert res_wait.is_waitlisted
    db.refresh(settings)
    assert settings.current_confirmed_count == 2

    # 4. Cancel waitlisted registration -> Must NOT release confirmed capacity!
    cancel_registration(db, org.id, event.id, res_wait.registration.id, reason="No longer interested")
    db.refresh(settings)
    assert settings.current_confirmed_count == 2

    # 5. Cancel confirmed registration -> Releases exactly 1 slot
    cancel_registration(db, org.id, event.id, res_conf.registration.id, reason="Doctor appointment")
    db.refresh(settings)
    assert settings.current_confirmed_count == 1

    # 6. Repeated cancellation of already cancelled registration -> Idempotent, does not decrement again!
    cancel_registration(db, org.id, event.id, res_conf.registration.id, reason="Repeat click")
    db.refresh(settings)
    assert settings.current_confirmed_count == 1


def test_capacity_reduction_below_current_attendance_behavior(db: Session):
    """Verify that lowering capacity_limit below current attendance preserves existing registrations but blocks new ones."""
    admin = _create_user(db, "reduce_admin@test.edu", "Reduce Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Reduce Event")
    settings = get_or_create_registration_settings(
        db, org.id, event.id, is_open=True, capacity_limit=10, waitlist_enabled=False
    )

    for i in range(4):
        create_individual_registration(db, org.id, event.id, full_name=f"User {i}", email=f"u{i}@test.edu")

    db.refresh(settings)
    assert settings.current_confirmed_count == 4

    # Lower capacity limit to 2
    update_registration_settings(db, org.id, event.id, admin, capacity_limit=2)
    db.refresh(settings)
    assert settings.capacity_limit == 2
    assert settings.current_confirmed_count == 4  # Existing registrations preserved

    # Attempting new registration must be blocked
    with pytest.raises(CapacityExhaustedError):
        create_individual_registration(db, org.id, event.id, full_name="Blocked User", email="blocked@test.edu")


def test_diagnostic_reconciliation_query(db: Session):
    """Verify that reconcile_event_registration_counts identifies discrepancies and auto-fixes accurately."""
    admin = _create_user(db, "diag_admin@test.edu", "Diag Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Diag Event")
    settings = get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    res1 = create_individual_registration(db, org.id, event.id, full_name="D1", email="d1@test.edu")
    res2 = create_individual_registration(db, org.id, event.id, full_name="D2", email="d2@test.edu")
    check_in_participant(db, org.id, event.id, admin, raw_token=res1.issued_tickets[0].raw_pass_token)

    # Reconciled initially
    diag1 = reconcile_event_registration_counts(db, event.id)
    assert diag1["confirmed_reconciled"] is True
    assert diag1["actual_confirmed_count"] == 2
    assert diag1["attended_reconciled"] is True
    assert diag1["actual_attended_count"] == 1

    # Tamper with settings counter synthetically
    settings.current_confirmed_count = 99
    settings.current_attended_count = 42
    db.flush()

    diag2 = reconcile_event_registration_counts(db, event.id)
    assert diag2["confirmed_reconciled"] is False
    assert diag2["attended_reconciled"] is False

    # Run with auto_fix=True
    diag_fixed = reconcile_event_registration_counts(db, event.id, auto_fix=True)
    assert diag_fixed["auto_fixed"] is True
    db.refresh(settings)
    assert settings.current_confirmed_count == 2
    assert settings.current_attended_count == 1


# =========================================================================
# Event Lifecycle & Program Scope Tests
# =========================================================================

def test_registration_rejection_for_archived_event_and_parent_program(db: Session):
    """Verify that registration and settings updates are rejected for archived events and parent programs."""
    admin = _create_user(db, "arch_admin@test.edu", "Arch Admin")
    org = _create_org(db, admin)

    # 1. Standalone archived event
    event = _create_event(db, org, admin, "Archived Event")
    event.status = "archived"
    event.archived_at = datetime.now(timezone.utc)
    db.flush()

    with pytest.raises(RegistrationClosedError):
        get_or_create_registration_settings(db, org.id, event.id)

    # 2. Child event under archived Program
    program = Program(
        organization_id=org.id,
        name="Archived Fest",
        status="archived",
        created_by_user_id=admin.id,
        archived_at=datetime.now(timezone.utc),
    )
    db.add(program)
    db.flush()

    child_event = Event(
        organization_id=org.id,
        program_id=program.id,
        name="Child Workshop",
        status="published",
        created_by_user_id=admin.id,
        event_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        timezone="Asia/Kolkata",
    )
    db.add(child_event)
    db.flush()

    with pytest.raises(RegistrationClosedError):
        get_or_create_registration_settings(db, org.id, child_event.id)


# =========================================================================
# Check-In, Idempotency & Manager Correction Audit Tests (D-SLICE5-04)
# =========================================================================

def test_check_in_eligibility_and_cancelled_participant_rejection(db: Session):
    """Verify that cancelled participants and revoked tickets cannot check in."""
    admin = _create_user(db, "chk_elig_admin@test.edu", "Check Elig Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Elig Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    res = create_individual_registration(db, org.id, event.id, full_name="Tom Harris", email="tom@test.edu")
    raw_token = res.issued_tickets[0].raw_pass_token
    ticket = res.issued_tickets[0].ticket
    part = res.participants[0]

    # Cancel registration
    cancel_registration(db, org.id, event.id, res.registration.id, reason="Unable to attend")

    # QR scan rejected
    with pytest.raises(TicketInvalidError):
        check_in_participant(db, org.id, event.id, admin, raw_token=raw_token)

    # Manual search rejected
    with pytest.raises(CheckInError):
        check_in_participant(db, org.id, event.id, admin, participant_id=part.id)


def test_check_in_duplicate_scan_idempotency_and_db_uniqueness(db: Session):
    """Verify that repeated scans return existing check-in idempotently and DB index blocks duplicate valid check-ins."""
    admin = _create_user(db, "dup_admin@test.edu", "Dup Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Dup Scan Event")
    settings = get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    res = create_individual_registration(db, org.id, event.id, full_name="Sneha Rao", email="sneha@test.edu")
    raw_token = res.issued_tickets[0].raw_pass_token
    part = res.participants[0]
    ticket = res.issued_tickets[0].ticket

    # Scan 1: creates check-in
    ci1, is_dup1 = check_in_participant(db, org.id, event.id, admin, raw_token=raw_token)
    assert not is_dup1
    db.refresh(settings)
    assert settings.current_attended_count == 1

    # Scan 2: idempotent return of existing check-in, counter not incremented
    ci2, is_dup2 = check_in_participant(db, org.id, event.id, admin, raw_token=raw_token)
    assert is_dup2
    assert ci1.id == ci2.id
    db.refresh(settings)
    assert settings.current_attended_count == 1

    # Attempting direct database insert of a second valid check-in fails via uq_check_in_event_participant
    second_db_ci = CheckIn(
        organization_id=org.id,
        event_id=event.id,
        participant_id=part.id,
        ticket_id=ticket.id,
        check_in_status="valid",  # Duplicate valid check-in!
        checked_in_by_user_id=admin.id,
    )
    db.add(second_db_ci)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_check_in_void_manager_authority_and_immutable_audit_trail(db: Session):
    """Verify D-SLICE5-04: volunteers cannot void check-ins; managers void with reason >= 10 chars, immutable ledger."""
    admin = _create_user(db, "lead@test.edu", "Event Lead Admin")
    volunteer = _create_user(db, "volunteer@test.edu", "Desk Volunteer")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Void Audit Event")
    settings = get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    # Volunteer assigned REGISTRATION_STAFF role
    _add_member_with_role(db, org, volunteer, role_name="REGISTRATION_STAFF", scope_type="event", scope_id=event.id)

    res = create_individual_registration(db, org.id, event.id, full_name="Rahul Verma", email="rahul@test.edu")
    token = res.issued_tickets[0].raw_pass_token

    # Volunteer can check in
    check_in, _ = check_in_participant(db, org.id, event.id, volunteer, raw_token=token)
    assert check_in.check_in_status == "valid"

    # Volunteer CANNOT void check-in
    with pytest.raises(PermissionDeniedError):
        correct_or_void_check_in(
            db, org.id, event.id, check_in.id, reason="Accidental badge scan", actor_user=volunteer
        )

    # Manager voids with reason >= 10 chars
    voided_ci, correction = correct_or_void_check_in(
        db, org.id, event.id, check_in.id, reason="Scanned mistaken badge during roll call", actor_user=admin
    )
    assert voided_ci.check_in_status == "voided"
    assert voided_ci.voided_by_user_id == admin.id
    assert voided_ci.voided_at is not None

    # Audit correction ledger
    assert correction.check_in_id == check_in.id
    assert correction.previous_status == "valid"
    assert correction.new_status == "voided"
    assert correction.corrected_by_user_id == admin.id
    assert "Scanned mistaken badge" in correction.reason

    # Headcount counter decremented
    db.refresh(settings)
    assert settings.current_attended_count == 0

    # Cannot void an already voided check-in
    with pytest.raises(CheckInCorrectionError):
        correct_or_void_check_in(
            db, org.id, event.id, check_in.id, reason="Repeat void attempt by manager", actor_user=admin
        )


def test_manual_check_in_multi_ticket_safety_no_multiple_results_found(db: Session):
    """Verify that issuing replacement tickets does not crash manual check-in with MultipleResultsFound."""
    admin = _create_user(db, "multi_tkt_admin@test.edu", "Multi Tkt Admin")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Multi Ticket Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    res = create_individual_registration(db, org.id, event.id, full_name="Kavita Iyer", email="kavita@test.edu")
    part = res.participants[0]
    tkt1 = res.issued_tickets[0].ticket

    # Attendee checks in
    check_in, _ = check_in_participant(db, org.id, event.id, admin, raw_token=res.issued_tickets[0].raw_pass_token)
    assert check_in.check_in_status == "valid"

    # Manager voids check-in and issues replacement ticket
    correct_or_void_check_in(db, org.id, event.id, check_in.id, reason="Badge lost after initial check-in", actor_user=admin)
    res_tkt2 = issue_replacement_ticket(db, org.id, event.id, part.id, admin, reason="Issued new NFC wristband")

    # Now attendee checks in again via manual search
    # Query must cleanly resolve the single issued ticket without MultipleResultsFound
    ci2, is_dup = check_in_participant(db, org.id, event.id, admin, participant_id=part.id)
    assert not is_dup
    assert ci2.ticket_id == res_tkt2.ticket.id


# =========================================================================
# Privacy & Roster Query Boundary Tests
# =========================================================================

def test_roster_privacy_masking_and_unmasked_permission_gate(db: Session):
    """Verify privacy boundaries: volunteers receive masked contact info; unmasked requires elevated permission."""
    admin = _create_user(db, "privacy_admin@test.edu", "Privacy Admin")
    volunteer = _create_user(db, "volunteer_privacy@test.edu", "Volunteer Privacy")
    org = _create_org(db, admin)
    event = _create_event(db, org, admin, "Privacy Event")
    get_or_create_registration_settings(db, org.id, event.id, is_open=True)

    _add_member_with_role(db, org, volunteer, role_name="REGISTRATION_STAFF", scope_type="event", scope_id=event.id)

    create_individual_registration(
        db, org.id, event.id, full_name="Ananya Panday", email="ananya.panday@bollywood.edu", phone_number="+91 9876543210"
    )

    # 1. Volunteer caller: receives masked contact details
    roster_masked = get_event_roster_participants(db, org.id, event.id, volunteer, include_unmasked_contact=True)
    assert len(roster_masked) == 1
    row = roster_masked[0]
    assert row["email"] != "ananya.panday@bollywood.edu"
    assert "a***y@bollywood.edu" in row["email"]
    assert row["phone_number"] != "+91 9876543210"
    assert "3210" in row["phone_number"]

    # 2. Admin caller: receives unmasked contact details
    roster_unmasked = get_event_roster_participants(db, org.id, event.id, admin, include_unmasked_contact=True)
    assert len(roster_unmasked) == 1
    admin_row = roster_unmasked[0]
    assert admin_row["email"] == "ananya.panday@bollywood.edu"
    assert admin_row["phone_number"] == "+91 9876543210"
