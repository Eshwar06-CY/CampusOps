from datetime import date, datetime, timedelta, timezone
import io
import uuid
import pytest
from sqlalchemy import select
from starlette.testclient import TestClient

from app.models.event import Event, Program
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
    check_in_participant,
    export_event_roster_csv,
    generate_registration_key,
    get_or_create_registration_settings,
)


@pytest.fixture
def sec_audit_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin_sec@internal.gov")
    creator = create_synthetic_user("creator_sec@org.edu", "Creator Sec")
    org = create_organization(db, creator, "Apex Institute of Tech", "Robotics Society")
    verify_organization(db, admin, org.id, "verified")

    # Staff users
    lead_user = create_synthetic_user("lead_sec@org.edu", "Event Lead Sec")
    volunteer_user = create_synthetic_user("volunteer_sec@org.edu", "Desk Volunteer Sec")
    unauth_member = create_synthetic_user("member_sec@org.edu", "General Member Sec")

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
        name="Security Fest 2026",
        planned_start_date=date(2026, 11, 1),
        planned_end_date=date(2026, 11, 10),
    )
    event1 = create_event(
        db,
        creator,
        org.id,
        "CyberQuest 2026",
        program_id=prog.id,
        event_date=date(2026, 11, 2),
    )
    event2 = create_event(
        db,
        creator,
        org.id,
        "HardwareHacks 2026",
        program_id=prog.id,
        event_date=date(2026, 11, 3),
    )

    # Scoped roles
    # Lead has EVENT_LEAD on event1 (full management, corrections, view unmasked)
    db.add(RoleAssignment(membership_id=mb_lead.id, role_name="EVENT_LEAD", scope_type="event", scope_id=event1.id))
    # Volunteer has REGISTRATION_STAFF on event1 (check-in, view registrations, but masked contact, no corrections)
    db.add(RoleAssignment(membership_id=mb_vol.id, role_name="REGISTRATION_STAFF", scope_type="event", scope_id=event1.id))
    db.commit()

    # Settings for event1
    reg_key, _ = generate_registration_key()
    settings1 = get_or_create_registration_settings(
        db,
        organization_id=org.id,
        event_id=event1.id,
        is_open=True,
        registration_format="both",
        capacity_limit=20,
        team_size_min=2,
        team_size_max=4,
        registration_key=reg_key,
    )
    db.commit()

    # Alien organization for cross-tenant testing
    alien_creator = create_synthetic_user("alien_sec@alien.edu", "Alien Creator Sec")
    alien_org = create_organization(db, alien_creator, "Alien Cyber", "Alien Club")
    verify_organization(db, admin, alien_org.id, "verified")
    alien_event = create_event(
        db,
        alien_creator,
        alien_org.id,
        "Alien Con 2026",
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
        "reg_key": reg_key,
        "settings1": settings1,
        "alien_org": alien_org,
        "alien_creator": alien_creator,
        "alien_event": alien_event,
        "alien_key": alien_key,
    }


# =========================================================================
# 1. Public Capabilities & URL Credential Exposure Tests
# =========================================================================

def test_public_pass_verification_via_post_body(client: TestClient, sec_audit_fixture):
    """
    Verifies digital pass display using POST body (CO-SEC-001).
    Ensures pass_code is NOT exposed in the URL path, preventing browser history and proxy log leakage.
    Ensures zero PII is disclosed in response.
    """
    reg_key = sec_audit_fixture["reg_key"]
    reg_payload = {
        "registration_type": "individual",
        "contact_email": "privacy.first@example.edu",
        "contact_phone": "+91 9876543210",
        "participants": [
            {
                "full_name": "Rohan Deshmukh",
                "email": "privacy.first@example.edu",
                "phone_number": "+91 9876543210",
                "college_name": "Apex Engineering",
                "student_id": "AE-101",
            }
        ],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    assert reg_resp.status_code == 201
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Secure verification via POST body
    verify_resp = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": pass_code},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["pass_code"] == pass_code
    assert data["participant_name"] == "Rohan Deshmukh"
    assert data["status"] == "issued"
    assert data["qr_payload"] == pass_code
    # Ensure zero contact details or student IDs leaked
    assert "email" not in data
    assert "phone_number" not in data
    assert "student_id" not in data


def test_public_pass_verification_invalid_token_returns_uniform_404(client: TestClient, sec_audit_fixture):
    """
    Verifies that invalid or non-existent pass tokens return a generic 404 without leaking internal state.
    """
    reg_key = sec_audit_fixture["reg_key"]
    verify_resp = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": "CO-PASS-INVALIDTOKEN1234567890ABCDEF"},
    )
    assert verify_resp.status_code == 404
    assert "Admission pass not found" in verify_resp.json()["detail"]


