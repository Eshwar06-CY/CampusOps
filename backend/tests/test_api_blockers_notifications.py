from datetime import date, datetime, timezone
import uuid
import pytest
from starlette.testclient import TestClient

from app.models.organization import OrganizationMembership
from app.models.role import RoleAssignment
from app.services.event import create_event
from app.services.organization import create_organization, verify_organization


@pytest.fixture
def blocker_notif_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin_blockers@internal.gov")
    creator = create_synthetic_user("creator_blockers@org.edu", "Creator Blockers")
    org = create_organization(db, creator, "Apex Institute", "Robotics Club")
    verify_organization(db, admin, org.id, "verified")

    staff_lead = create_synthetic_user("lead_blockers@org.edu", "Staff Lead")
    worker = create_synthetic_user("worker_blockers@org.edu", "Worker Member")
    other_user = create_synthetic_user("other_blockers@org.edu", "Other User")

    now = datetime.now(timezone.utc)
    mb_lead = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=staff_lead.id,
        membership_status="active",
        joined_at=now,
    )
    mb_worker = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=worker.id,
        membership_status="active",
        joined_at=now,
    )
    db.add_all([mb_lead, mb_worker])
    db.commit()

    db.add_all([
        RoleAssignment(membership_id=mb_lead.id, role_name="OFFICE_BEARER", scope_type="organization"),
        RoleAssignment(membership_id=mb_worker.id, role_name="COORDINATOR", scope_type="organization"),
    ])
    db.commit()

    ev = create_event(db, creator, org.id, "RoboWars 2026", event_date=date(2026, 11, 15))

    # Foreign organization
    foreign_creator = create_synthetic_user("foreign@other.edu", "Foreign Creator")
    foreign_org = create_organization(db, foreign_creator, "Foreign Institute", "Foreign Club")
    verify_organization(db, admin, foreign_org.id, "verified")

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "staff_lead": staff_lead,
        "worker": worker,
        "other_user": other_user,
        "mb_lead": mb_lead,
        "mb_worker": mb_worker,
        "ev": ev,
        "foreign_org": foreign_org,
        "foreign_creator": foreign_creator,
    }


# =========================================================================
# 1. Operational Blockers
# =========================================================================

def test_create_and_resolve_blocker_lifecycle(client: TestClient, blocker_notif_fixture, auth_user):
    staff_lead = blocker_notif_fixture["staff_lead"]
    org = blocker_notif_fixture["org"]
    ev = blocker_notif_fixture["ev"]
    mb_lead = blocker_notif_fixture["mb_lead"]

    auth_user(staff_lead)

    # 1. Create operational blocker
    payload = {
        "title": "Power Cut in Main Arena",
        "description": "Main circuit breaker tripped; waiting for campus electrician.",
        "scope_type": "event",
        "scope_id": str(ev.id),
        "priority": "critical",
        "owner_membership_id": str(mb_lead.id),
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/blockers", json=payload)
    assert resp.status_code == 201
    blocker_id = resp.json()["id"]
    assert resp.json()["title"] == "Power Cut in Main Arena"
    assert resp.json()["status"] == "open"
    assert resp.json()["priority"] == "critical"

    # 2. Retrieve blocker detail with history
    detail_resp = client.get(f"/api/v1/organizations/{org.id}/blockers/{blocker_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == blocker_id
    assert len(detail_resp.json()["history"]) == 1
    assert detail_resp.json()["history"][0]["new_status"] == "open"

    # 3. Update blocker metadata
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}",
        json={"priority": "high", "description": "Electrician arrived, working on breaker."},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["priority"] == "high"

    # 4. Resolve blocker
    resolve_resp = client.post(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}/resolve",
        json={"resolution_note": "Replaced fuse; main circuit restored."},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"
    assert resolve_resp.json()["resolution_note"] == "Replaced fuse; main circuit restored."

    # Cannot resolve already resolved blocker
    res_again = client.post(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}/resolve",
        json={"resolution_note": "Duplicate resolution attempt."},
    )
    assert res_again.status_code == 400

    # 5. Reopen blocker
    reopen_resp = client.post(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}/reopen",
        json={"reason": "Fuse tripped again when arena lights switched on."},
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "open"

    # Cannot reopen already open blocker
    reopen_again = client.post(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}/reopen",
        json={"reason": "Redundant reopen attempt."},
    )
    assert reopen_again.status_code == 400

    # 6. Verify detail history contains resolution and reopening entries
    final_detail = client.get(f"/api/v1/organizations/{org.id}/blockers/{blocker_id}").json()
    assert len(final_detail["history"]) >= 2


