import uuid
from datetime import date
import pytest
from starlette.testclient import TestClient

from app.services.event import archive_event, archive_program, create_event, create_program
from app.services.organization import create_organization, verify_organization


@pytest.fixture
def dept_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin@internal.gov")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Apex University", club_name="Tech Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    program = create_program(db, creator=creator, organization_id=org.id, name="Fest 2027")
    child_event = create_event(
        db, creator=creator, organization_id=org.id, name="Child Coding", program_id=program.id
    )
    standalone_event = create_event(
        db, creator=creator, organization_id=org.id, name="Standalone Workshop", program_id=None
    )
    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "program": program,
        "child_event": child_event,
        "standalone_event": standalone_event,
    }


def test_create_program_shared_department(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    program = dept_fixture["program"]
    auth_user(creator)

    payload = {
        "name": "Logistics & Operations",
        "description": "Facilities and equipment",
        "program_id": str(program.id),
        "standalone_event_id": None,
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Logistics & Operations"
    assert data["program_id"] == str(program.id)
    assert data["standalone_event_id"] is None
    assert data["status"] == "active"


def test_create_standalone_event_department(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    standalone_event = dept_fixture["standalone_event"]
    auth_user(creator)

    payload = {
        "name": "Design & Publicity",
        "program_id": None,
        "standalone_event_id": str(standalone_event.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Design & Publicity"
    assert data["program_id"] is None
    assert data["standalone_event_id"] == str(standalone_event.id)


def test_department_under_child_event_rejected(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    child_event = dept_fixture["child_event"]
    auth_user(creator)

    # Attempt to create standalone department pointing to a child event
    payload = {
        "name": "Child Dept",
        "program_id": None,
        "standalone_event_id": str(child_event.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 400
    assert "Child events share program departments" in resp.json()["detail"]


def test_department_exclusive_parent_both_populated_rejected(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    program = dept_fixture["program"]
    standalone_event = dept_fixture["standalone_event"]
    auth_user(creator)

    payload = {
        "name": "Conflicted Dept",
        "program_id": str(program.id),
        "standalone_event_id": str(standalone_event.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 400
    assert "Department must belong to exactly one parent" in resp.json()["detail"]


def test_department_exclusive_parent_neither_populated_rejected(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    auth_user(creator)

    payload = {
        "name": "Orphan Dept",
        "program_id": None,
        "standalone_event_id": None,
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 400
    assert "Department must belong to exactly one parent" in resp.json()["detail"]


def test_department_archived_parent_rejected(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    program = dept_fixture["program"]
    auth_user(creator)

    # Archive the program
    archive_program(db, user=creator, program_id=program.id)

    payload = {
        "name": "Late Dept",
        "program_id": str(program.id),
        "standalone_event_id": None,
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/departments", json=payload)
    assert resp.status_code == 400
    assert "archived" in resp.json()["detail"].lower()


def test_list_and_update_departments(client: TestClient, db, dept_fixture, auth_user):
    creator = dept_fixture["creator"]
    org = dept_fixture["org"]
    program = dept_fixture["program"]
    auth_user(creator)

    # Create dept
    resp_create = client.post(
        f"/api/v1/organizations/{org.id}/departments",
        json={"name": "Sponsorship", "program_id": str(program.id)},
    )
    assert resp_create.status_code == 201
    dept_id = resp_create.json()["id"]

    # List
    resp_list = client.get(f"/api/v1/organizations/{org.id}/departments?program_id={program.id}")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # Update
    resp_patch = client.patch(
        f"/api/v1/organizations/{org.id}/departments/{dept_id}",
        json={"name": "Corporate Sponsorship & Outreach"},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["name"] == "Corporate Sponsorship & Outreach"

    # Archive
    resp_arch = client.post(f"/api/v1/organizations/{org.id}/departments/{dept_id}/archive")
    assert resp_arch.status_code == 200
    assert resp_arch.json()["status"] == "archived"