def test_public_registration_lookup_via_post_body(client: TestClient, sec_audit_fixture):
    """
    Verifies registration status lookup using POST body to prevent confirmation code exposure in URL.
    Ensures participant names/roles are returned but emails/phones are omitted.
    """
    reg_key = sec_audit_fixture["reg_key"]
    reg_payload = {
        "registration_type": "team",
        "team_name": "BitCrushers",
        "contact_email": "captain@bitcrushers.org",
        "participants": [
            {
                "full_name": "Captain Kirk",
                "email": "captain@bitcrushers.org",
                "phone_number": "+91 9999900001",
                "is_primary_contact": True,
                "team_role": "leader",
            },
            {
                "full_name": "Spock Vulcan",
                "email": "spock@bitcrushers.org",
                "phone_number": "+91 9999900002",
                "team_role": "member",
            },
        ],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    assert reg_resp.status_code == 201
    code = reg_resp.json()["confirmation_code"]

    lookup_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/lookup",
        json={"confirmation_code": code},
    )
    assert lookup_resp.status_code == 200
    data = lookup_resp.json()
    assert data["confirmation_code"] == code
    assert data["registration_status"] == "confirmed"
    assert data["team_name"] == "BitCrushers"
    assert data["participant_count"] == 2
    # Ensure participant emails and phones are omitted from the public status lookup
    for p in data["participants"]:
        assert "email" not in p
        assert "phone_number" not in p
        assert "student_id" not in p


def test_public_registration_cancellation_via_post_body(client: TestClient, sec_audit_fixture):
    """
    Verifies cancellation using POST body with matching contact email.
    Confirms capacity is released and admission passes are invalidated.
    """
    reg_key = sec_audit_fixture["reg_key"]
    reg_payload = {
        "registration_type": "individual",
        "contact_email": "cancel.me@example.edu",
        "participants": [
            {
                "full_name": "Anita Roy",
                "email": "cancel.me@example.edu",
            }
        ],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    assert reg_resp.status_code == 201
    code = reg_resp.json()["confirmation_code"]
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Wrong email returns 404
    bad_cancel = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/cancel",
        json={
            "confirmation_code": code,
            "contact_email": "wrong.email@example.edu",
            "cancellation_reason": "I cannot attend anymore due to exam",
        },
    )
    assert bad_cancel.status_code == 404

    # Valid cancel via POST body
    good_cancel = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/cancel",
        json={
            "confirmation_code": code,
            "contact_email": "cancel.me@example.edu",
            "cancellation_reason": "I cannot attend anymore due to scheduled exam",
        },
    )
    assert good_cancel.status_code == 200
    assert good_cancel.json()["registration_status"] == "cancelled"

    # Pass is invalidated
    pass_check = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": pass_code},
    )
    assert pass_check.status_code == 404


def test_public_capability_legacy_get_endpoints_removed(client: TestClient, sec_audit_fixture):
    """
    Regression test verifying that legacy routes accepting sensitive capabilities
    (pass codes, confirmation codes) in URL paths have been removed and return 404.
    """
    reg_key = sec_audit_fixture["reg_key"]
    reg_payload = {
        "registration_type": "individual",
        "contact_email": "legacy.user@example.edu",
        "participants": [
            {"full_name": "Legacy User", "email": "legacy.user@example.edu"}
        ],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    assert reg_resp.status_code == 201
    code = reg_resp.json()["confirmation_code"]
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # 1. Legacy GET pass in URL path must be rejected with 404
    resp_pass = client.get(f"/api/v1/public/events/{reg_key}/passes/{pass_code}")
    assert resp_pass.status_code == 404

    # 2. Legacy GET registration in URL path must be rejected with 404
    resp_reg = client.get(f"/api/v1/public/events/{reg_key}/registrations/{code}")
    assert resp_reg.status_code == 404

    # 3. Legacy POST cancel with confirmation code in URL path must be rejected with 404
    resp_cancel = client.post(
        f"/api/v1/public/events/{reg_key}/registrations/{code}/cancel",
        json={"cancellation_reason": "Not coming", "contact_email": "legacy.user@example.edu"},
    )
    assert resp_cancel.status_code == 404

    # 4. Verify that secure body-based POST endpoints continue to work as intended
    verify_resp = client.post(
        f"/api/v1/public/events/{reg_key}/passes/verify",
        json={"pass_code": pass_code},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["participant_name"] == "Legacy User"


def test_registration_key_has_no_administrative_privileges(client: TestClient, sec_audit_fixture):
    """
    Verifies that registration_key cannot be used as an authorization token to access staff or admin routes.
    """
    reg_key = sec_audit_fixture["reg_key"]
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]

    headers = {"Authorization": f"Bearer {reg_key}"}
    resp = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants",
        headers=headers,
    )
    assert resp.status_code in (401, 403)


