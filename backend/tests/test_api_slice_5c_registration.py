from datetime import date, datetime, timedelta, timezone
import io
import uuid
import pytest
from starlette.testclient import TestClient

from app.models.organization import OrganizationMembership
from app.models.registration import (
    CheckIn,
    CheckInCorrection,
    EventRegistrationSettings,
    Participant,
    Registration,
    Ticket,
)
from app.models.role import RoleAssignment
from app.services.event import create_event, create_program
from app.services.organization import create_organization, verify_organization
from app.services.registration import (
    generate_registration_key,
    get_or_create_registration_settings,
    hash_credential,
)


@pytest.fixture
def reg_api_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin_reg@internal.gov")
    creator = create_synthetic_user("creator_reg@org.edu", "Creator Reg")
    org = create_organization(db, creator, "Apex University", "Engineering Club")
    verify_organization(db, admin, org.id, "verified")

    # Staff users
    lead_user = create_synthetic_user("lead_reg@org.edu", "Event Lead Reg")
    volunteer_user = create_synthetic_user("volunteer_reg@org.edu", "Desk Volunteer")
    unauth_member = create_synthetic_user("member_reg@org.edu", "General Member")

    now = datetime.now(timezone.utc)
    mb_lead = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=lead_user.id,
        membership_status="active",
        joined_at=now,
    )
    mb_vol = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=volunteer_user.id,
        membership_status="active",
        joined_at=now,
    )
    mb_gen = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=unauth_member.id,
        membership_status="active",
        joined_at=now,
    )
    db.add_all([mb_lead, mb_vol, mb_gen])
    db.commit()

    # Program and Child Events
    prog = create_program(
        db,
        creator=creator,
        organization_id=org.id,
        name="Annual TechFest 2026",
        planned_start_date=date(2026, 11, 1),
        planned_end_date=date(2026, 11, 10),
    )
    event1 = create_event(
        db,
        creator,
        org.id,
        "Hackathon 2026",
        program_id=prog.id,
        event_date=date(2026, 11, 2),
    )
    event2 = create_event(
        db,
        creator,
        org.id,
        "RoboWars 2026",
        program_id=prog.id,
        event_date=date(2026, 11, 3),
    )

    # Standalone Event
    standalone_event = create_event(
        db,
        creator,
        org.id,
        "CodeCamp Standalone",
        event_date=date(2026, 12, 1),
    )

    # Assign Scoped Roles
    # Lead has EVENT_LEAD scoped to event1
    db.add(RoleAssignment(membership_id=mb_lead.id, role_name="EVENT_LEAD", scope_type="event", scope_id=event1.id))
    # Volunteer has REGISTRATION_STAFF scoped to event1
    db.add(RoleAssignment(membership_id=mb_vol.id, role_name="REGISTRATION_STAFF", scope_type="event", scope_id=event1.id))
    db.commit()

    # Configure registration settings for event1 with unguessable key
    reg_key, key_hash = generate_registration_key()
    settings1 = get_or_create_registration_settings(
        db,
        organization_id=org.id,
        event_id=event1.id,
        is_open=True,
        registration_format="both",
        capacity_limit=50,
        team_size_min=2,
        team_size_max=4,
        registration_key=reg_key,
    )
    db.commit()

    # Alien organization for cross-tenant testing
    alien_creator = create_synthetic_user("alien_reg@alien.edu", "Alien Creator")
    alien_org = create_organization(db, alien_creator, "Alien Tech", "Alien Club")
    verify_organization(db, admin, alien_org.id, "verified")
    alien_event = create_event(
        db,
        alien_creator,
        alien_org.id,
        "Alien Hackathon",
        event_date=date(2026, 11, 2),
    )
    alien_key, _ = generate_registration_key()
    get_or_create_registration_settings(
        db,
        organization_id=alien_org.id,
        event_id=alien_event.id,
        is_open=True,
        registration_key=alien_key,
    )
    db.commit()

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "lead_user": lead_user,
        "volunteer_user": volunteer_user,
        "unauth_member": unauth_member,
        "prog": prog,
        "event1": event1,
        "event2": event2,
        "standalone_event": standalone_event,
        "reg_key": reg_key,
        "settings1": settings1,
        "alien_org": alien_org,
        "alien_creator": alien_creator,
        "alien_event": alien_event,
        "alien_key": alien_key,
    }


