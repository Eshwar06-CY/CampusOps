from datetime import date, datetime, timezone
import uuid
import pytest
from starlette.testclient import TestClient

from app.models.organization import OrganizationMembership
from app.models.role import RoleAssignment
from app.services.event import create_department, create_event, create_program
from app.services.organization import create_organization, verify_organization


@pytest.fixture
def task_api_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    admin = create_synthetic_platform_admin("platform_admin_tasks@internal.gov")
    creator = create_synthetic_user("creator_tasks@org.edu", "Creator Tasks")
    org = create_organization(db, creator, "Apex University", "Engineering Club")
    verify_organization(db, admin, org.id, "verified")

    worker1 = create_synthetic_user("worker1_tasks@org.edu", "Worker One")
    worker2 = create_synthetic_user("worker2_tasks@org.edu", "Worker Two")
    reviewer = create_synthetic_user("reviewer_tasks@org.edu", "Reviewer Lead")

    now = datetime.now(timezone.utc)
    mb1 = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=worker1.id,
        membership_status="active",
        joined_at=now,
    )
    mb2 = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=worker2.id,
        membership_status="active",
        joined_at=now,
    )
    mb_rev = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=reviewer.id,
        membership_status="active",
        joined_at=now,
    )
    db.add_all([mb1, mb2, mb_rev])
    db.commit()

    # Roles
    db.add_all([
        RoleAssignment(membership_id=mb1.id, role_name="COORDINATOR", scope_type="organization"),
        RoleAssignment(membership_id=mb2.id, role_name="COORDINATOR", scope_type="organization"),
        RoleAssignment(membership_id=mb_rev.id, role_name="OFFICE_BEARER", scope_type="organization"),
    ])
    db.commit()

    # Program, child event, and shared department
    prog = create_program(
        db,
        creator=creator,
        organization_id=org.id,
        name="TechFest 2026",
        planned_start_date=date(2026, 11, 1),
        planned_end_date=date(2026, 11, 10),
    )
    ev = create_event(db, creator, org.id, "Hackathon 2026", program_id=prog.id, event_date=date(2026, 11, 2))
    dept = create_department(db, creator, org.id, "Logistics Dept", program_id=prog.id)

    # Standalone Event
    standalone_ev = create_event(db, creator, org.id, "Solo Expo", event_date=date(2026, 12, 1))

    # Alien organization for cross-tenant testing
    other_creator = create_synthetic_user("other_creator@alien.edu", "Alien Creator")
    other_org = create_organization(db, other_creator, "Alien University", "Alien Club")
    verify_organization(db, admin, other_org.id, "verified")

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "worker1": worker1,
        "worker2": worker2,
        "reviewer": reviewer,
        "mb1": mb1,
        "mb2": mb2,
        "mb_rev": mb_rev,
        "prog": prog,
        "ev": ev,
        "dept": dept,
        "standalone_ev": standalone_ev,
        "other_org": other_org,
        "other_creator": other_creator,
    }


# =========================================================================
# 1. Task Creation & Retrieval
# =========================================================================