# =========================================================================
# 2. CSV Formula Injection Sanitization (CWE-1236)
# =========================================================================

def test_export_event_roster_csv_sanitizes_formula_triggers(db, sec_audit_fixture):
    """
    Verifies that participant-supplied strings starting with formula trigger characters
    (=, +, -, @, \\t, \\r) are escaped with a leading single quote (') in CSV export.
    Prevents CWE-1236 Spreadsheet Formula Injection.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead_user = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]

    from app.services.registration import create_team_registration

    malicious_members = [
        {
            "full_name": "=cmd|' /C calc'!A0",
            "email": "calc.exploit@test.edu",
            "phone_number": "+91 9999911111",
            "college_name": "@SUM(1+1)*cmd",
            "student_id": "-12345-EVIL",
            "is_primary_contact": True,
            "team_role": "leader",
        },
        {
            "full_name": "\tTabPrefixName",
            "email": "\rReturnPrefix@test.edu",
            "phone_number": "+1234567890",
            "college_name": "Clean College",
            "student_id": "=1+1",
            "team_role": "member",
        },
    ]

    create_team_registration(
        db=db,
        organization_id=org.id,
        event_id=event1.id,
        team_name="=HYPERLINK('http://attacker.com','Click')",
        members=malicious_members,
        contact_email="calc.exploit@test.edu",
        contact_phone="+91 9999911111",
    )
    db.commit()

    csv_data = export_event_roster_csv(
        db=db,
        organization_id=org.id,
        event_id=event1.id,
        actor_user=lead_user,
    )

    from app.services.registration import sanitize_csv_cell

    # Verify formula characters are safely neutralized with leading '
    assert "'=cmd|' /C calc'!A0" in csv_data
    assert "'@SUM(1+1)*cmd" in csv_data
    assert "'-12345-EVIL" in csv_data
    assert "'+1234567890" in csv_data
    assert "'=1+1" in csv_data
    assert "'=HYPERLINK" in csv_data
    # Verify sanitize_csv_cell correctly handles tab and carriage return
    assert sanitize_csv_cell("\tTabPrefix") == "'\tTabPrefix"
    assert sanitize_csv_cell("\rReturnPrefix") == "'\rReturnPrefix"
    assert sanitize_csv_cell("CleanText") == "CleanText"
    assert sanitize_csv_cell(None) == ""


# =========================================================================
# 3. Registration Idempotency Replay & Safe Credential Redaction
# =========================================================================

def test_idempotent_registration_replay_redacts_credentials(client: TestClient, sec_audit_fixture, db):
    """
    Submitting an identical payload with the same idempotency_key returns the existing registration,
    does NOT consume additional capacity, and redacts raw pass tokens.
    """
    reg_key = sec_audit_fixture["reg_key"]
    event1 = sec_audit_fixture["event1"]
    settings1 = sec_audit_fixture["settings1"]

    initial_confirmed = settings1.current_confirmed_count

    payload = {
        "registration_type": "individual",
        "contact_email": "idemp.safe@example.edu",
        "idempotency_key": "sec_audit_idemp_key_001",
        "participants": [
            {
                "full_name": "Idemp User",
                "email": "idemp.safe@example.edu",
            }
        ],
    }

    resp1 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["passes"][0]["pass_code"].startswith("CO-PASS-")

    # Replay identical payload
    resp2 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["registration_id"] == data1["registration_id"]
    assert data2["confirmation_code"] == data1["confirmation_code"]
    # Pass token is redacted to protect the credential from subsequent callers
    assert data2["passes"][0]["pass_code"] == "<REDACTED_AFTER_ISSUANCE>"

    # Ensure capacity incremented only once
    db.refresh(settings1)
    assert settings1.current_confirmed_count == initial_confirmed + 1


def test_idempotent_registration_conflict_on_altered_payload(client: TestClient, sec_audit_fixture):
    """
    Replaying an idempotency_key with a modified contact email or attendee details raises 409 Conflict.
    """
    reg_key = sec_audit_fixture["reg_key"]
    payload1 = {
        "registration_type": "individual",
        "contact_email": "original@example.edu",
        "idempotency_key": "sec_audit_idemp_key_002",
        "participants": [
            {"full_name": "Original Name", "email": "original@example.edu"}
        ],
    }
    resp1 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload1)
    assert resp1.status_code == 201

    payload2 = {
        "registration_type": "individual",
        "contact_email": "tampered@example.edu",
        "idempotency_key": "sec_audit_idemp_key_002",
        "participants": [
            {"full_name": "Original Name", "email": "tampered@example.edu"}
        ],
    }
    resp2 = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload2)
    assert resp2.status_code == 409
    assert "Idempotency key reused" in resp2.json()["detail"]


# =========================================================================
# 4. Participant Privacy & Tiered Roster Masking
# =========================================================================

def test_desk_volunteer_roster_receives_masked_contacts(client: TestClient, sec_audit_fixture, auth_user):
    """
    Desk volunteers with ACTION_VIEW_REGISTRATIONS but lacking ACTION_VIEW_ATTENDEE_CONTACT
    receive masked emails (e.g. 'a***a@org.edu') and masked phone numbers.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    volunteer = sec_audit_fixture["volunteer_user"]
    reg_key = sec_audit_fixture["reg_key"]

    # Register an attendee
    reg_payload = {
        "registration_type": "individual",
        "contact_email": "aarav.sharma@domain.edu",
        "contact_phone": "+91 9876543210",
        "participants": [
            {
                "full_name": "Aarav Sharma",
                "email": "aarav.sharma@domain.edu",
                "phone_number": "+91 9876543210",
                "college_name": "Tech Institute",
                "student_id": "TI-456",
            }
        ],
    }
    client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)

    auth_user(volunteer)

    # 1. Check participants list
    resp_roster = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants",
    )
    assert resp_roster.status_code == 200
    items = resp_roster.json()
    aarav_item = next(it for it in items if it["full_name"] == "Aarav Sharma")
    assert aarav_item["email"] == "a***a@domain.edu"
    assert "9876543210" not in (aarav_item["phone_number"] or "")

    # 2. Check participant detail
    p_id = aarav_item["id"]
    resp_detail = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants/{p_id}",
    )
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["email"] == "a***a@domain.edu"
    assert "9876543210" not in (detail["phone_number"] or "")

    # 3. Check registrations list
    resp_regs = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registrations",
    )
    assert resp_regs.status_code == 200
    reg_items = resp_regs.json()
    matching_reg = next(it for it in reg_items if it["id"] == aarav_item["registration_id"])
    assert matching_reg["contact_email"] == "a***a@domain.edu"
    assert "9876543210" not in (matching_reg["contact_phone"] or "")