# =========================================================================
# 1. Public Settings & Discovery Tests
# =========================================================================

def test_public_settings_retrieval_success(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["public_registration_key"] == reg_key
    assert data["event_name"] == "Hackathon 2026"
    assert data["registration_status"] == "open"
    assert data["registration_format"] == "both"
    assert data["team_size_min"] == 2
    assert data["team_size_max"] == 4
    assert data["capacity_available"] is True


def test_public_settings_registration_closed(client: TestClient, reg_api_fixture, db):
    reg_key = reg_api_fixture["reg_key"]
    settings1 = reg_api_fixture["settings1"]
    settings1.is_open = False
    db.commit()

    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["registration_status"] == "closed"


def test_public_settings_temporal_windows(client: TestClient, reg_api_fixture, db):
    reg_key = reg_api_fixture["reg_key"]
    settings1 = reg_api_fixture["settings1"]
    now = datetime.now(timezone.utc)

    # Window in the future -> not_yet_open
    settings1.is_open = True
    settings1.registration_open_at = now + timedelta(days=2)
    db.commit()

    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 200
    assert resp.json()["registration_status"] == "not_yet_open"

    # Window in the past -> ended
    settings1.registration_open_at = now - timedelta(days=5)
    settings1.registration_close_at = now - timedelta(days=1)
    db.commit()

    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 200
    assert resp.json()["registration_status"] == "ended"


def test_public_settings_invalid_key_and_archived_event(client: TestClient, reg_api_fixture, db):
    # Non-existent key -> 404
    resp = client.get("/api/v1/public/events/non_existent_key_slug")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Event not found or registration key invalid."

    # Archived event -> 404
    event1 = reg_api_fixture["event1"]
    reg_key = reg_api_fixture["reg_key"]
    event1.status = "archived"
    event1.archived_at = datetime.now(timezone.utc)
    db.commit()

    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 404


# =========================================================================
# 2. Public Registration Workflows (Solo & Team)
# =========================================================================

def test_public_individual_registration_success(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    payload = {
        "registration_type": "individual",
        "contact_email": "alice@student.edu",
        "contact_phone": "+91 9876543210",
        "participants": [
            {
                "full_name": "Alice Wonderland",
                "email": "alice@student.edu",
                "phone_number": "+91 9876543210",
                "college_name": "Apex University",
                "student_id": "APEX-2026-001",
                "is_primary_contact": True,
            }
        ],
    }

    resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["registration_status"] == "confirmed"
    assert data["registration_type"] == "individual"
    assert len(data["passes"]) == 1
    assert data["passes"][0]["participant_name"] == "Alice Wonderland"
    assert data["passes"][0]["pass_code"].startswith("CO-PASS-")
    assert data["passes"][0]["ticket_reference"].startswith("TKT-")


def test_public_team_registration_success(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    payload = {
        "registration_type": "team",
        "team_name": "ByteCrafters",
        "contact_email": "lead@student.edu",
        "contact_phone": "+91 9876543211",
        "participants": [
            {
                "full_name": "Team Lead Aarav",
                "email": "lead@student.edu",
                "phone_number": "+91 9876543211",
                "college_name": "Apex University",
                "student_id": "APEX-2026-010",
                "is_primary_contact": True,
                "team_role": "leader",
            },
            {
                "full_name": "Member Diya",
                "email": "diya@student.edu",
                "phone_number": "+91 9876543212",
                "college_name": "Apex University",
                "student_id": "APEX-2026-011",
                "is_primary_contact": False,
                "team_role": "member",
            },
        ],
    }

    resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["registration_status"] == "confirmed"
    assert data["registration_type"] == "team"
    assert data["team_name"] == "ByteCrafters"
    assert len(data["passes"]) == 2
    # Verify each member has a unique pass code
    pass_codes = [p["pass_code"] for p in data["passes"]]
    assert len(set(pass_codes)) == 2


def test_public_team_registration_bounds_validation(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    # Team requires min 2 members per fixture settings
    payload_one_member = {
        "registration_type": "team",
        "team_name": "SoloBand",
        "contact_email": "solo@student.edu",
        "participants": [
            {
                "full_name": "Solo Guy",
                "email": "solo@student.edu",
            }
        ],
    }
    resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload_one_member)
    assert resp.status_code == 422
    assert "outside allowed bounds" in resp.json()["detail"]


def test_public_team_registration_duplicate_member_detection(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    payload = {
        "registration_type": "team",
        "team_name": "CloneArmy",
        "contact_email": "clone@student.edu",
        "participants": [
            {
                "full_name": "Same Person",
                "email": "same@student.edu",
            },
            {
                "full_name": "Same Person",
                "email": "same@student.edu",
            },
        ],
    }
    resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp.status_code == 400
    assert "Duplicate team member detected" in resp.json()["detail"]


# =========================================================================
# 3. Idempotency & Safe Replay Tests
# =========================================================================

def test_idempotent_replay_safe_credentials_redaction(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    idemp_key = f"idemp_{uuid.uuid4().hex[:12]}"
    payload = {
        "registration_type": "individual",
        "contact_email": "idemp_test@student.edu",
        "idempotency_key": idemp_key,
        "participants": [
            {
                "full_name": "Idemp Tester",
                "email": "idemp_test@student.edu",
            }
        ],
    }

    # First request -> 201 Created with raw pass code
    resp1 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["passes"][0]["pass_code"].startswith("CO-PASS-")

    # Second request with identical payload and key -> 201 Created with REDACTED pass token
    resp2 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["registration_id"] == data1["registration_id"]
    assert data2["confirmation_code"] == data1["confirmation_code"]
    assert data2["passes"][0]["pass_code"] == "<REDACTED_AFTER_ISSUANCE>"


def test_idempotent_replay_conflict_with_different_payload(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    idemp_key = f"idemp_{uuid.uuid4().hex[:12]}"
    payload1 = {
        "registration_type": "individual",
        "contact_email": "initial@student.edu",
        "idempotency_key": idemp_key,
        "participants": [
            {
                "full_name": "Initial Person",
                "email": "initial@student.edu",
            }
        ],
    }
    resp1 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload1)
    assert resp1.status_code == 201

    # Second request with same idempotency key but different email payload -> 409 Conflict
    payload2 = {
        "registration_type": "individual",
        "contact_email": "different@student.edu",
        "idempotency_key": idemp_key,
        "participants": [
            {
                "full_name": "Initial Person",
                "email": "different@student.edu",
            }
        ],
    }
    resp2 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload2)
    assert resp2.status_code == 409
    assert "Idempotency key reused with different" in resp2.json()["detail"]


# =========================================================================
# 4. Capacity Exhaustion & All-or-Nothing Team Admission
# =========================================================================

def test_capacity_exhaustion_and_all_or_nothing(client: TestClient, reg_api_fixture, db):
    reg_key = reg_api_fixture["reg_key"]
    settings1 = reg_api_fixture["settings1"]
    # Set capacity to 2 slots
    settings1.capacity_limit = 2
    settings1.current_confirmed_count = 1
    db.commit()

    # Team needing 2 slots when only 1 is available -> Rejected completely
    payload_team = {
        "registration_type": "team",
        "team_name": "TwoDevs",
        "contact_email": "two@student.edu",
        "participants": [
            {"full_name": "Dev One", "email": "dev1@student.edu"},
            {"full_name": "Dev Two", "email": "dev2@student.edu"},
        ],
    }
    resp_team = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload_team)
    assert resp_team.status_code == 400
    assert "cannot accommodate 2 participant(s)" in resp_team.json()["detail"]

    # Solo needing 1 slot -> Succeeds
    payload_solo = {
        "registration_type": "individual",
        "contact_email": "solo_fit@student.edu",
        "participants": [{"full_name": "Solo Fit", "email": "solo_fit@student.edu"}],
    }
    resp_solo = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload_solo)
    assert resp_solo.status_code == 201

    # Now capacity is 2/2 -> Next solo rejected
    payload_overflow = {
        "registration_type": "individual",
        "contact_email": "overflow@student.edu",
        "participants": [{"full_name": "Overflow", "email": "overflow@student.edu"}],
    }
    resp_overflow = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload_overflow)
    assert resp_overflow.status_code == 400


# =========================================================================
# 5. Public Pass Rendering & PII Exclusion
# =========================================================================

def test_public_pass_rendering_zero_pii_in_qr_payload(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    # Register attendee
    payload = {
        "registration_type": "individual",
        "contact_email": "qr_test@student.edu",
        "contact_phone": "+91 9988776655",
        "participants": [
            {
                "full_name": "QR Attendee",
                "email": "qr_test@student.edu",
                "phone_number": "+91 9988776655",
            }
        ],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # View pass via secure body-based POST endpoint
    pass_resp = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": pass_code},
    )
    assert pass_resp.status_code == 200
    data = pass_resp.json()
    assert data["participant_name"] == "QR Attendee"
    assert data["status"] == "issued"
    assert data["qr_payload"] == pass_code
    # Ensure zero PII in qr payload
    assert "qr_test@student.edu" not in data["qr_payload"]
    assert "+91 9988776655" not in data["qr_payload"]


def test_public_pass_rendering_invalid_token(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    resp = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": "CO-PASS-FAKEFAKEFAKE"},
    )
    assert resp.status_code == 404


# =========================================================================
# 6. Public Status Lookup & Cancellation
# =========================================================================

def test_public_status_lookup_and_cancellation(client: TestClient, reg_api_fixture):
    reg_key = reg_api_fixture["reg_key"]
    payload = {
        "registration_type": "individual",
        "contact_email": "cancel_test@student.edu",
        "participants": [{"full_name": "Cancel Me", "email": "cancel_test@student.edu"}],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    code = reg_resp.json()["confirmation_code"]

    # Check status via secure body-based POST endpoint
    status_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/lookup",
        json={"confirmation_code": code},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["registration_status"] == "confirmed"
    assert status_resp.json()["participant_count"] == 1

    # Cancel registration via secure body-based POST endpoint
    cancel_payload = {
        "confirmation_code": code,
        "cancellation_reason": "Family emergency, unable to attend",
        "contact_email": "cancel_test@student.edu",
    }
    cancel_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/cancel",
        json=cancel_payload,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["registration_status"] == "cancelled"

    # Status is now cancelled
    status_resp2 = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/lookup",
        json={"confirmation_code": code},
    )
    assert status_resp2.status_code == 200
    assert status_resp2.json()["registration_status"] == "cancelled"


# =========================================================================
# 7. Staff Settings Management & Key Rotation
# =========================================================================

def test_staff_settings_update_and_key_rotation(client: TestClient, reg_api_fixture, auth_user):
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]
    old_key = reg_api_fixture["reg_key"]
    auth_user(lead)

    # Rotate registration key
    update_payload = {
        "rotate_registration_key": True,
        "capacity_limit": 150,
    }
    resp = client.put(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings",
        json=update_payload,
    )
    assert resp.status_code == 200
    assert resp.json()["capacity_limit"] == 150

    # Old registration key is now invalid
    old_resp = client.get(f"/api/v1/public/events/{old_key}")
    assert old_resp.status_code == 404


def test_staff_settings_unauthorized_user_rejected(client: TestClient, reg_api_fixture, auth_user):
    unauth = reg_api_fixture["unauth_member"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]
    auth_user(unauth)

    resp = client.put(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings",
        json={"capacity_limit": 200},
    )
    assert resp.status_code == 403


# =========================================================================
# 8. Staff Walk-In Registration
# =========================================================================

def test_staff_walk_in_registration_success(client: TestClient, reg_api_fixture, auth_user):
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]
    auth_user(volunteer)

    payload = {
        "registration_type": "individual",
        "contact_email": "walkin@student.edu",
        "participants": [
            {
                "full_name": "Walkin Attendee",
                "email": "walkin@student.edu",
            }
        ],
    }
    resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registrations/walk-in",
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["registration_status"] == "confirmed"
    assert len(data["passes"]) == 1