def test_create_task_authorized(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    ev = task_api_fixture["ev"]
    mb1 = task_api_fixture["mb1"]
    auth_user(creator)

    payload = {
        "title": "Setup Projector",
        "description": "Ensure HDMI connection works",
        "due_date": "2026-11-02",
        "due_time": "10:00:00",
        "timezone": "Asia/Kolkata",
        "priority": "high",
        "proof_required": True,
        "scope_type": "event",
        "scope_id": str(ev.id),
        "assignee_membership_id": str(mb1.id),
    }

    resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Setup Projector"
    assert data["priority"] == "high"
    assert data["status"] == "assigned"
    assert data["scope_type"] == "event"
    assert data["scope_id"] == str(ev.id)
    assert data["event_id"] == str(ev.id)
    assert data["due_date"] == "2026-11-02"
    assert data["due_time"] == "10:00:00"
    assert data["active_assignee"] is not None
    assert data["active_assignee"]["membership_id"] == str(mb1.id)


def test_create_task_unauthenticated_rejected(client: TestClient, task_api_fixture):
    org = task_api_fixture["org"]
    payload = {
        "title": "Unauthenticated Task",
        "due_date": "2026-11-02",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json=payload)
    assert resp.status_code == 401


def test_create_task_extra_fields_forbidden(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    payload = {
        "title": "Extra Fields Task",
        "due_date": "2026-11-02",
        "unexpected_field": "injected",
    }
    resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json=payload)
    assert resp.status_code == 422


def test_cross_tenant_task_access_denied_with_404(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    other_org = task_api_fixture["other_org"]
    other_creator = task_api_fixture["other_creator"]

    # Creator creates task in org
    auth_user(creator)
    resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks",
        json={"title": "Private Org Task", "due_date": "2026-11-05"},
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Other creator tries to access task under foreign org
    auth_user(other_creator)
    resp_get = client.get(f"/api/v1/organizations/{other_org.id}/tasks/{task_id}")
    assert resp_get.status_code == 404
    assert resp_get.json()["detail"] == "Task not found."

    # Other creator tries to access task under original org (they are not a member)
    resp_cross = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}")
    assert resp_cross.status_code == 404
    assert resp_cross.json()["detail"] == "Organization not found."


def test_list_tasks_and_filtering(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    ev = task_api_fixture["ev"]
    mb1 = task_api_fixture["mb1"]
    mb2 = task_api_fixture["mb2"]
    auth_user(creator)

    # Create 3 tasks
    client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Task 1",
        "due_date": "2026-11-01",
        "scope_type": "event",
        "scope_id": str(ev.id),
        "assignee_membership_id": str(mb1.id),
    })
    client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Task 2",
        "due_date": "2026-11-02",
        "scope_type": "event",
        "scope_id": str(ev.id),
        "assignee_membership_id": str(mb2.id),
    })
    client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Task 3 Org",
        "due_date": "2026-11-03",
        "scope_type": "organization",
    })

    # List all tasks
    resp = client.get(f"/api/v1/organizations/{org.id}/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) >= 3

    # Filter by scope_type
    resp_scope = client.get(f"/api/v1/organizations/{org.id}/tasks?scope_type=event")
    assert resp_scope.status_code == 200
    assert all(t["scope_type"] == "event" for t in resp_scope.json())

    # Filter assigned_to_me as worker1
    worker1 = task_api_fixture["worker1"]
    auth_user(worker1)
    resp_my = client.get(f"/api/v1/organizations/{org.id}/tasks?assigned_to_me=true")
    assert resp_my.status_code == 200
    my_tasks = resp_my.json()
    assert len(my_tasks) >= 1
    assert all(t["active_assignee"]["membership_id"] == str(mb1.id) for t in my_tasks)


def test_update_task_metadata(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Original Title",
        "description": "Original Desc",
        "priority": "low",
        "due_date": "2026-11-05",
    })
    task_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/organizations/{org.id}/tasks/{task_id}", json={
        "title": "Updated Title",
        "priority": "high",
    })
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "Updated Title"
    assert data["priority"] == "high"
    assert data["description"] == "Original Desc"


# =========================================================================
# 2. Assignment & Reassignment (D-SLICE4-01)
# =========================================================================