def test_event_lead_roster_receives_unmasked_contacts(client: TestClient, sec_audit_fixture, auth_user):
    """
    Event Lead possessing ACTION_VIEW_ATTENDEE_CONTACT receives full unmasked emails and phone numbers.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead_user = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]

    reg_payload = {
        "registration_type": "individual",
        "contact_email": "priya.nair@domain.edu",
        "contact_phone": "+91 9123456789",
        "participants": [
            {
                "full_name": "Priya Nair",
                "email": "priya.nair@domain.edu",
                "phone_number": "+91 9123456789",
                "college_name": "Tech Institute",
                "student_id": "TI-789",
            }
        ],
    }
    client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)

    auth_user(lead_user)

    resp = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants",
    )
    assert resp.status_code == 200
    items = resp.json()
    priya_item = next(it for it in items if it["full_name"] == "Priya Nair")
    assert priya_item["email"] == "priya.nair@domain.edu"
    assert priya_item["phone_number"] == "+91 9123456789"


def test_desk_volunteer_denied_csv_export(client: TestClient, sec_audit_fixture, auth_user):
    """
    Desk volunteer lacking ACTION_EXPORT_PARTICIPANTS is denied CSV export with 403 Forbidden.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    volunteer = sec_audit_fixture["volunteer_user"]

    auth_user(volunteer)

    resp = client.get(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/roster-export",
    )
    assert resp.status_code == 403