# =========================================================================
# 9. Attendance Check-In Operations (QR, Manual & Team Member Isolation)
# =========================================================================

def test_qr_scan_check_in_and_duplicate_idempotency(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register attendee
    payload = {
        "registration_type": "individual",
        "contact_email": "checkin_qr@student.edu",
        "participants": [{"full_name": "QR CheckIn Guy", "email": "checkin_qr@student.edu"}],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Staff checks in attendee
    auth_user(volunteer)
    ci_payload = {
        "pass_code": pass_code,
        "method": "qr_scan",
        "station_id": "STATION-DESK-A",
    }
    ci_resp = client.post(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins", json=ci_payload)
    assert ci_resp.status_code == 200
    assert ci_resp.json()["status"] == "verified"
    assert ci_resp.json()["participant_name"] == "QR CheckIn Guy"

    # Second scan -> Duplicate Idempotent (already_checked_in)
    ci_resp2 = client.post(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins", json=ci_payload)
    assert ci_resp2.status_code == 200
    assert ci_resp2.json()["status"] == "already_checked_in"
    assert "already checked in" in ci_resp2.json()["message"]


def test_team_member_individual_check_in_rule(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register team with 2 members
    team_payload = {
        "registration_type": "team",
        "team_name": "PairDevs",
        "contact_email": "pair@student.edu",
        "participants": [
            {"full_name": "Member A", "email": "a@student.edu", "is_primary_contact": True},
            {"full_name": "Member B", "email": "b@student.edu"},
        ],
    }
    team_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=team_payload)
    passes = team_resp.json()["passes"]
    pass_a = passes[0]["pass_code"]
    pass_b = passes[1]["pass_code"]

    auth_user(volunteer)

    # Check in Member A
    ci_a = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_a, "station_id": "DESK-1"},
    )
    assert ci_a.status_code == 200
    assert ci_a.json()["status"] == "verified"

    # Member B must NOT be automatically checked in
    # Verify via check-in lookup for Member B
    lookup_b = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-in-lookup?q=Member B")
    assert lookup_b.status_code == 200
    items = lookup_b.json()
    assert len(items) == 1
    assert items[0]["full_name"] == "Member B"
    assert items[0]["already_checked_in"] is False
    assert items[0]["is_eligible_for_check_in"] is True


def test_manual_search_check_in(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register attendee
    solo_payload = {
        "registration_type": "individual",
        "contact_email": "manual_guy@student.edu",
        "participants": [{"full_name": "Manual Search Guy", "email": "manual_guy@student.edu"}],
    }
    client.post(f"/api/v1/public/events/{reg_key}/registrations", json=solo_payload)

    auth_user(volunteer)

    # Search desk roster
    lookup_resp = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-in-lookup?q=Manual Search")
    assert lookup_resp.status_code == 200
    item = lookup_resp.json()[0]
    p_id = item["participant_id"]

    # Manual check in by participant_id
    ci_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"participant_id": p_id, "method": "manual_search", "station_id": "MANUAL-DESK"},
    )
    assert ci_resp.status_code == 200
    assert ci_resp.json()["status"] == "verified"


# =========================================================================
# 10. Check-In Voids & Manager-Only Authority
# =========================================================================

def test_check_in_void_manager_only(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    volunteer = reg_api_fixture["volunteer_user"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register & check in attendee
    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "void_test@student.edu",
            "participants": [{"full_name": "Void Me", "email": "void_test@student.edu"}],
        },
    )
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    auth_user(volunteer)
    ci_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_code},
    )
    ci_id = ci_resp.json()["check_in_id"]

    # Desk volunteer tries to void -> 403 Forbidden
    void_resp_vol = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{ci_id}/void",
        json={"reason": "Accidental scan, volunteer mistake"},
    )
    assert void_resp_vol.status_code == 403

    # Event lead voids with reason < 10 chars -> 400 Bad Request
    auth_user(lead)
    void_resp_short = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{ci_id}/void",
        json={"reason": "too short"},
    )
    assert void_resp_short.status_code == 422 or void_resp_short.status_code == 400

    # Event lead voids with valid reason >= 10 chars -> 200 OK
    void_resp_lead = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{ci_id}/void",
        json={"reason": "Accidental check-in of wrong attendee; confirmed not present."},
    )
    assert void_resp_lead.status_code == 200
    assert void_resp_lead.json()["check_in_status"] == "voided"