def test_assign_and_reassign_task_lifecycle(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    worker1 = task_api_fixture["worker1"]
    worker2 = task_api_fixture["worker2"]
    mb1 = task_api_fixture["mb1"]
    mb2 = task_api_fixture["mb2"]

    auth_user(creator)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Reassignment Task",
        "due_date": "2026-11-10",
        "assignee_membership_id": str(mb1.id),
    })
    task_id = create_resp.json()["id"]
    assert create_resp.json()["active_assignee"]["membership_id"] == str(mb1.id)

    # Worker 1 has view access as active assignee
    auth_user(worker1)
    view_resp1 = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}")
    assert view_resp1.status_code == 200

    # Creator reassigns task to Worker 2
    auth_user(creator)
    reassign_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/assign",
        json={"assignee_membership_id": str(mb2.id)},
    )
    assert reassign_resp.status_code == 200
    assert reassign_resp.json()["active_assignee"]["membership_id"] == str(mb2.id)

    # Worker 2 now has active access
    auth_user(worker2)
    view_resp2 = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}")
    assert view_resp2.status_code == 200

    # Worker 1 (now unassigned) loses authority to submit proof
    auth_user(worker1)
    submit_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={"evidence_urls": ["https://example.com/proof1"]},
    )
    assert submit_resp.status_code == 403


def test_assign_task_unauthorized_rejected(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    worker1 = task_api_fixture["worker1"]
    mb2 = task_api_fixture["mb2"]

    auth_user(creator)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Auth Check Task",
        "due_date": "2026-11-10",
    })
    task_id = create_resp.json()["id"]

    # Plain coordinator worker1 attempts to assign
    auth_user(worker1)
    assign_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/assign",
        json={"assignee_membership_id": str(mb2.id)},
    )
    assert assign_resp.status_code == 403


# =========================================================================
# 3. Deadlines & History
# =========================================================================

def test_change_task_deadline_audited(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Deadline Task",
        "due_date": "2026-11-10",
        "due_time": "12:00:00",
    })
    task_id = create_resp.json()["id"]

    # Change deadline
    deadline_payload = {
        "new_due_date": "2026-11-15",
        "new_due_time": "18:00:00",
        "reason": "Stage preparation delayed by rain",
    }
    dl_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/deadline",
        json=deadline_payload,
    )
    assert dl_resp.status_code == 200
    assert dl_resp.json()["due_date"] == "2026-11-15"
    assert dl_resp.json()["due_time"] == "18:00:00"

    # Verify history
    hist_resp = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert len(hist_data["deadline_history"]) == 1
    entry = hist_data["deadline_history"][0]
    assert entry["previous_due_date"] == "2026-11-10"
    assert entry["new_due_date"] == "2026-11-15"
    assert entry["reason"] == "Stage preparation delayed by rain"


def test_change_deadline_missing_reason_rejected(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "No Reason Deadline Task",
        "due_date": "2026-11-10",
    })
    task_id = create_resp.json()["id"]

    dl_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/deadline",
        json={"new_due_date": "2026-11-15", "reason": "   "},
    )
    assert dl_resp.status_code == 400


# =========================================================================
# 4. Evidence Submissions, Self-Review Prohibition & Review Workflow
# =========================================================================