# =========================================================================
# 5. Staff Authorization & Object-Level Access Isolation
# =========================================================================

def test_cross_event_check_in_isolation(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    Attempting to check in an attendee from Event 2 using Event 1's endpoint fails with 400/404,
    preventing sibling-event tampering even if staff has permissions.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    event2 = sec_audit_fixture["event2"]
    lead_user = sec_audit_fixture["lead_user"]

    # Register an attendee in Event 2 directly
    from app.services.registration import create_individual_registration
    get_or_create_registration_settings(db, org.id, event2.id, is_open=True)
    res2 = create_individual_registration(
        db,
        organization_id=org.id,
        event_id=event2.id,
        full_name="Event2 Attendee",
        email="event2.user@test.edu",
    )
    db.commit()
    tkt2 = res2.issued_tickets[0].raw_pass_token

    auth_user(lead_user)

    # Attempt to check in Event 2 ticket on Event 1 endpoint
    resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": tkt2, "method": "qr_scan", "station_id": "STATION-1"},
    )
    assert resp.status_code in (400, 404)


def test_cross_tenant_isolation(client: TestClient, sec_audit_fixture, auth_user):
    """
    Staff from Organization A attempting to access Organization B's endpoints receives 404.
    """
    alien_org = sec_audit_fixture["alien_org"]
    alien_event = sec_audit_fixture["alien_event"]
    lead_user = sec_audit_fixture["lead_user"]

    auth_user(lead_user)

    resp = client.get(
        f"/api/v1/organizations/{alien_org.id}/events/{alien_event.id}/participants",
    )
    assert resp.status_code == 404


def test_desk_volunteer_cannot_void_check_in(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    Desk volunteers cannot void check-ins; only managers with ACTION_CORRECT_CHECK_IN can do so.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    volunteer = sec_audit_fixture["volunteer_user"]
    lead = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]

    reg_payload = {
        "registration_type": "individual",
        "contact_email": "void.test@test.edu",
        "participants": [{"full_name": "Void Candidate", "email": "void.test@test.edu"}],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Check in as volunteer
    auth_user(volunteer)
    ci_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_code, "method": "qr_scan", "station_id": "GATE-A"},
    )
    assert ci_resp.status_code == 200
    check_in_id = ci_resp.json()["check_in_id"]

    # Volunteer tries to void -> 403 Forbidden
    void_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{check_in_id}/void",
        json={"reason": "Accidental scan made by volunteer"},
    )
    assert void_resp.status_code == 403


def test_manager_void_check_in_validation_and_audit(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    Event Lead voids a check-in with mandatory >= 10 char reason:
    - Reason < 10 chars is rejected with 422
    - Reason >= 10 chars succeeds, decrements attended count, marks check-in voided,
      and records an immutable CheckInCorrection audit row.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]

    reg_payload = {
        "registration_type": "individual",
        "contact_email": "manager.void@test.edu",
        "participants": [{"full_name": "Manager Void Target", "email": "manager.void@test.edu"}],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    auth_user(lead)

    # Check in
    ci_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_code, "method": "qr_scan", "station_id": "GATE-B"},
    )
    assert ci_resp.status_code == 200
    check_in_id = ci_resp.json()["check_in_id"]

    # Reason < 10 chars rejected
    bad_void = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{check_in_id}/void",
        json={"reason": "mistake"},
    )
    assert bad_void.status_code == 422

    # Valid void >= 10 chars
    good_void = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins/{check_in_id}/void",
        json={"reason": "Scanned wrong attendee pass at registration desk"},
    )
    assert good_void.status_code == 200
    assert good_void.json()["check_in_status"] == "voided"

    # Verify audit correction record exists in database
    corr = db.execute(
        select(CheckInCorrection).where(CheckInCorrection.check_in_id == uuid.UUID(check_in_id))
    ).scalar_one_or_none()
    assert corr is not None
    assert corr.previous_status == "valid"
    assert corr.new_status == "voided"
    assert corr.corrected_by_user_id == lead.id
    assert "Scanned wrong attendee pass" in corr.reason


