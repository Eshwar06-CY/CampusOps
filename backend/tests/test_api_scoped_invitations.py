import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.event import Department, Event, EventLeadAssignment, Program
from app.services.organization import create_organization, verify_organization
from app.services.event import create_program, create_event, create_department, archive_event, archive_department


@pytest.fixture
def scoped_invitation_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin@internal.gov")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Apex University", club_name="Robotics Society")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Program and standalone event in Org
    program = create_program(db, creator=creator, organization_id=org.id, name="RoboFest 2026")
    event = create_event(db, creator=creator, organization_id=org.id, name="Bot Combat", program_id=program.id)
    dept = create_department(db, creator=creator, organization_id=org.id, name="Hardware & Electronics", program_id=program.id)

    # Another Org for cross-tenant tests
    creator_b = create_synthetic_user("creator_b@other.edu", "Other Creator")
    org_b = create_organization(db, creator=creator_b, college_name="Other University", club_name="AI Society")
    verify_organization(db, admin_user=admin, organization_id=org_b.id, decision="verified")
    event_b = create_event(db, creator=creator_b, organization_id=org_b.id, name="AI Hackathon")
    dept_b = create_department(db, creator=creator_b, organization_id=org_b.id, name="Neural Nets Dept", standalone_event_id=event_b.id)

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "program": program,
        "event": event,
        "dept": dept,
        "creator_b": creator_b,
        "org_b": org_b,
        "event_b": event_b,
        "dept_b": dept_b,
    }


def test_department_scoped_invitation_lifecycle(
    client: TestClient,
    db,
    scoped_invitation_fixture,
    create_synthetic_user,
    auth_user,
    test_email_sink,
):
    """Verify creating and accepting a department-scoped invitation for DEPARTMENT_LEAD."""
    creator = scoped_invitation_fixture["creator"]
    org = scoped_invitation_fixture["org"]
    dept = scoped_invitation_fixture["dept"]

    auth_user(creator)

    invite_payload = {
        "email": "dept_lead_candidate@org.edu",
        "role_name": "DEPARTMENT_LEAD",
        "scope_type": "department",
        "scope_id": str(dept.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=invite_payload)
    assert resp.status_code == 201
    inv_data = resp.json()
    assert inv_data["email"] == "dept_lead_candidate@org.edu"
    assert inv_data["role_name"] == "DEPARTMENT_LEAD"
    assert inv_data["scope_type"] == "department"
    assert inv_data["scope_id"] == str(dept.id)

    # Email delivered to sink
    token = test_email_sink.get_latest_token_for("dept_lead_candidate@org.edu")
    assert token is not None

    # Invitee signs up / authenticates
    invitee = create_synthetic_user("dept_lead_candidate@org.edu", "Dept Lead Invitee")
    auth_user(invitee)

    # Invitee accepts invitation
    accept_resp = client.post("/api/v1/invitations/accept", json={"token": token})
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "active"

    # Verify RoleAssignment created for department
    mb = (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.organization_id == org.id, OrganizationMembership.user_id == invitee.id)
        .first()
    )
    assert mb is not None
    roles = db.query(RoleAssignment).filter(RoleAssignment.membership_id == mb.id).all()
    assert any(r.role_name == "DEPARTMENT_LEAD" and r.scope_type == "department" and r.scope_id == dept.id for r in roles)