def test_submission_and_review_workflow(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    worker1 = task_api_fixture["worker1"]
    reviewer = task_api_fixture["reviewer"]
    mb1 = task_api_fixture["mb1"]

    # 1. Creator creates proof-required task assigned to Worker 1
    auth_user(creator)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Mic Testing",
        "due_date": "2026-11-05",
        "proof_required": True,
        "assignee_membership_id": str(mb1.id),
    })
    task_id = create_resp.json()["id"]

    # 2. Worker 1 starts the task
    auth_user(worker1)
    start_resp = client.post(f"/api/v1/organizations/{org.id}/tasks/{task_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    # 3. Worker 1 submits evidence
    submit_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={
            "evidence_urls": ["https://drive.google.com/file/d/test12345"],
            "submitter_note": "Audio levels checked at 0dB",
        },
    )
    assert submit_resp.status_code == 201
    submission_id = submit_resp.json()["id"]
    assert submit_resp.json()["submission_number"] == 1
    assert submit_resp.json()["status"] == "pending_review"

    # Task status is now submitted_for_review
    get_task_resp = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}")
    assert get_task_resp.json()["status"] == "submitted_for_review"

    # 4. Self-Review Prohibition: Worker 1 attempts to review their own submission
    self_rev_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={"decision": "approved"},
    )
    assert self_rev_resp.status_code in (400, 403)

    # 5. Reviewer requests changes with note
    auth_user(reviewer)
    req_changes_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={
            "decision": "changes_requested",
            "review_note": "Wireless mic channel 3 has dropouts; re-test on 500MHz.",
        },
    )
    assert req_changes_resp.status_code == 200
    assert req_changes_resp.json()["decision"] == "changes_requested"

    # Task status is now changes_requested
    t_after_changes = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}").json()
    assert t_after_changes["status"] == "changes_requested"

    # 6. Worker 1 re-submits updated evidence (submission #2)
    auth_user(worker1)
    resubmit_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={
            "evidence_urls": ["https://drive.google.com/file/d/test500mhz"],
            "submitter_note": "Switched channel to 500MHz, zero dropouts.",
        },
    )
    assert resubmit_resp.status_code == 201
    submission_id_2 = resubmit_resp.json()["id"]
    assert resubmit_resp.json()["submission_number"] == 2

    # 7. Reviewer approves submission #2
    auth_user(reviewer)
    approve_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id_2}/review",
        json={"decision": "approved"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["decision"] == "approved"

    # Task is now completed
    t_completed = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}").json()
    assert t_completed["status"] == "completed"
    assert t_completed["completed_at"] is not None

    # Verify submissions list contains both versioned submissions
    subs_list_resp = client.get(f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions")
    assert subs_list_resp.status_code == 200
    submissions_list = subs_list_resp.json()
    assert len(submissions_list) == 2
    assert submissions_list[0]["submission_number"] == 1
    assert submissions_list[0]["review"]["decision"] == "changes_requested"
    assert submissions_list[1]["submission_number"] == 2
    assert submissions_list[1]["review"]["decision"] == "approved"


def test_task_cancellation_workflow(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Task to Cancel",
        "due_date": "2026-11-20",
    })
    task_id = create_resp.json()["id"]

    # Cancel task
    cancel_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/cancel",
        json={"cancellation_reason": "Event cancelled by administration."},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Cannot update cancelled task
    patch_resp = client.patch(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}",
        json={"title": "Resurrected Title"},
    )
    assert patch_resp.status_code == 400


def test_create_task_under_archived_or_unverified_scope_rejected(client: TestClient, db, task_api_fixture, auth_user, create_synthetic_user):
    # Unverified org
    unver_creator = create_synthetic_user("unver_task_creator@org.edu", "Unver Creator")
    unver_org = create_organization(db, unver_creator, "Unverified College", "Unverified Club")
    auth_user(unver_creator)
    resp = client.post(f"/api/v1/organizations/{unver_org.id}/tasks", json={
        "title": "Unver Task",
        "due_date": "2026-11-20",
    })
    assert resp.status_code == 403

    # Archived event
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    archived_ev = create_event(db, creator, org.id, "Archived Fest Event", event_date=date(2026, 12, 5))
    from app.services.event import archive_event
    archive_event(db, creator, archived_ev.id)

    auth_user(creator)
    resp_arch = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Task Under Archived Event",
        "due_date": "2026-11-20",
        "scope_type": "event",
        "scope_id": str(archived_ev.id),
    })
    assert resp_arch.status_code == 400