def test_duplicate_check_in_rejection_and_idempotency(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    Submitting check-in for an already checked-in ticket fails with 409 Conflict (or 400),
    does not create duplicate CheckIn rows, and does not increment attended count twice.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]
    settings1 = sec_audit_fixture["settings1"]

    reg_payload = {
        "registration_type": "individual",
        "contact_email": "dup.scan@test.edu",
        "participants": [{"full_name": "Dup Scan Target", "email": "dup.scan@test.edu"}],
    }
    reg_resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=reg_payload)
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    auth_user(lead)

    # First check-in
    ci1 = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_code, "method": "qr_scan", "station_id": "GATE-C"},
    )
    assert ci1.status_code == 200
    assert ci1.json()["status"] == "verified"

    db.refresh(settings1)
    attended_after_first = settings1.current_attended_count

    # Second check-in attempt
    ci2 = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": pass_code, "method": "qr_scan", "station_id": "GATE-C"},
    )
    assert ci2.status_code == 200
    assert ci2.json()["status"] == "already_checked_in"
    assert ci2.json()["check_in_id"] == ci1.json()["check_in_id"]

    # Attended count must remain unchanged
    db.refresh(settings1)
    assert settings1.current_attended_count == attended_after_first


# =========================================================================
# 6. Capacity Accounting, Rollback & Boundary Invariants
# =========================================================================

