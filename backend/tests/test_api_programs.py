import uuid
from datetime import date
import pytest
from starlette.testclient import TestClient

from app.services.organization import create_organization, verify_organization


@pytest.fixture
def org_setup(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin@internal.gov")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Apex University", club_name="Tech Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")
    return {"admin": admin, "creator": creator, "org": org}


def test_create_program_authorized(client: TestClient, db, org_setup, auth_user):
    creator = org_setup["creator"]
    org = org_setup["org"]
    auth_user(creator)

    payload = {
        "name": "E-Week 2027",
        "description": "Annual Entrepreneurship Week",
        "planned_start_date": "2027-02-10",
        "planned_end_date": "2027-02-15",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "E-Week 2027"
    assert data["status"] == "draft"
    assert data["organization_id"] == str(org.id)
    assert data["planned_start_date"] == "2027-02-10"
    assert data["planned_end_date"] == "2027-02-15"


def test_create_program_unauthorized(client: TestClient, db, org_setup, create_synthetic_user, auth_user):
    org = org_setup["org"]
    outsider = create_synthetic_user("outsider@other.edu", "Outsider")
    auth_user(outsider)

    payload = {"name": "Hacked Program"}
    resp = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp.status_code == 404  # non-disclosing 404 for non-members


def test_create_program_in_pending_verification_org_rejected(client: TestClient, db, create_synthetic_user, auth_user):
    creator = create_synthetic_user("pending_creator@org.edu", "Pending Creator")
    pending_org = create_organization(db, creator=creator, college_name="Pending College", club_name="Pending Club")
    auth_user(creator)

    payload = {"name": "Early Program"}
    resp = client.post(f"/api/v1/organizations/{pending_org.id}/programs", json=payload)
    assert resp.status_code == 403


def test_create_program_duplicate_name_rejected(client: TestClient, db, org_setup, auth_user):
    creator = org_setup["creator"]
    org = org_setup["org"]
    auth_user(creator)

    payload = {"name": "Robotics Fair"}
    resp1 = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp2.status_code == 400
    assert "already exists in this organization" in resp2.json()["detail"]


def test_create_program_invalid_dates_rejected(client: TestClient, db, org_setup, auth_user):
    creator = org_setup["creator"]
    org = org_setup["org"]
    auth_user(creator)

    payload = {
        "name": "Time Machine Program",
        "planned_start_date": "2027-02-20",
        "planned_end_date": "2027-02-10",  # earlier than start
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp.status_code == 400
    assert "Planned end date cannot be earlier" in resp.json()["detail"]


def test_create_program_extra_fields_forbidden(client: TestClient, db, org_setup, auth_user):
    creator = org_setup["creator"]
    org = org_setup["org"]
    auth_user(creator)

    payload = {
        "name": "Injected Program",
        "is_admin": True,  # extra field
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/programs", json=payload)
    assert resp.status_code == 422


def test_list_and_get_programs_tenant_isolation(
    client: TestClient, db, org_setup, create_synthetic_user, auth_user
):
    creator = org_setup["creator"]
    org1 = org_setup["org"]
    auth_user(creator)

    # Create program in Org 1
    resp = client.post(f"/api/v1/organizations/{org1.id}/programs", json={"name": "Org1 Program"})
    assert resp.status_code == 201
    prog_id = resp.json()["id"]

    # Other user in Org 2
    user2 = create_synthetic_user("user2@org2.edu", "Org2 User")
    org2 = create_organization(db, creator=user2, college_name="College 2", club_name="Club 2")
    auth_user(user2)

    # User 2 listing Org 1 programs -> 404
    resp_list = client.get(f"/api/v1/organizations/{org1.id}/programs")
    assert resp_list.status_code == 404

    # User 2 getting Org 1 program -> 404
    resp_get = client.get(f"/api/v1/organizations/{org1.id}/programs/{prog_id}")
    assert resp_get.status_code == 404


def test_update_and_archive_program_lifecycle(client: TestClient, db, org_setup, auth_user):
    creator = org_setup["creator"]
    org = org_setup["org"]
    auth_user(creator)

    # 1. Create
    resp = client.post(
        f"/api/v1/organizations/{org.id}/programs",
        json={"name": "Original Name", "planned_start_date": "2027-03-01", "planned_end_date": "2027-03-10"},
    )
    assert resp.status_code == 201
    prog_id = resp.json()["id"]

    # 2. Update
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/programs/{prog_id}",
        json={"name": "Updated Name", "description": "New description"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated Name"
    assert patch_resp.json()["description"] == "New description"

    # 3. Archive
    arch_resp = client.post(f"/api/v1/organizations/{org.id}/programs/{prog_id}/archive")
    assert arch_resp.status_code == 200
    assert arch_resp.json()["status"] == "archived"
    assert arch_resp.json()["archived_at"] is not None

    # 4. Archived program no longer accessible via active get
    get_resp = client.get(f"/api/v1/organizations/{org.id}/programs/{prog_id}")
    assert get_resp.status_code == 404