# =========================================================================
# 11. Privacy Masking & CSV Roster Export
# =========================================================================

def test_privacy_contact_masking_tiered_access(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    volunteer = reg_api_fixture["volunteer_user"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register attendee
    client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "private_attendee@student.edu",
            "contact_phone": "+91 9123456789",
            "participants": [
                {
                    "full_name": "Private Attendee",
                    "email": "private_attendee@student.edu",
                    "phone_number": "+91 9123456789",
                }
            ],
        },
    )

    # Volunteer inspects roster -> Contact details are masked
    auth_user(volunteer)
    roster_vol = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants")
    assert roster_vol.status_code == 200
    item_vol = [i for i in roster_vol.json() if i["full_name"] == "Private Attendee"][0]
    assert item_vol["email"] != "private_attendee@student.edu"
    assert "***" in item_vol["email"]

    # Manager inspects roster -> Unmasked contact info
    auth_user(lead)
    roster_lead = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants")
    assert roster_lead.status_code == 200
    item_lead = [i for i in roster_lead.json() if i["full_name"] == "Private Attendee"][0]
    assert item_lead["email"] == "private_attendee@student.edu"
    assert item_lead["phone_number"] == "+91 9123456789"


def test_roster_csv_export_permissions(client: TestClient, reg_api_fixture, auth_user):
    volunteer = reg_api_fixture["volunteer_user"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Volunteer denied export -> 403 Forbidden
    auth_user(volunteer)
    resp_vol = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/roster-export")
    assert resp_vol.status_code == 403

    # Event Lead permitted export -> 200 OK text/csv
    auth_user(lead)
    resp_lead = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/roster-export")
    assert resp_lead.status_code == 200
    assert resp_lead.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in resp_lead.headers["content-disposition"]
    assert "participant_id,full_name,email" in resp_lead.text


# =========================================================================
# 12. Attendance Summary & Metrics
# =========================================================================

def test_attendance_summary_metrics(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    lead = reg_api_fixture["lead_user"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register 1 solo and 1 team (2 members)
    solo_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "solo_metric@student.edu",
            "participants": [{"full_name": "Solo Metric", "email": "solo_metric@student.edu"}],
        },
    )
    solo_pass = solo_resp.json()["passes"][0]["pass_code"]

    team_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "team",
            "team_name": "MetricTeam",
            "contact_email": "team_metric@student.edu",
            "participants": [
                {"full_name": "Team Dev 1", "email": "t1@student.edu"},
                {"full_name": "Team Dev 2", "email": "t2@student.edu"},
            ],
        },
    )
    team_pass1 = team_resp.json()["passes"][0]["pass_code"]

    # Check in solo attendee and 1 team member
    auth_user(volunteer)
    client.post(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins", json={"pass_code": solo_pass})
    client.post(f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins", json={"pass_code": team_pass1})

    # View summary
    auth_user(lead)
    sum_resp = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/attendance-summary")
    assert sum_resp.status_code == 200
    data = sum_resp.json()
    assert data["total_individual_registrations"] >= 1
    assert data["total_team_registrations"] >= 1
    assert data["current_attended_count"] >= 2
    assert data["teams_partially_attended"] >= 1


# =========================================================================
# 13. Scope Boundaries & Sibling-Event / Cross-Tenant Isolation
# =========================================================================

def test_sibling_event_ticket_scan_rejection(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event2 = reg_api_fixture["event2"]

    # Register for Event 1
    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "sibling_test@student.edu",
            "participants": [{"full_name": "Sibling Attendee", "email": "sibling_test@student.edu"}],
        },
    )
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Attempt to scan this pass at Event 2 -> 404 (pass not found in event 2)
    auth_user(reg_api_fixture["creator"])  # creator has org-wide admin
    ci_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event2.id}/check-ins",
        json={"pass_code": pass_code},
    )
    assert ci_resp.status_code == 404
    assert "Admission pass or participant not found" in ci_resp.json()["detail"]