def test_team_registration_all_or_nothing_capacity_and_rollback(client: TestClient, sec_audit_fixture, db):
    """
    When remaining capacity is insufficient for a team size, the entire submission fails
    with 400 Bad Request, rolling back without creating phantom participants or partial tickets.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    reg_key = sec_audit_fixture["reg_key"]
    settings1 = sec_audit_fixture["settings1"]

    # Set capacity limit strictly to current confirmed + 2
    settings1.capacity_limit = settings1.current_confirmed_count + 2
    db.commit()

    # Attempt to register team of 3 (needs 3 slots, but only 2 available)
    payload_overflow = {
        "registration_type": "team",
        "team_name": "Team OverCapacity",
        "contact_email": "over@capacity.org",
        "participants": [
            {"full_name": "Member A", "email": "a@cap.org"},
            {"full_name": "Member B", "email": "b@cap.org"},
            {"full_name": "Member C", "email": "c@cap.org"},
        ],
    }

    resp = client.post(f"/api/v1/public/events/{reg_key}/registrations", json=payload_overflow)
    assert resp.status_code == 400
    assert "cannot accommodate" in resp.json()["detail"].lower()

    # Verify no phantom participants were created
    phantom_parts = list(
        db.execute(
            select(Participant).where(Participant.email_normalized.in_(["a@cap.org", "b@cap.org", "c@cap.org"]))
        ).scalars().all()
    )
    assert len(phantom_parts) == 0


def test_manager_lowering_capacity_limit_does_not_evict_attendees(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    When an event manager reduces the capacity_limit below current confirmed count:
    - current_confirmed_count is preserved without evicting registered attendees.
    - Subsequent registrations are blocked with 400.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]
    settings1 = sec_audit_fixture["settings1"]

    # Register 1 individual
    client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "safe.confirmed@test.edu",
            "participants": [{"full_name": "Safe Confirmed", "email": "safe.confirmed@test.edu"}],
        },
    )

    db.refresh(settings1)
    confirmed_before = settings1.current_confirmed_count
    assert confirmed_before > 0

    # Manager lowers capacity to 0
    auth_user(lead)
    patch_resp = client.put(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings",
        json={"capacity_limit": 0},
    )
    assert patch_resp.status_code == 200

    db.refresh(settings1)
    assert settings1.current_confirmed_count == confirmed_before

    # Attempt new registration -> rejected
    new_reg = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "blocked@test.edu",
            "participants": [{"full_name": "Blocked Attendee", "email": "blocked@test.edu"}],
        },
    )
    assert new_reg.status_code == 400


# =========================================================================
# 7. Registration Settings, Key Rotation & Archival Cascading
# =========================================================================

def test_registration_key_rotation_immediately_invalidates_old_key(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    When a manager rotates the registration_key:
    - Old key immediately returns 404.
    - New key is returned and allows registration.
    - Previously issued admission passes remain valid.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead = sec_audit_fixture["lead_user"]
    old_key = sec_audit_fixture["reg_key"]

    # Register attendee under old key
    reg_resp = client.post(
        f"/api/v1/public/events/{old_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "pre.rotation@test.edu",
            "participants": [{"full_name": "Pre Rotation", "email": "pre.rotation@test.edu"}],
        },
    )
    assert reg_resp.status_code == 201
    pass_code = reg_resp.json()["passes"][0]["pass_code"]

    # Manager rotates registration key
    auth_user(lead)
    patch_resp = client.put(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/registration-settings",
        json={"rotate_registration_key": True},
    )
    assert patch_resp.status_code == 200
    new_key = patch_resp.json()["public_registration_key"]
    assert new_key is not None
    assert new_key != old_key

    # Old key immediately returns 404
    old_resp = client.get(f"/api/v1/public/events/{old_key}")
    assert old_resp.status_code == 404

    # New key resolves 200
    new_resp = client.get(f"/api/v1/public/events/{new_key}")
    assert new_resp.status_code == 200

    # Previously issued pass remains verifiable under the new key
    pass_verify = client.post(
        f"/api/v1/public/events/{new_key}/passes/verify",
        json={"pass_code": pass_code},
    )
    assert pass_verify.status_code == 200
    assert pass_verify.json()["participant_name"] == "Pre Rotation"


def test_archiving_event_or_parent_program_returns_404(client: TestClient, sec_audit_fixture, db):
    """
    When an event or its parent program is archived:
    - Public discovery returns 404.
    - Staff operations return 404.
    """
    event1 = sec_audit_fixture["event1"]
    prog = sec_audit_fixture["prog"]
    reg_key = sec_audit_fixture["reg_key"]

    # 1. Archive event
    event1.status = "archived"
    event1.archived_at = datetime.now(timezone.utc)
    db.commit()

    resp = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp.status_code == 404

    # Unarchive event, archive parent program
    event1.status = "published"
    event1.archived_at = None
    prog.status = "archived"
    prog.archived_at = datetime.now(timezone.utc)
    db.commit()

    resp_prog_arch = client.get(f"/api/v1/public/events/{reg_key}")
    assert resp_prog_arch.status_code == 404


# =========================================================================
# 8. Single Active Pass Invariant & Reissue Revocation
# =========================================================================

def test_ticket_reissue_revokes_old_pass_and_maintains_single_active_ticket(client: TestClient, sec_audit_fixture, auth_user, db):
    """
    Reissuing an admission pass revokes the prior ticket.
    Scanning the old pass token fails; scanning the newly issued token succeeds.
    Exactly one active ticket exists for the participant.
    """
    org = sec_audit_fixture["org"]
    event1 = sec_audit_fixture["event1"]
    lead = sec_audit_fixture["lead_user"]
    reg_key = sec_audit_fixture["reg_key"]

    reg_resp = client.post(
        f"/api/v1/public/events/{reg_key}/registrations",
        json={
            "registration_type": "individual",
            "contact_email": "lost.phone@test.edu",
            "participants": [{"full_name": "Lost Phone User", "email": "lost.phone@test.edu"}],
        },
    )
    assert reg_resp.status_code == 201
    p_id = reg_resp.json()["passes"][0]["participant_id"]
    old_token = reg_resp.json()["passes"][0]["pass_code"]

    auth_user(lead)

    # Reissue pass
    reissue_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/participants/{p_id}/reissue-pass",
        json={"reason": "Attendee lost mobile device with original pass QR"},
    )
    assert reissue_resp.status_code == 200
    new_token = reissue_resp.json()["pass_code"]
    assert new_token != old_token

    # Scanning old token fails
    old_check = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": old_token, "method": "qr_scan", "station_id": "GATE-D"},
    )
    assert old_check.status_code in (400, 404)

    # Scanning new token succeeds
    new_check = client.post(
        f"/api/v1/organizations/{org.id}/events/{event1.id}/check-ins",
        json={"pass_code": new_token, "method": "qr_scan", "station_id": "GATE-D"},
    )
    assert new_check.status_code == 200

