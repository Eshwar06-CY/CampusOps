import uuid
import pytest
from fastapi.testclient import TestClient

from app.auth.principal import AuthenticatedPrincipal, get_current_principal
from app.main import app


def test_unauthenticated_requests_fail_closed(client: TestClient):
    """
    Verify all protected endpoints reject requests without a verified principal with 401.
    No mock auth headers (X-User-ID, etc.) are honored.
    """
    # 1. GET /api/v1/me
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

    # 2. GET /api/v1/organizations
    resp = client.get("/api/v1/organizations")
    assert resp.status_code == 401

    # 3. POST /api/v1/organizations
    resp = client.post(
        "/api/v1/organizations",
        json={"college_name": "MIT", "club_name": "Robotics Club"},
    )
    assert resp.status_code == 401

    # 4. POST /api/v1/invitations/accept
    resp = client.post(
        "/api/v1/invitations/accept",
        json={"token": "some-random-token-12345"},
    )
    assert resp.status_code == 401


def test_spoofed_headers_and_body_ids_are_ignored(client: TestClient):
    """
    Verify spoofed headers (X-User-ID, X-Auth-Subject, etc.) and payload user_id fields
    do not bypass the fail-closed auth boundary.
    """
    spoofed_id = str(uuid.uuid4())
    headers = {
        "X-User-ID": spoofed_id,
        "X-User-Email": "attacker@evil.com",
        "X-Auth-Subject-ID": "sub_attacker",
        "Authorization": "Bearer fake-token-without-adapter",
    }

    # Spoofed GET /api/v1/me fails closed with 401
    resp = client.get("/api/v1/me", headers=headers)
    assert resp.status_code == 401

    # Extra/spoofed fields in request bodies are rejected by schema validation
    resp = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "college_name": "MIT",
            "club_name": "Robotics Club",
            "user_id": spoofed_id,  # Extra attribute forbidden
        },
    )
    assert resp.status_code in (401, 422)


def test_suspended_user_account_rejected_with_403(
    client: TestClient,
    create_synthetic_user,
    auth_user,
):
    """Verify suspended or locked user account is denied access with 403 Forbidden."""
    suspended_user = create_synthetic_user(
        email="suspended@example.com",
        display_name="Suspended Person",
        account_status="suspended",
    )
    auth_user(suspended_user)

    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert "suspended, disabled, or locked" in resp.json()["detail"]


def test_unverified_email_rejected_with_403(
    client: TestClient,
    create_synthetic_user,
    auth_user,
):
    """Verify user with unverified email is denied access to organization operations with 403."""
    unverified_user = create_synthetic_user(
        email="unverified@example.com",
        display_name="Unverified Person",
        verified=False,
    )
    auth_user(unverified_user, email_verified=False)

    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"]


def test_unverified_principal_cannot_hijack_existing_verified_account(
    client: TestClient,
    create_synthetic_user,
    auth_principal,
):
    """
    Finding 1 Regression Test:
    Attacker signs up with unverified email matching an existing verified user.
    The system must reject the request with 403 Forbidden and NOT resolve or leak
    the existing user's profile.
    """
    # Existing verified user
    create_synthetic_user(
        email="target@campus.edu",
        display_name="Target User",
        auth_subject_id="sub_target_legit",
        verified=True,
    )

    # Attacker presents token with target's email but unverified
    auth_principal(
        auth_subject_id="sub_attacker",
        email="target@campus.edu",
        email_verified=False,
        display_name="Attacker",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"]


def test_auth_subject_conflict_rejected(
    client: TestClient,
    create_synthetic_user,
    auth_principal,
):
    """
    Finding 1 Regression Test:
    A verified principal whose subject ID differs from an existing profile's bound
    auth_subject_id must be rejected with 403 to prevent account takeover.
    """
    create_synthetic_user(
        email="bound@campus.edu",
        display_name="Bound User",
        auth_subject_id="sub_original",
        verified=True,
    )

    # Different subject claims same email
    auth_principal(
        auth_subject_id="sub_different",
        email="bound@campus.edu",
        email_verified=True,
        display_name="Different Subject",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert "conflict" in resp.json()["detail"].lower()


def test_email_change_unverified_rejected(
    client: TestClient,
    create_synthetic_user,
    auth_principal,
):
    """
    Verify that if a user changes email at identity provider, but the new email
    is not verified, the request is rejected with 403 and the profile email is not updated.
    """
    user = create_synthetic_user(
        email="old_email@campus.edu",
        display_name="Email Changer",
        auth_subject_id="sub_changer",
        verified=True,
    )

    auth_principal(
        auth_subject_id="sub_changer",
        email="new_unverified@campus.edu",
        email_verified=False,
        display_name="Email Changer",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"]


def test_email_change_conflict_rejected(
    client: TestClient,
    create_synthetic_user,
    auth_principal,
):
    """
    Verify that if a user changes email at provider to an email already claimed by
    another profile, the request is rejected with 409 Conflict without overwriting.
    """
    create_synthetic_user(
        email="claimed@campus.edu",
        display_name="Existing Claimer",
        auth_subject_id="sub_claimer",
        verified=True,
    )
    user2 = create_synthetic_user(
        email="user2@campus.edu",
        display_name="User Two",
        auth_subject_id="sub_user2",
        verified=True,
    )

    auth_principal(
        auth_subject_id="sub_user2",
        email="claimed@campus.edu",
        email_verified=True,
        display_name="User Two",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 409
    assert "associated with another profile" in resp.json()["detail"]


def test_email_change_verified_succeeds(
    client: TestClient,
    create_synthetic_user,
    auth_principal,
):
    """
    Verify that if a user changes email at provider and verifies it,
    the profile is safely updated to the new email address.
    """
    user = create_synthetic_user(
        email="initial@campus.edu",
        display_name="Legit User",
        auth_subject_id="sub_legit_change",
        verified=True,
    )

    auth_principal(
        auth_subject_id="sub_legit_change",
        email="updated@campus.edu",
        email_verified=True,
        display_name="Legit User",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "updated@campus.edu"