def test_cross_tenant_access_blocked(client: TestClient, reg_api_fixture, auth_user):
    alien_creator = reg_api_fixture["alien_creator"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Alien user attempts to read Org 1's participants -> 404
    auth_user(alien_creator)
    resp = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Organization not found."


# =========================================================================
# 14. Additional Integration Tests: Authentication, Reissue, Hash Storage & Pagination
# =========================================================================

def test_unauthenticated_staff_requests_rejected(client: TestClient, reg_api_fixture):
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # No auth_user called -> fail-closed 401 Unauthorized
    resp1 = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings")
    assert resp1.status_code == 401

    resp2 = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants")
    assert resp2.status_code == 401

    resp3 = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": "CO-PASS-WHATEVER"},
    )
    assert resp3.status_code == 401


def test_pass_reissue_invalidates_prior_pass(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    lead = reg_api_fixture["lead_user"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register attendee
    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "reissue_test@student.edu",
            "participants": [{"full_name": "Reissue Attendee", "email": "reissue_test@student.edu"}],
        },
    )
    pass_data = reg_resp.json()["passes"][0]
    p_id = pass_data["participant_id"]
    old_pass_code = pass_data["pass_code"]

    # Manager reissues pass
    auth_user(lead)
    reissue_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants/{p_id}/reissue-pass",
        json={"reason": "Attendee phone died, requested replacement ticket at desk."},
    )
    assert reissue_resp.status_code == 200
    new_pass_code = reissue_resp.json()["pass_code"]
    assert new_pass_code != old_pass_code

    # Desk volunteer attempts to check in with OLD pass -> 400 Bad Request (Ticket has been revoked)
    auth_user(volunteer)
    ci_old = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": old_pass_code},
    )
    assert ci_old.status_code == 400
    assert "Ticket has been revoked" in ci_old.json()["detail"]

    # Check in with NEW pass -> 200 OK Verified
    ci_new = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": new_pass_code},
    )
    assert ci_new.status_code == 200
    assert ci_new.json()["status"] == "verified"