def test_create_task_scopes_validation(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    prog = task_api_fixture["prog"]
    dept = task_api_fixture["dept"]
    standalone_ev = task_api_fixture["standalone_ev"]
    auth_user(creator)

    # Program scope
    resp_prog = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Program Wide Task",
        "due_date": "2026-11-05",
        "scope_type": "program",
        "scope_id": str(prog.id),
    })
    assert resp_prog.status_code == 201
    assert resp_prog.json()["scope_type"] == "program"
    assert resp_prog.json()["program_id"] == str(prog.id)

    # Department scope
    resp_dept = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Dept Task",
        "due_date": "2026-11-05",
        "scope_type": "department",
        "scope_id": str(dept.id),
    })
    assert resp_dept.status_code == 201
    assert resp_dept.json()["scope_type"] == "department"
    assert resp_dept.json()["department_id"] == str(dept.id)

    # Standalone Event scope
    resp_solo = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Solo Event Task",
        "due_date": "2026-12-01",
        "scope_type": "event",
        "scope_id": str(standalone_ev.id),
    })
    assert resp_solo.status_code == 201
    assert resp_solo.json()["event_id"] == str(standalone_ev.id)
    assert resp_solo.json()["program_id"] is None


def test_create_task_invalid_deadline_or_timezone_rejected(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    auth_user(creator)

    # Missing deadline
    resp_miss = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Missing Deadline",
    })
    assert resp_miss.status_code == 422

    # Invalid timezone
    resp_tz = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Bad Timezone",
        "due_date": "2026-11-20",
        "timezone": "Invalid/FakeZone",
    })
    assert resp_tz.status_code == 400


def test_evidence_submission_validations(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    worker1 = task_api_fixture["worker1"]
    mb1 = task_api_fixture["mb1"]

    auth_user(creator)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Proof Required Task",
        "due_date": "2026-11-20",
        "proof_required": True,
        "assignee_membership_id": str(mb1.id),
    })
    task_id = create_resp.json()["id"]

    auth_user(worker1)
    client.post(f"/api/v1/organizations/{org.id}/tasks/{task_id}/start")

    # Missing evidence URL when proof_required=True
    resp_empty = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={"evidence_urls": [], "submitter_note": "No URLs provided"},
    )
    assert resp_empty.status_code == 400
    assert "proof" in resp_empty.json()["detail"].lower()

    # Invalid scheme (ftp://)
    resp_ftp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={"evidence_urls": ["ftp://fileserver/proof.pdf"]},
    )
    assert resp_ftp.status_code == 400

    # Relative path
    resp_rel = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={"evidence_urls": ["/relative/path/to/evidence"]},
    )
    assert resp_rel.status_code == 400


def test_review_validations(client: TestClient, task_api_fixture, auth_user):
    creator = task_api_fixture["creator"]
    org = task_api_fixture["org"]
    worker1 = task_api_fixture["worker1"]
    worker2 = task_api_fixture["worker2"]
    reviewer = task_api_fixture["reviewer"]
    mb1 = task_api_fixture["mb1"]

    auth_user(creator)
    create_resp = client.post(f"/api/v1/organizations/{org.id}/tasks", json={
        "title": "Review Validation Task",
        "due_date": "2026-11-20",
        "assignee_membership_id": str(mb1.id),
    })
    task_id = create_resp.json()["id"]

    auth_user(worker1)
    client.post(f"/api/v1/organizations/{org.id}/tasks/{task_id}/start")
    sub_resp = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions",
        json={"evidence_urls": ["https://drive.google.com/proof1"]},
    )
    submission_id = sub_resp.json()["id"]

    # 1. Unauthorized reviewer: worker2 is only a COORDINATOR
    auth_user(worker2)
    resp_unauth = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={"decision": "approved"},
    )
    assert resp_unauth.status_code == 403

    # 2. Reviewer requests changes without mandatory review note
    auth_user(reviewer)
    resp_no_note = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={"decision": "changes_requested", "review_note": "  "},
    )
    assert resp_no_note.status_code == 400

    # 3. Valid review approval
    resp_app = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={"decision": "approved"},
    )
    assert resp_app.status_code == 200

    # 4. Duplicate review attempt on already reviewed submission
    resp_dup = client.post(
        f"/api/v1/organizations/{org.id}/tasks/{task_id}/submissions/{submission_id}/review",
        json={"decision": "approved"},
    )
    assert resp_dup.status_code == 400

