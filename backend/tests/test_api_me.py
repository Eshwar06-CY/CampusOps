import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.services.organization import create_organization


def test_me_returns_profile_and_memberships(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify /me returns authenticated user's profile and active memberships with roles."""
    user = create_synthetic_user(
        email="alice@campus.edu",
        display_name="Alice Smith",
    )
    auth_user(user)

    # Create an organization where Alice is Primary Admin
    org = create_organization(
        db=db,
        creator=user,
        college_name="Engineering College",
        club_name="Robotics Club",
    )

    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == str(user.id)
    assert data["email"] == "alice@campus.edu"
    assert data["display_name"] == "Alice Smith"
    assert data["email_verified"] is True
    assert data["account_status"] == "active"
    assert data["is_platform_admin"] is False

    # Check memberships list
    assert len(data["memberships"]) == 1
    m = data["memberships"][0]
    assert m["organization_id"] == str(org.id)
    assert m["organization_name"] == "Robotics Club"
    assert m["membership_status"] == "active"
    assert len(m["roles"]) == 1
    assert m["roles"][0]["role_name"] == "PRIMARY_ADMIN"
    assert m["roles"][0]["scope_type"] == "organization"


def test_me_tenant_isolation_never_leaks_other_users(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify /me only shows the caller's own memberships and never leaks another user's."""
    user1 = create_synthetic_user("user1@campus.edu", "User One")
    user2 = create_synthetic_user("user2@campus.edu", "User Two")

    # user1 creates Org 1
    org1 = create_organization(
        db=db,
        creator=user1,
        college_name="College A",
        club_name="Club One",
    )
    # user2 creates Org 2
    org2 = create_organization(
        db=db,
        creator=user2,
        college_name="College B",
        club_name="Club Two",
    )

    # Authenticate as user1
    auth_user(user1)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user1.id)
    org_ids = [m["organization_id"] for m in data["memberships"]]
    assert str(org1.id) in org_ids
    assert str(org2.id) not in org_ids

    # Authenticate as user2
    auth_user(user2)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user2.id)
    org_ids = [m["organization_id"] for m in data["memberships"]]
    assert str(org2.id) in org_ids
    assert str(org1.id) not in org_ids


def test_me_excludes_inactive_or_removed_memberships(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify /me excludes removed or inactive memberships."""
    user = create_synthetic_user("bob@campus.edu", "Bob")
    org = create_organization(db, creator=user, college_name="College C", club_name="Club C")

    # Mark the membership as removed
    membership = org.memberships[0]
    membership.membership_status = "removed"
    db.commit()

    auth_user(user)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["memberships"]) == 0


def test_me_identifies_platform_admin(
    client: TestClient,
    create_synthetic_platform_admin,
    auth_user,
):
    """Verify /me correctly flags platform admins."""
    admin_user = create_synthetic_platform_admin("superadmin@campusops.internal")
    auth_user(admin_user)

    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    assert resp.json()["is_platform_admin"] is True