def test_list_blockers_and_scoping(client: TestClient, blocker_notif_fixture, auth_user):
    staff_lead = blocker_notif_fixture["staff_lead"]
    org = blocker_notif_fixture["org"]
    ev = blocker_notif_fixture["ev"]
    auth_user(staff_lead)

    client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Blocker 1",
        "description": "Desc 1",
        "scope_type": "event",
        "scope_id": str(ev.id),
        "priority": "medium",
    })
    client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Blocker 2 Org",
        "description": "Desc 2",
        "scope_type": "organization",
        "priority": "high",
    })

    resp = client.get(f"/api/v1/organizations/{org.id}/blockers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_cross_tenant_blocker_access_denied(client: TestClient, blocker_notif_fixture, auth_user):
    staff_lead = blocker_notif_fixture["staff_lead"]
    foreign_creator = blocker_notif_fixture["foreign_creator"]
    org = blocker_notif_fixture["org"]
    foreign_org = blocker_notif_fixture["foreign_org"]

    auth_user(staff_lead)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Private Blocker",
        "description": "Secret Issue",
        "scope_type": "organization",
    })
    blocker_id = create_resp.json()["id"]

    # Foreign actor accessing under foreign org
    auth_user(foreign_creator)
    resp_foreign = client.get(f"/api/v1/organizations/{foreign_org.id}/blockers/{blocker_id}")
    assert resp_foreign.status_code == 404
    assert resp_foreign.json()["detail"] == "Blocker not found."


# =========================================================================
# 2. In-App Notifications
# =========================================================================

def test_notifications_workflow(client: TestClient, blocker_notif_fixture, auth_user):
    creator = blocker_notif_fixture["creator"]
    worker = blocker_notif_fixture["worker"]
    other_user = blocker_notif_fixture["other_user"]
    org = blocker_notif_fixture["org"]
    mb_worker = blocker_notif_fixture["mb_worker"]

    # 1. Creator assigns task to worker, generating a notification for worker
    auth_user(creator)
    task_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Notified Task",
        "due_date": "2026-11-20",
        "assignee_membership_id": str(mb_worker.id),
    })
    assert task_resp.status_code == 201

    # 2. Worker retrieves their notifications
    auth_user(worker)
    notif_resp = client.get("/api/v1/notifications")
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()
    assert len(notifs) >= 1
    target_notif = next((n for n in notifs if "Notified Task" in n["title"] or "Notified Task" in n["message"]), None)
    assert target_notif is not None
    assert target_notif["is_read"] is False

    notif_id = target_notif["id"]

    # 3. Worker reads single notification
    single_resp = client.get(f"/api/v1/notifications/{notif_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["id"] == notif_id

    # 4. Other user cannot read worker's notification
    auth_user(other_user)
    other_read_resp = client.get(f"/api/v1/notifications/{notif_id}")
    assert other_read_resp.status_code == 404

    other_mark_resp = client.post(f"/api/v1/notifications/{notif_id}/read")
    assert other_mark_resp.status_code == 404

    # 5. Worker marks notification as read
    auth_user(worker)
    mark_resp = client.post(f"/api/v1/notifications/{notif_id}/read")
    assert mark_resp.status_code == 200
    assert mark_resp.json()["is_read"] is True
    assert mark_resp.json()["read_at"] is not None

    # Filter unread_only should now exclude this notification
    unread_resp = client.get("/api/v1/notifications?unread_only=true")
    assert unread_resp.status_code == 200
    assert not any(n["id"] == notif_id for n in unread_resp.json())


def test_blocker_validation_and_unauthorized_rejection(client: TestClient, blocker_notif_fixture, auth_user):
    other_user = blocker_notif_fixture["other_user"]
    staff_lead = blocker_notif_fixture["staff_lead"]
    org = blocker_notif_fixture["org"]

    # 1. Non-member / unauthorized user rejected with 404 (non-disclosure)
    auth_user(other_user)
    resp_unauth = client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Unauthorized Blocker",
        "description": "Should fail",
    })
    assert resp_unauth.status_code == 404

    # 2. Staff lead: empty title rejected with 422
    auth_user(staff_lead)
    resp_empty_title = client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "",
        "description": "Some description",
    })
    assert resp_empty_title.status_code == 422

    # 3. Blocker creation with extra fields rejected with 422
    resp_extra = client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Extra field blocker",
        "description": "Some description",
        "injected": "malicious",
    })
    assert resp_extra.status_code == 422

    # 4. Resolve with empty note rejected with 422 (min_length=1)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/blockers", json={
        "title": "Resolve Check Blocker",
        "description": "Some description",
    })
    blocker_id = create_resp.json()["id"]

    resp_bad_res = client.post(
        f"/api/v1/organizations/{org.id}/blockers/{blocker_id}/resolve",
        json={"resolution_note": ""},
    )
    assert resp_bad_res.status_code == 422