def test_database_credential_entropy_and_hash_storage(client: TestClient, reg_api_fixture, db):
    reg_key = reg_api_fixture["reg_key"]
    # Register attendee
    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "hash_check@student.edu",
            "participants": [{"full_name": "Hash Check", "email": "hash_check@student.edu"}],
        },
    )
    raw_pass_token = reg_resp.json()["passes"][0]["pass_code"]

    # Inspect Ticket in database
    ticket = db.query(Ticket).filter(Ticket.pass_code_hash == hash_credential(raw_pass_token)).first()
    assert ticket is not None
    # Ensure digest is 64 hex characters (SHA-256)
    assert len(ticket.pass_code_hash) == 64
    # Ensure raw credential is NOT present anywhere in ticket columns
    assert raw_pass_token not in ticket.ticket_reference
    assert raw_pass_token != ticket.pass_code_hash


def test_roster_pagination_and_query_filtering(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register 3 distinct participants
    for i in range(3):
        client.post(
            f"/api/v1/public/events/{reg_key}/registrations",
            json={
                "registration_type": "individual",
                "contact_email": f"page_user_{i}@student.edu",
                "participants": [{"full_name": f"Page User {i}", "email": f"page_user_{i}@student.edu"}],
            },
        )

    auth_user(lead)
    # Page 1: limit 2, offset 0
    p1 = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants?limit=2&offset=0")
    assert p1.status_code == 200
    assert len(p1.json()) == 2

    # Search filter
    search_resp = client.get(f"/api/v1/organizations/{org.id}/events/{event1.id}/participants?search=Page User 1")
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1
    assert search_resp.json()[0]["full_name"] == "Page User 1"


def test_archived_parent_program_restrictions(client: TestClient, reg_api_fixture, auth_user, db):
    prog = reg_api_fixture["prog"]
    lead = reg_api_fixture["lead_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]
    reg_key = reg_api_fixture["reg_key"]

    # Archive parent program
    prog.status = "archived"
    prog.archived_at = datetime.now(timezone.utc)
    db.commit()

    # Public endpoint -> 404 (child event blocked)
    resp_pub = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp_pub.status_code == 404

    # Staff settings management -> 404 Parent program archived
    auth_user(lead)
    resp_staff = client.put(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings",
        json={"capacity_limit": 300},
    )
    assert resp_staff.status_code == 404
    assert "Parent program has been archived" in resp_staff.json()["detail"]


def test_participant_details_update_authorized_and_denied(client: TestClient, reg_api_fixture, auth_user):
    reg_key = reg_api_fixture["reg_key"]
    lead = reg_api_fixture["lead_user"]
    volunteer = reg_api_fixture["volunteer_user"]
    org = reg_api_fixture["org"]
    event1 = reg_api_fixture["event1"]

    # Register attendee
    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "patch_user@student.edu",
            "participants": [{"full_name": "Old Name", "email": "patch_user@student.edu"}],
        },
    )
    p_id = reg_resp.json()["passes"][0]["participant_id"]

    # Volunteer cannot update attendee -> 403 Forbidden
    auth_user(volunteer)
    resp_vol = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants/{p_id}",
        json={"full_name": "New Name"},
    )
    assert resp_vol.status_code == 403

    # Event lead updates attendee -> 200 OK
    auth_user(lead)
    resp_lead = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants/{p_id}",
        json={
            "full_name": "Corrected Name",
            "college_name": "New Engineering College",
            "student_id": "STU-2026-999",
        },
    )
    assert resp_lead.status_code == 200
    assert resp_lead.json()["full_name"] == "Corrected Name"
    assert resp_lead.json()["college_name"] == "New Engineering College"
    assert resp_lead.json()["student_id"] == "STU-2026-999"

