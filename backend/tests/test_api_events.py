import uuid
from datetime import date
import pytest
from starlette.testclient import TestClient

from app.services.event import assign_event_lead, create_program
from app.services.organization import create_organization, verify_organization


@pytest.fixture
def event_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin@internal.gov")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Apex University", club_name="Tech Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    program = create_program(
        db,
        creator=creator,
        organization_id=org.id,
        name="Annual Fest",
        planned_start_date=date(2027, 3, 1),
        planned_end_date=date(2027, 3, 10),
    )
    return {"admin": admin, "creator": creator, "org": org, "program": program}


def test_create_standalone_event(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    payload = {
        "name": "RoboWars 2027",
        "description": "Combat robotics",
        "program_id": None,
        "event_date": "2027-04-15",
        "event_end_date": "2027-04-16",
        "planned_start_time": "2027-04-15T10:00:00Z",
        "planned_end_time": "2027-04-16T18:00:00Z",
        "venue": "Campus Grounds",
        "event_format": "in_person",
        "registration_mode": "team",
        "timezone": "Asia/Kolkata",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "RoboWars 2027"
    assert data["program_id"] is None
    assert data["event_date"] == "2027-04-15"
    assert data["event_end_date"] == "2027-04-16"
    assert data["timezone"] == "Asia/Kolkata"
    assert data["registration_mode"] == "team"


def test_create_child_event_under_program(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    program = event_fixture["program"]
    auth_user(creator)

    payload = {
        "name": "Hackathon 2027",
        "program_id": str(program.id),
        "event_date": "2027-03-02",
        "event_end_date": "2027-03-03",
        "planned_start_time": "2027-03-02T18:00:00Z",
        "planned_end_time": "2027-03-03T02:00:00Z",  # multi-day overnight!
        "venue": "CS Lab",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Hackathon 2027"
    assert data["program_id"] == str(program.id)


def test_create_child_event_via_subresource_route(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    program = event_fixture["program"]
    auth_user(creator)

    payload = {
        "name": "Coding Contest",
        "event_date": "2027-03-05",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/programs/{program.id}/events", json=payload)
    assert resp.status_code == 201
    assert resp.json()["program_id"] == str(program.id)


def test_cross_tenant_program_child_event_rejected(
    client: TestClient, db, event_fixture, create_synthetic_user, auth_user
):
    org1 = event_fixture["org"]
    prog1 = event_fixture["program"]

    # Org 2 setup
    creator2 = create_synthetic_user("creator2@org2.edu", "Creator 2")
    org2 = create_organization(db, creator=creator2, college_name="Other College", club_name="Other Club")
    verify_organization(db, admin_user=event_fixture["admin"], organization_id=org2.id, decision="verified")

    auth_user(creator2)

    # Attempt to create event in Org 2 referencing Program from Org 1
    payload = {
        "name": "Intruder Event",
        "program_id": str(prog1.id),
        "event_date": "2027-03-05",
    }
    resp = client.post(f"/api/v1/organizations/{org2.id}/events", json=payload)
    assert resp.status_code == 400
    assert "belongs to org" in resp.json()["detail"] or "different organization" in resp.json()["detail"]


def test_invalid_timezone_rejected(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    payload = {
        "name": "Bad TZ Event",
        "timezone": "Mars/Olympus_Mons",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/events", json=payload)
    assert resp.status_code == 400
    assert "Invalid timezone identifier" in resp.json()["detail"]


def test_invalid_date_order_rejected(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    payload = {
        "name": "Backwards Event",
        "event_date": "2027-04-10",
        "event_end_date": "2027-04-08",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/events", json=payload)
    assert resp.status_code == 400
    assert "Event end date cannot be earlier" in resp.json()["detail"]


def test_single_day_event_inverted_time_rejected(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    payload = {
        "name": "Inverted Time Single Day",
        "event_date": "2027-04-10",
        "event_end_date": "2027-04-10",
        "planned_start_time": "2027-04-10T18:00:00Z",
        "planned_end_time": "2027-04-10T10:00:00Z",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/events", json=payload)
    assert resp.status_code == 400
    assert "Planned end time cannot be earlier" in resp.json()["detail"]


def test_event_outside_parent_program_dates_rejected(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    program = event_fixture["program"]  # 2027-03-01 to 2027-03-10
    auth_user(creator)

    # Event date earlier than program start
    resp_early = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={"name": "Too Early", "program_id": str(program.id), "event_date": "2027-02-25"},
    )
    assert resp_early.status_code == 400
    assert "cannot be earlier than parent program start date" in resp_early.json()["detail"]

    # Event date later than program end
    resp_late = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={"name": "Too Late", "program_id": str(program.id), "event_date": "2027-03-15"},
    )
    assert resp_late.status_code == 400
    assert "cannot be later than parent program end date" in resp_late.json()["detail"]


def test_event_lead_can_update_event(
    client: TestClient, db, event_fixture, create_synthetic_user, auth_user
):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    # Create standalone event
    resp_ev = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={"name": "Tech Expo", "venue": "Hall A"},
    )
    assert resp_ev.status_code == 201
    event_id = resp_ev.json()["id"]

    # Create member in organization
    lead_user = create_synthetic_user("lead@org.edu", "Lead Member")
    from app.models.organization import OrganizationMembership
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=lead_user.id,
        membership_status="active",
    )
    db.add(membership)
    db.flush()

    # Assign member as EVENT_LEAD
    assign_event_lead(
        db, assigner=creator, organization_id=org.id, event_id=uuid.UUID(event_id), membership_id=membership.id
    )

    # Now authenticate as lead_user and update venue
    auth_user(lead_user)
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event_id}",
        json={"venue": "Hall B - Upgraded"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["venue"] == "Hall B - Upgraded"


def test_archiving_event_blocks_further_updates(client: TestClient, db, event_fixture, auth_user):
    creator = event_fixture["creator"]
    org = event_fixture["org"]
    auth_user(creator)

    resp_ev = client.post(f"/api/v1/organizations/{org.id}/events", json={"name": "Temp Event"})
    event_id = resp_ev.json()["id"]

    # Archive
    arch_resp = client.post(f"/api/v1/organizations/{org.id}/events/{event_id}/archive")
    assert arch_resp.status_code == 200
    assert arch_resp.json()["status"] == "archived"

    # Attempt update on archived event
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event_id}",
        json={"name": "New Name After Archive"},
    )
    assert patch_resp.status_code == 404
