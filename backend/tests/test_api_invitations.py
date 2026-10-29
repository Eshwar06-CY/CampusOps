import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.invitation import Invitation
from app.models.organization import Organization
from app.services.organization import create_organization, verify_organization


def test_invitation_creation_fails_closed_when_email_unconfigured(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
):
    """
    Verify FPC-06 fail-closed behavior:
    If transactional email provider is unconfigured, POST /invitations returns 503
    and persists NO invitation row in the database.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)

    # Note: test_email_sink is NOT passed, so default email service is unconfigured
    payload = {
        "email": "invitee@campus.edu",
        "role_name": "OFFICE_BEARER",
        "scope_type": "organization",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=payload)
    assert resp.status_code == 503
    assert "email provider is not configured" in resp.json()["detail"]

    # Verify database has zero invitations
    count = db.query(Invitation).filter(Invitation.organization_id == org.id).count()
    assert count == 0


def test_invitation_creation_rolls_back_on_email_delivery_exception(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
    monkeypatch,
):
    """
    Finding 3 Regression Test:
    If email delivery raises an unexpected exception (e.g. connection timeout),
    the endpoint cleanly rolls back, returns HTTP 503, and leaves no orphan invitation rows.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)

    def crashing_send(*args, **kwargs):
        raise ConnectionResetError("Simulated SMTP/network connection reset")

    monkeypatch.setattr(test_email_sink, "send_invitation_email", crashing_send)

    payload = {
        "email": "invitee_crash@campus.edu",
        "role_name": "OFFICE_BEARER",
        "scope_type": "organization",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=payload)
    assert resp.status_code == 503
    assert "Failed to deliver" in resp.json()["detail"]

    # Verify no orphan invitation row was left in the database
    count = db.query(Invitation).filter(Invitation.email_normalized == "invitee_crash@campus.edu").count()
    assert count == 0



def test_invitation_creation_success_with_sink(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """
    Verify invitation creation succeeds when email sink is configured:
    - HTTP 201 Created.
    - Token delivered to email sink.
    - Raw token and token hash are NEVER exposed in HTTP response.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)

    payload = {
        "email": "invitee@campus.edu",
        "role_name": "OFFICE_BEARER",
        "scope_type": "organization",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Invariants on response schema
    assert "raw_token" not in data
    assert "token" not in data
    assert "token_hash" not in data
    assert data["email"] == "invitee@campus.edu"
    assert data["role_name"] == "OFFICE_BEARER"
    assert data["status"] == "pending"
    assert data["organization_id"] == str(org.id)

    # Token was securely delivered to email sink
    raw_token = test_email_sink.get_latest_token_for("invitee@campus.edu")
    assert raw_token is not None
    assert len(raw_token) > 20


def test_invitation_primary_admin_role_rejected(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """Verify attempting to invite a PRIMARY_ADMIN is rejected with 403."""
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)

    payload = {
        "email": "candidate@campus.edu",
        "role_name": "PRIMARY_ADMIN",
        "scope_type": "organization",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=payload)
    assert resp.status_code == 403
    assert "Primary Workspace Administrator cannot be granted via invitation" in resp.json()["detail"]


def test_invitation_nonexistent_department_scope_rejected_with_400(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """
    Verify nonexistent department scope is rejected with HTTP 400 Bad Request.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)

    # Department scope with nonexistent department
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={
            "email": "deplead@campus.edu",
            "role_name": "DEPARTMENT_LEAD",
            "scope_type": "department",
            "scope_id": fake_id,
        },
    )
    assert resp.status_code == 400
    assert f"Department '{fake_id}' not found." in resp.json()["detail"]


def test_invitation_blocked_in_unverified_organization(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
    test_email_sink,
):
    """Verify invitation creation is blocked when organization is pending_verification."""
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    # Not verified

    auth_user(creator)

    payload = {
        "email": "invitee@campus.edu",
        "role_name": "OFFICE_BEARER",
        "scope_type": "organization",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/invitations", json=payload)
    assert resp.status_code == 403


def test_accept_invitation_lifecycle(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """
    Verify complete invitation acceptance flow:
    1. Creator issues invitation.
    2. Invitee accepts via POST /invitations/accept with token in body.
    3. Membership and role assignment are established.
    4. Replay attempt fails with 400.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Creator invites invitee
    auth_user(creator)
    client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "member@campus.edu", "role_name": "OFFICE_BEARER", "scope_type": "organization"},
    )
    raw_token = test_email_sink.get_latest_token_for("member@campus.edu")

    # Invitee authenticates and accepts
    invitee = create_synthetic_user("member@campus.edu", "New Member")
    auth_user(invitee)

    accept_resp = client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
    )
    assert accept_resp.status_code == 200
    data = accept_resp.json()
    assert data["organization_id"] == str(org.id)
    assert data["role_name"] == "OFFICE_BEARER"
    assert data["status"] == "active"

    # Invitee profile now shows active membership
    me_resp = client.get("/api/v1/me")
    assert me_resp.status_code == 200
    me_orgs = [m["organization_id"] for m in me_resp.json()["memberships"]]
    assert str(org.id) in me_orgs

    # Replay attempt fails
    replay_resp = client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
    )
    assert replay_resp.status_code == 400


def test_accept_invitation_email_mismatch_rejected(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """Verify accepting an invitation with the wrong user email returns 403."""
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)
    client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "intended@campus.edu", "role_name": "OFFICE_BEARER", "scope_type": "organization"},
    )
    raw_token = test_email_sink.get_latest_token_for("intended@campus.edu")

    # Attacker tries to accept with different email
    attacker = create_synthetic_user("attacker@campus.edu", "Attacker")
    auth_user(attacker)

    resp = client.post("/api/v1/invitations/accept", json={"token": raw_token})
    assert resp.status_code == 403
    assert "intended@campus.edu" in resp.json()["detail"]


def test_revoke_invitation_lifecycle(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
    test_email_sink,
):
    """
    Verify invitation revocation:
    - Primary Admin revokes -> 200 OK and status 'revoked'.
    - Subsequent acceptance fails with 400 Bad Request.
    """
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="College", club_name="Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    auth_user(creator)
    inv_resp = client.post(
        f"/api/v1/organizations/{org.id}/invitations",
        json={"email": "to_revoke@campus.edu", "role_name": "OFFICE_BEARER", "scope_type": "organization"},
    )
    inv_id = inv_resp.json()["id"]
    raw_token = test_email_sink.get_latest_token_for("to_revoke@campus.edu")

    # Revoke
    revoke_resp = client.post(f"/api/v1/organizations/{org.id}/invitations/{inv_id}/revoke")
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"

    # Acceptance of revoked token fails
    invitee = create_synthetic_user("to_revoke@campus.edu", "Target")
    auth_user(invitee)
    accept_resp = client.post("/api/v1/invitations/accept", json={"token": raw_token})
    assert accept_resp.status_code == 400
    assert "revoked" in accept_resp.json()["detail"].lower()
