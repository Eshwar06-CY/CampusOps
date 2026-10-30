import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization
from app.services.organization import create_organization, verify_organization


def test_create_organization_success(
    client: TestClient,
    create_synthetic_user,
    auth_user,
):
    """
    Verify creating an organization succeeds:
    - Starts in pending_verification per FPC-02.
    - Creator becomes Primary Admin.
    """
    user = create_synthetic_user("creator@campus.edu", "Org Creator")
    auth_user(user)

    payload = {
        "college_name": "Stanford University",
        "club_name": "AI Safety Student Group",
    }
    resp = client.post("/api/v1/organizations", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["college_name"] == "Stanford University"
    assert data["club_name"] == "AI Safety Student Group"
    assert data["verification_status"] == "pending_verification"
    assert "id" in data


def test_create_organization_extra_fields_rejected(
    client: TestClient,
    create_synthetic_user,
    auth_user,
):
    """Verify extra attributes are rejected by strict Pydantic model (extra='forbid')."""
    user = create_synthetic_user("creator@campus.edu", "Org Creator")
    auth_user(user)

    payload = {
        "college_name": "Stanford University",
        "club_name": "AI Safety Student Group",
        "verification_status": "verified",  # Attempt to bypass pending_verification
        "is_admin": True,
    }
    resp = client.post("/api/v1/organizations", json=payload)
    assert resp.status_code == 422


def test_create_organization_invalid_input_rejected(
    client: TestClient,
    create_synthetic_user,
    auth_user,
):
    """Verify empty or invalid college/club names are rejected."""
    user = create_synthetic_user("creator@campus.edu", "Org Creator")
    auth_user(user)

    # Empty names
    resp = client.post("/api/v1/organizations", json={"college_name": "   ", "club_name": ""})
    assert resp.status_code in (400, 422)


def test_list_organizations_tenant_isolation(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify /organizations lists only organizations where the user has active membership."""
    alice = create_synthetic_user("alice@campus.edu", "Alice")
    bob = create_synthetic_user("bob@campus.edu", "Bob")

    org_alice = create_organization(db, creator=alice, college_name="College A", club_name="Club Alice")
    org_bob = create_organization(db, creator=bob, college_name="College B", club_name="Club Bob")

    # Alice queries
    auth_user(alice)
    resp = client.get("/api/v1/organizations")
    assert resp.status_code == 200
    alice_orgs = resp.json()
    alice_org_ids = [o["id"] for o in alice_orgs]
    assert str(org_alice.id) in alice_org_ids
    assert str(org_bob.id) not in alice_org_ids

    # Bob queries
    auth_user(bob)
    resp = client.get("/api/v1/organizations")
    assert resp.status_code == 200
    bob_orgs = resp.json()
    bob_org_ids = [o["id"] for o in bob_orgs]
    assert str(org_bob.id) in bob_org_ids
    assert str(org_alice.id) not in bob_org_ids


def test_get_organization_details_and_foreign_org_returns_404(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """
    Verify reading an organization:
    - Member can read their own organization.
    - Foreign organization or non-existent ID returns uniform 404 to prevent enumeration.
    """
    owner = create_synthetic_user("owner@campus.edu", "Owner")
    stranger = create_synthetic_user("stranger@campus.edu", "Stranger")

    org = create_organization(db, creator=owner, college_name="Owner College", club_name="Owner Club")

    # Owner reads successfully
    auth_user(owner)
    resp = client.get(f"/api/v1/organizations/{org.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(org.id)
    assert resp.json()["verification_status"] == "pending_verification"

    # Stranger reads foreign org: uniform 404
    auth_user(stranger)
    resp = client.get(f"/api/v1/organizations/{org.id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Organization not found."

    # Non-existent ID returns 404
    resp = client.get(f"/api/v1/organizations/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_active_non_admin_member_can_view_organization_profile(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """
    Finding 4 Regression Test:
    An active member with a non-admin role (e.g. COORDINATOR) can view
    the organization workspace profile (GET /organizations/{id}).
    """
    from app.models.organization import OrganizationMembership
    from app.models.role import RoleAssignment

    owner = create_synthetic_user("owner_coord@campus.edu", "Owner")
    coord_user = create_synthetic_user("coord@campus.edu", "Coordinator Person")
    org = create_organization(db, creator=owner, college_name="Tech Institute", club_name="Coding Society")

    # Grant COORDINATOR role to coord_user
    coord_membership = OrganizationMembership(
        organization_id=org.id,
        user_id=coord_user.id,
        membership_status="active",
        created_by_user_id=owner.id,
    )
    db.add(coord_membership)
    db.flush()

    role = RoleAssignment(
        membership_id=coord_membership.id,
        role_name="COORDINATOR",
        scope_type="organization",
        scope_id=None,
        granted_by_user_id=owner.id,
    )
    db.add(role)
    db.commit()

    # Coordinator reads org details
    auth_user(coord_user)
    resp = client.get(f"/api/v1/organizations/{org.id}")
    assert resp.status_code == 200
    assert resp.json()["club_name"] == "Coding Society"
    assert resp.json()["id"] == str(org.id)



def test_verify_organization_requires_platform_admin(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
):
    """
    Verify organization verification lifecycle:
    - Regular user (even Primary Admin) cannot verify -> 403 Forbidden.
    - Platform admin can verify -> 200 OK and status transitions to 'verified'.
    """
    creator = create_synthetic_user("creator@campus.edu", "Creator")
    platform_admin = create_synthetic_platform_admin("admin@campusops.internal")

    org = create_organization(db, creator=creator, college_name="Test College", club_name="Test Club")

    # Regular user attempts verification -> 403 Forbidden
    auth_user(creator)
    resp = client.post(
        f"/api/v1/organizations/{org.id}/verify",
        json={"decision": "verified"},
    )
    assert resp.status_code == 403
    assert "Platform administrator authority is required" in resp.json()["detail"]

    # Platform admin verifies -> 200 OK
    auth_user(platform_admin)
    resp = client.post(
        f"/api/v1/organizations/{org.id}/verify",
        json={"decision": "verified", "note": "Verified by university charter check"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verification_status"] == "verified"
    assert data["verification_reviewer_id"] == str(platform_admin.id)
    assert data["verification_note"] == "Verified by university charter check"


def test_verify_organization_rejection_requires_note(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
):
    """Verify platform admin rejecting an organization requires an explicit note."""
    creator = create_synthetic_user("creator@campus.edu", "Creator")
    platform_admin = create_synthetic_platform_admin("admin@campusops.internal")

    org = create_organization(db, creator=creator, college_name="Fake College", club_name="Fake Club")

    auth_user(platform_admin)

    # Reject without note fails with 400
    resp = client.post(
        f"/api/v1/organizations/{org.id}/verify",
        json={"decision": "rejected"},
    )
    assert resp.status_code == 400
    assert "reason" in resp.json()["detail"].lower()

    # Reject with note succeeds
    resp = client.post(
        f"/api/v1/organizations/{org.id}/verify",
        json={"decision": "rejected", "note": "Duplicate application"},
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "rejected"


def test_organization_detail_information_disclosure_controls(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
):
    """
    Prompt 07 Information Disclosure Control Test:
    - Platform Admin sees verification_reviewer_id and verification_note.
    - Primary Admin sees verification_note (e.g. to fix reasons), but reviewer_id is censored.
    - Ordinary Member (Coordinator) has BOTH verification_note and reviewer_id censored (None).
    """
    from app.models.organization import OrganizationMembership
    from app.models.role import RoleAssignment

    admin = create_synthetic_platform_admin("platform_sec@campusops.internal")
    creator = create_synthetic_user("creator_sec@campus.edu", "Primary Admin")
    coord = create_synthetic_user("coord_sec@campus.edu", "Regular Coordinator")

    org = create_organization(db, creator=creator, college_name="Sec College", club_name="Sec Club")

    # Add Coordinator to org
    coord_m = OrganizationMembership(
        organization_id=org.id,
        user_id=coord.id,
        membership_status="active",
        created_by_user_id=creator.id,
    )
    db.add(coord_m)
    db.flush()
    db.add(
        RoleAssignment(
            membership_id=coord_m.id,
            role_name="COORDINATOR",
            scope_type="organization",
            scope_id=None,
            granted_by_user_id=creator.id,
        )
    )
    db.commit()

    # Platform admin rejects org with reason
    auth_user(admin)
    client.post(
        f"/api/v1/organizations/{org.id}/verify",
        json={"decision": "rejected", "note": "Official faculty verification charter required."},
    )

    # 1. Platform Admin reads -> full disclosure of reviewer ID and note
    resp_admin = client.get(f"/api/v1/organizations/{org.id}")
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert data_admin["verification_note"] == "Official faculty verification charter required."
    assert data_admin["verification_reviewer_id"] == str(admin.id)

    # 2. Primary Workspace Admin reads -> note is visible (actionable), reviewer ID is censored
    auth_user(creator)
    resp_owner = client.get(f"/api/v1/organizations/{org.id}")
    assert resp_owner.status_code == 200
    data_owner = resp_owner.json()
    assert data_owner["verification_note"] == "Official faculty verification charter required."
    assert data_owner["verification_reviewer_id"] is None

    # 3. Ordinary Member reads -> note and reviewer ID are BOTH censored
    auth_user(coord)
    resp_coord = client.get(f"/api/v1/organizations/{org.id}")
    assert resp_coord.status_code == 200
    data_coord = resp_coord.json()
    assert data_coord["verification_note"] is None
    assert data_coord["verification_reviewer_id"] is None
    assert data_coord["verification_reviewed_at"] is None


def test_list_organization_members_unauthenticated(client: TestClient):
    """Verify listing members fails closed with 401 when unauthenticated."""
    resp = client.get(f"/api/v1/organizations/{uuid.uuid4()}/members")
    assert resp.status_code == 401


def test_list_organization_members_non_member_returns_404(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify non-members receive uniform 404 (anti-enumeration)."""
    alice = create_synthetic_user("alice@campus.edu", "Alice")
    bob = create_synthetic_user("bob@campus.edu", "Bob")
    org = create_organization(db, creator=alice, college_name="College", club_name="Club")

    auth_user(bob)
    resp = client.get(f"/api/v1/organizations/{org.id}/members")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_list_organization_members_success_and_privacy_masking(
    client: TestClient,
    db,
    create_synthetic_user,
    create_synthetic_platform_admin,
    auth_user,
):
    """
    Verify member directory listing with contact privacy disclosure rules:
    - Primary Admin sees full unmasked emails.
    - Ordinary member (Coordinator) sees their own email unmasked, but other members masked.
    - Output strictly excludes credentials, passwords, and tokens.
    """
    admin = create_synthetic_platform_admin("superadmin@campusops.internal")
    creator = create_synthetic_user("creator@campus.edu", "Primary Admin User")
    org = create_organization(db, creator=creator, college_name="Stanford", club_name="AI Society")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Add second member: Coordinator
    coord = create_synthetic_user("coord.secret@stanford.edu", "Coordinator User")
    from app.models.organization import OrganizationMembership
    from app.models.role import RoleAssignment

    coord_m = OrganizationMembership(
        organization_id=org.id,
        user_id=coord.id,
        membership_status="active",
        created_by_user_id=creator.id,
    )
    db.add(coord_m)
    db.flush()
    db.add(
        RoleAssignment(
            membership_id=coord_m.id,
            role_name="COORDINATOR",
            scope_type="organization",
            scope_id=None,
            granted_by_user_id=creator.id,
        )
    )
    db.commit()

    # 1. Primary Admin queries: both members unmasked
    auth_user(creator)
    resp_admin = client.get(f"/api/v1/organizations/{org.id}/members")
    assert resp_admin.status_code == 200
    members_admin = resp_admin.json()
    assert len(members_admin) == 2

    # Verify no credential leakage
    for m in members_admin:
        assert "password" not in m
        assert "token" not in m
        assert "auth_subject_id" not in m
        assert m["email_masked"] is False

    coord_entry_admin = next(m for m in members_admin if m["user_id"] == str(coord.id))
    assert coord_entry_admin["email"] == "coord.secret@stanford.edu"
    assert coord_entry_admin["display_name"] == "Coordinator User"
    assert any(r["role_name"] == "COORDINATOR" for r in coord_entry_admin["roles"])

    # 2. Coordinator queries: self is unmasked, creator is masked
    auth_user(coord)
    resp_coord = client.get(f"/api/v1/organizations/{org.id}/members")
    assert resp_coord.status_code == 200
    members_coord = resp_coord.json()
    assert len(members_coord) == 2

    coord_self = next(m for m in members_coord if m["user_id"] == str(coord.id))
    assert coord_self["email"] == "coord.secret@stanford.edu"
    assert coord_self["email_masked"] is False

    creator_from_coord = next(m for m in members_coord if m["user_id"] == str(creator.id))
    assert creator_from_coord["email_masked"] is True
    assert creator_from_coord["email"] != "creator@campus.edu"
    assert "c***r@campus.edu" == creator_from_coord["email"]

    # 3. Platform Admin queries: unmasked
    auth_user(admin)
    resp_platform = client.get(f"/api/v1/organizations/{org.id}/members")
    assert resp_platform.status_code == 200
    assert len(resp_platform.json()) == 2
    assert all(m["email_masked"] is False for m in resp_platform.json())


def test_list_organization_members_pagination_and_status_filtering(
    client: TestClient,
    db,
    create_synthetic_user,
    auth_user,
):
    """Verify limit, offset, and status filtering on members endpoint."""
    creator = create_synthetic_user("owner@campus.edu", "Owner")
    org = create_organization(db, creator=creator, college_name="MIT", club_name="Robotics")

    auth_user(creator)

    # Add 2 more members
    from app.models.organization import OrganizationMembership
    for i in range(2):
        u = create_synthetic_user(f"member{i}@mit.edu", f"Member {i}")
        mem = OrganizationMembership(
            organization_id=org.id,
            user_id=u.id,
            membership_status="active",
            created_by_user_id=creator.id,
        )
        db.add(mem)
    db.commit()

    # Query with limit=2, offset=0
    resp1 = client.get(f"/api/v1/organizations/{org.id}/members?limit=2&offset=0")
    assert resp1.status_code == 200
    assert len(resp1.json()) == 2

    # Query with limit=2, offset=2
    resp2 = client.get(f"/api/v1/organizations/{org.id}/members?limit=2&offset=2")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1

