import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization, OrganizationMembership
from app.models.event import Event, EventLeadAssignment
from app.services.organization import create_organization, verify_organization
from app.services.event import create_event, assign_event_lead, get_active_event_leads


@pytest.fixture
def lead_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin@internal.gov")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Tech Institute", club_name="Coding Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Regular member in same org
    member_user = create_synthetic_user("member@org.edu", "Member User")
    member_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=member_user.id,
        membership_status="active",
    )
    db.add(member_mb)
    db.flush()

    # Another org and member for cross-tenant tests
    creator_b = create_synthetic_user("creator_b@other.edu", "Other Org Creator")
    org_b = create_organization(db, creator=creator_b, college_name="Other Institute", club_name="Robo Club")
    verify_organization(db, admin_user=admin, organization_id=org_b.id, decision="verified")

    other_user = create_synthetic_user("other@other.edu", "Other Member")
    other_mb = OrganizationMembership(
        organization_id=org_b.id,
        user_id=other_user.id,
        membership_status="active",
    )
    db.add(other_mb)
    db.flush()

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "member_user": member_user,
        "member_mb": member_mb,
        "creator_b": creator_b,
        "org_b": org_b,
        "other_user": other_user,
        "other_mb": other_mb,
    }


def test_assign_and_list_event_leads_success(client: TestClient, db, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    member_mb = lead_fixture["member_mb"]
    auth_user(creator)

    # 1. Create an event
    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Annual Hackathon"})
    assert resp_ev.status_code == 201
    event_id = resp_ev.json()["id"]

    # 2. Initially no leads
    list_resp = client.get(f"/api/v1/organizations/{org.id}/events/{event_id}/leads")
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # 3. Assign member as lead
    assign_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(member_mb.id)},
    )
    assert assign_resp.status_code == 201
    assign_data = assign_resp.json()
    assert assign_data["event_id"] == event_id
    assert assign_data["membership_id"] == str(member_mb.id)
    assert assign_data["assigned_by_user_id"] == str(creator.id)
    assert assign_data["revoked_at"] is None

    # 4. List leads again
    list_resp2 = client.get(f"/api/v1/organizations/{org.id}/events/{event_id}/leads")
    assert list_resp2.status_code == 200
    leads = list_resp2.json()
    assert len(leads) == 1
    assert leads[0]["id"] == assign_data["id"]


def test_assign_duplicate_event_lead_rejected_with_409(client: TestClient, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    member_mb = lead_fixture["member_mb"]
    auth_user(creator)

    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Design Sprint"})
    event_id = resp_ev.json()["id"]

    # First assignment
    resp1 = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(member_mb.id)},
    )
    assert resp1.status_code == 201

    # Second assignment of same member to same event -> 409 Conflict
    resp2 = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(member_mb.id)},
    )
    assert resp2.status_code == 409
    assert "already an active event lead" in resp2.json()["detail"].lower()


def test_assign_lead_cross_tenant_membership_rejected(client: TestClient, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    other_mb = lead_fixture["other_mb"]
    auth_user(creator)

    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Org A Summit"})
    event_id = resp_ev.json()["id"]

    # Try assigning member from org_b to event in org_a -> 404 (membership does not exist in org_a)
    resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(other_mb.id)},
    )
    assert resp.status_code == 404
    assert "different organization" in resp.json()["detail"].lower()


def test_assign_lead_to_archived_event_rejected(client: TestClient, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    member_mb = lead_fixture["member_mb"]
    auth_user(creator)

    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Past Event"})
    event_id = resp_ev.json()["id"]

    # Archive the event
    arch_resp = client.post(f"/api/v1/organizations/{org.id}/events/{event_id}/archive")
    assert arch_resp.status_code == 200

    # Attempt lead assignment on archived event -> 404 (archived event not found for active operations)
    resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(member_mb.id)},
    )
    assert resp.status_code == 404
    assert "not found or is archived" in resp.json()["detail"].lower()


def test_revoke_event_lead_and_authority_loss(client: TestClient, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    member_user = lead_fixture["member_user"]
    member_mb = lead_fixture["member_mb"]
    auth_user(creator)

    # 1. Create event
    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "AI Workshop", "venue": "Room 1"})
    event_id = resp_ev.json()["id"]

    # 2. Assign lead
    assign_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads",
        json={"membership_id": str(member_mb.id)},
    )
    assert assign_resp.status_code == 201
    assignment_id = assign_resp.json()["id"]

    # 3. As lead, member_user can update the event
    auth_user(member_user)
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event_id}",
        json={"venue": "Room 101"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["venue"] == "Room 101"

    # 4. As admin, revoke the lead
    auth_user(creator)
    revoke_resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads/{assignment_id}/revoke"
    )
    assert revoke_resp.status_code == 200
    revoke_data = revoke_resp.json()
    assert revoke_data["revoked_at"] is not None

    # 5. Now as member_user, updating the event is forbidden (lost lead authority)
    auth_user(member_user)
    patch_resp2 = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event_id}",
        json={"venue": "Room 102"},
    )
    assert patch_resp2.status_code == 403

    # 6. Attempting to revoke again returns 400
    auth_user(creator)
    revoke_again = client.post(
        f"/api/v1/organizations/{org.id}/events/{event_id}/leads/{assignment_id}/revoke"
    )
    assert revoke_again.status_code == 400
    assert "not found" in revoke_again.json()["detail"].lower()


def test_cross_tenant_isolation_on_event_leads(client: TestClient, lead_fixture, auth_user):
    creator = lead_fixture["creator"]
    org = lead_fixture["org"]
    creator_b = lead_fixture["creator_b"]
    org_b = lead_fixture["org_b"]
    other_mb = lead_fixture["other_mb"]

    # Org A creates event
    auth_user(creator)
    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Org A Secret Meet"})
    event_id = resp_ev.json()["id"]

    # Creator B in Org B attempts to access Org A leads endpoint -> 404 (caller not a member of Org A)
    auth_user(creator_b)
    resp_leads = client.get(f"/api/v1/organizations/{org.id}/events/{event_id}/leads")
    assert resp_leads.status_code == 404

    # Creator B attempts to assign lead to Org A event via Org B URL path -> 404 (event does not belong to Org B)
    resp_assign = client.post(
        f"/api/v1/organizations/{org_b.id}/events/{event_id}/leads",
        json={"membership_id": str(other_mb.id)},
    )
    assert resp_assign.status_code == 404