def test_event_scoped_invitation_creates_event_lead_assignment(
    client: TestClient,
    db,
    scoped_invitation_fixture,
    create_synthetic_user,
    auth_user,
    test_email_sink,
):
    """
    Verify creating and accepting an event-scoped invitation for EVENT_LEAD.
    Must atomically create both RoleAssignment and EventLeadAssignment.
    """
    creator = scoped_invitation_fixture["creator"]
    org = scoped_invitation_fixture["org"]
    event = scoped_invitation_fixture["event"]

    auth_user(creator)

    invite_payload = {
        "email": "event_lead_candidate@org.edu",
        "role_name": "EVENT_LEAD",
        "scope_type": "event",
        "scope_id": str(event.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=invite_payload)
    assert resp.status_code == 201

    token = test_email_sink.get_latest_token_for("event_lead_candidate@org.edu")
    assert token is not None

    # Invitee authenticates and accepts
    invitee = create_synthetic_user("event_lead_candidate@org.edu", "Event Lead Candidate")
    auth_user(invitee)

    accept_resp = client.post("/api/v1/invitations/accept", json={"token": token})
    assert accept_resp.status_code == 200

    # Verify database state: both RoleAssignment and EventLeadAssignment exist and are active
    mb = (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.organization_id == org.id, OrganizationMembership.user_id == invitee.id)
        .first()
    )
    assert mb is not None

    role = (
        db.query(RoleAssignment)
        .filter(
            RoleAssignment.membership_id == mb.id,
            RoleAssignment.role_name == "EVENT_LEAD",
            RoleAssignment.scope_type == "event",
            RoleAssignment.scope_id == event.id,
        )
        .first()
    )
    assert role is not None
    assert role.revoked_at is None

    lead_assignment = (
        db.query(EventLeadAssignment)
        .filter(
            EventLeadAssignment.organization_id == org.id,
            EventLeadAssignment.event_id == event.id,
            EventLeadAssignment.membership_id == mb.id,
        )
        .first()
    )
    assert lead_assignment is not None
    assert lead_assignment.revoked_at is None

    # Verify newly accepted event lead has lead update permissions on event
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event.id}",
        json={"venue": "Main Arena"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["venue"] == "Main Arena"


def test_invalid_role_scope_combinations_rejected(
    client: TestClient,
    scoped_invitation_fixture,
    auth_user,
    test_email_sink,
):
    """Verify role-scope matrix validation rejects illegal combinations."""
    creator = scoped_invitation_fixture["creator"]
    org = scoped_invitation_fixture["org"]
    event = scoped_invitation_fixture["event"]
    dept = scoped_invitation_fixture["dept"]

    auth_user(creator)

    # 1. DEPARTMENT_LEAD cannot be organization scoped
    r1 = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "u1@org.edu", "role_name": "DEPARTMENT_LEAD", "scope_type": "organization"},
    )
    assert r1.status_code == 400
    assert "scoped to a department" in r1.json()["detail"].lower()

    # 2. DEPARTMENT_LEAD cannot be event scoped
    r2 = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "u2@org.edu", "role_name": "DEPARTMENT_LEAD", "scope_type": "event", "scope_id": str(event.id)},
    )
    assert r2.status_code == 400
    assert "scoped to a department" in r2.json()["detail"].lower()

    # 3. EVENT_LEAD cannot be department scoped
    r3 = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "u3@org.edu", "role_name": "EVENT_LEAD", "scope_type": "department", "scope_id": str(dept.id)},
    )
    assert r3.status_code == 400
    assert "scoped to an event" in r3.json()["detail"].lower()

    # 4. OFFICE_BEARER cannot be department scoped
    r4 = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "u4@org.edu", "role_name": "OFFICE_BEARER", "scope_type": "department", "scope_id": str(dept.id)},
    )
    assert r4.status_code == 400
    assert "scoped to the organization" in r4.json()["detail"].lower()


def test_cross_tenant_scope_rejected_in_invitations(
    client: TestClient,
    scoped_invitation_fixture,
    auth_user,
    test_email_sink,
):
    """Verify invitations cannot reference entities belonging to a different organization."""
    creator = scoped_invitation_fixture["creator"]
    org = scoped_invitation_fixture["org"]
    event_b = scoped_invitation_fixture["event_b"]
    dept_b = scoped_invitation_fixture["dept_b"]

    auth_user(creator)

    # Attempt to invite into Org B's department from Org A
    resp_dept = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "cross_dept@org.edu", "role_name": "DEPARTMENT_LEAD", "scope_type": "department", "scope_id": str(dept_b.id)},
    )
    assert resp_dept.status_code == 400
    assert "different organization" in resp_dept.json()["detail"].lower()

    # Attempt to invite into Org B's event from Org A
    resp_ev = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "cross_event@org.edu", "role_name": "EVENT_LEAD", "scope_type": "event", "scope_id": str(event_b.id)},
    )
    assert resp_ev.status_code == 400
    assert "different organization" in resp_ev.json()["detail"].lower()


def test_archived_target_scope_rejected_in_invitations(
    client: TestClient,
    db,
    scoped_invitation_fixture,
    auth_user,
    test_email_sink,
):
    """Verify invitations cannot reference archived departments or events."""
    creator = scoped_invitation_fixture["creator"]
    org = scoped_invitation_fixture["org"]
    event = scoped_invitation_fixture["event"]
    dept = scoped_invitation_fixture["dept"]

    auth_user(creator)

    # Archive department
    archive_department(db, user=creator, department_id=dept.id)

    # Attempt invitation into archived department
    resp_dept = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "arch_dept@org.edu", "role_name": "DEPARTMENT_LEAD", "scope_type": "department", "scope_id": str(dept.id)},
    )
    assert resp_dept.status_code == 400
    assert "not found" in resp_dept.json()["detail"].lower()

    # Archive event
    archive_event(db, user=creator, event_id=event.id)

    # Attempt invitation into archived event
    resp_ev = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "arch_event@org.edu", "role_name": "EVENT_LEAD", "scope_type": "event", "scope_id": str(event.id)},
    )
    assert resp_ev.status_code == 400
    assert "not found" in resp_ev.json()["detail"].lower()
