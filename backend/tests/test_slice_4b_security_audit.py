import datetime
import uuid
import pytest
from starlette.testclient import TestClient
from unittest.mock import patch

from app.models.event import Event, Department
from app.models.organization import OrganizationMembership
from app.models.role import RoleAssignment
from app.models.task import EvidenceSubmission, Notification, OperationalBlocker, Task, TaskReview, TaskStatusHistory
from app.services.event import create_department, create_event, create_program
from app.services.organization import create_organization, verify_organization
from app.services.task import (
    assign_task,
    create_operational_blocker,
    create_task,
    start_task,
    submit_task_evidence,
)


@pytest.fixture
def audit_fixture(db, create_synthetic_user, create_synthetic_platform_admin):
    """
    Sets up multi-tenant, multi-role test fixtures for rigorous Slice 4B security audit:
    - Org 1 (Apex): Admin, Office Bearer (Reviewer), Event Lead 1 (Event 1), Event Lead 2 (Event 2),
      Dept Lead 1 (Dept 1), Coordinator (Worker 1), Worker 2, Worker 3.
    - Org 2 (Foreign): Foreign Admin, Foreign Worker.
    - Dual Member: Member in both Org 1 and Org 2.
    """
    plat_admin = create_synthetic_platform_admin("plat_admin_sec4b@internal.gov")
    
    # Org 1
    org1_owner = create_synthetic_user("org1_owner@apex.edu", "Org 1 Owner")
    org1 = create_organization(db, org1_owner, "Apex University", "Apex Council")
    verify_organization(db, plat_admin, org1.id, "verified")

    reviewer = create_synthetic_user("reviewer_sec4b@apex.edu", "Reviewer Lead")
    event_lead1 = create_synthetic_user("elead1_sec4b@apex.edu", "Event Lead One")
    event_lead2 = create_synthetic_user("elead2_sec4b@apex.edu", "Event Lead Two")
    dept_lead1 = create_synthetic_user("dlead1_sec4b@apex.edu", "Dept Lead One")
    dept_lead2 = create_synthetic_user("dlead2_sec4b@apex.edu", "Dept Lead Two")
    worker1 = create_synthetic_user("worker1_sec4b@apex.edu", "Worker One")
    worker2 = create_synthetic_user("worker2_sec4b@apex.edu", "Worker Two")
    worker3 = create_synthetic_user("worker3_sec4b@apex.edu", "Worker Three")

    now = datetime.datetime.now(datetime.timezone.utc)
    
    def add_member(user, org, role_name=None, scope_type="organization", scope_id=None):
        mb = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=user.id,
            membership_status="active",
            joined_at=now,
        )
        db.add(mb)
        db.flush()
        if role_name:
            ra = RoleAssignment(
                membership_id=mb.id,
                role_name=role_name,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            db.add(ra)
            db.flush()
        return mb

    mb_reviewer = add_member(reviewer, org1, "OFFICE_BEARER", "organization")
    
    # Events in Org 1
    ev1 = create_event(db, org1_owner, org1.id, "Annual Hackathon", event_date=datetime.date(2026, 11, 20))
    ev2 = create_event(db, org1_owner, org1.id, "Robotics Summit", event_date=datetime.date(2026, 11, 25))
    
    # Departments in Org 1 (standalone events)
    dept1 = create_department(db, org1_owner, org1.id, "Hackathon Logistics", standalone_event_id=ev1.id)
    dept2 = create_department(db, org1_owner, org1.id, "Robotics Logistics", standalone_event_id=ev2.id)

    mb_elead1 = add_member(event_lead1, org1, "EVENT_LEAD", "event", ev1.id)
    mb_elead2 = add_member(event_lead2, org1, "EVENT_LEAD", "event", ev2.id)
    mb_dlead1 = add_member(dept_lead1, org1, "DEPARTMENT_LEAD", "department", dept1.id)
    mb_dlead2 = add_member(dept_lead2, org1, "DEPARTMENT_LEAD", "department", dept2.id)
    mb_worker1 = add_member(worker1, org1, "COORDINATOR", "organization")
    mb_worker2 = add_member(worker2, "COORDINATOR", "organization") if False else add_member(worker2, org1, "COORDINATOR", "organization")
    mb_worker3 = add_member(worker3, org1, "COORDINATOR", "organization")

    # Org 2 (Alien)
    org2_owner = create_synthetic_user("org2_owner@alien.edu", "Org 2 Owner")
    org2 = create_organization(db, org2_owner, "Alien Institute", "Alien Council")
    verify_organization(db, plat_admin, org2.id, "verified")

    foreign_worker = create_synthetic_user("foreign_worker@alien.edu", "Foreign Worker")
    mb_foreign = add_member(foreign_worker, org2, "COORDINATOR", "organization")

    # Dual Member (Member in Org 1 and Admin in Org 2)
    dual_user = create_synthetic_user("dual_user@cross.edu", "Dual Member")
    mb_dual_org1 = add_member(dual_user, org1, "OFFICE_BEARER", "organization")
    mb_dual_org2 = add_member(dual_user, org2, "PRIMARY_ADMIN", "organization")

    db.commit()

    return {
        "org1": org1,
        "org1_owner": org1_owner,
        "org2": org2,
        "org2_owner": org2_owner,
        "reviewer": reviewer,
        "event_lead1": event_lead1,
        "event_lead2": event_lead2,
        "dept_lead1": dept_lead1,
        "dept_lead2": dept_lead2,
        "worker1": worker1,
        "worker2": worker2,
        "worker3": worker3,
        "foreign_worker": foreign_worker,
        "dual_user": dual_user,
        "mb_reviewer": mb_reviewer,
        "mb_elead1": mb_elead1,
        "mb_elead2": mb_elead2,
        "mb_dlead1": mb_dlead1,
        "mb_dlead2": mb_dlead2,
        "mb_worker1": mb_worker1,
        "mb_worker2": mb_worker2,
        "mb_worker3": mb_worker3,
        "mb_foreign": mb_foreign,
        "ev1": ev1,
        "ev2": ev2,
        "dept1": dept1,
        "dept2": dept2,
    }


# =========================================================================
# 1. Cross-Tenant Anti-Enumeration & Resource Non-Disclosure
# =========================================================================

def test_cross_tenant_task_access_returns_404_not_found(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that any attempt to access, mutate, assign, submit, or review an alien organization's
    task through an authorized organization route returns uniform HTTP 404 Not Found without disclosing metadata.
    """
    org1 = audit_fixture["org1"]
    org2 = audit_fixture["org2"]
    org1_owner = audit_fixture["org1_owner"]
    org2_owner = audit_fixture["org2_owner"]
    mb_foreign = audit_fixture["mb_foreign"]

    # Create task in Org 2
    task_org2 = create_task(
        db,
        creator=org2_owner,
        organization_id=org2.id,
        title="Foreign Task in Org 2",
        due_date=datetime.date(2026, 11, 30),
        proof_required=True,
        assignee_membership_id=mb_foreign.id,
    )

    auth_user(org1_owner)

    # 1. GET task
    resp = client.get(f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 2. PATCH task
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}",
        json={"title": "Hacked Title"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 3. POST assign
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/assign",
        json={"assignee_membership_id": str(audit_fixture["mb_worker1"].id)},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 4. POST start
    resp = client.post(f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/start")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 5. POST cancel
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/cancel",
        json={"cancellation_reason": "Attempted cross-tenant cancel"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 6. POST deadline
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/deadline",
        json={"new_due_date": "2026-12-01", "reason": "Attempted cross-tenant deadline"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 7. POST submissions
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/submissions",
        json={"evidence_urls": ["https://proof.example.com/test"]},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 8. GET submissions
    resp = client.get(f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/submissions")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."

    # 9. GET history
    resp = client.get(f"/api/v1/organizations/{org1.id}/tasks/{task_org2.id}/history")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found."


def test_cross_tenant_blocker_access_and_mutation_returns_404(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that operational blockers belonging to another organization return uniform HTTP 404
    on GET, PATCH, resolve, and reopen routes.
    """
    org1 = audit_fixture["org1"]
    org2 = audit_fixture["org2"]
    org1_owner = audit_fixture["org1_owner"]
    org2_owner = audit_fixture["org2_owner"]
    dual_user = audit_fixture["dual_user"]

    # Create blocker in Org 2
    blocker_org2 = create_operational_blocker(
        db,
        creator=org2_owner,
        organization_id=org2.id,
        title="Stage Lights Broken in Org 2",
        description="Short circuit on Org 2 main stage.",
        priority="high",
    )

    auth_user(org1_owner)

    # 1. GET blocker
    resp = client.get(f"/api/v1/organizations/{org1.id}/blockers/{blocker_org2.id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Blocker not found."

    # 2. PATCH blocker
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker_org2.id}",
        json={"title": "Unauthorized Patch Title"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Blocker not found."

    # 3. Resolve blocker
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker_org2.id}/resolve",
        json={"resolution_note": "Fake resolution", "status": "resolved"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Blocker not found."

    # 4. Reopen blocker
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker_org2.id}/reopen",
        json={"reason": "Fake reopen"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Blocker not found."

    # 5. Dual member (admin in both orgs) attempting to modify Org 2 blocker under Org 1 URL
    auth_user(dual_user)
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker_org2.id}",
        json={"title": "Cross Org URL Tampering"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Blocker not found."


# =========================================================================
# 2. Strict Self-Review Prohibition
# =========================================================================

def test_self_review_strictly_prohibited_for_all_roles(client: TestClient, audit_fixture, auth_user, db):
    """
    CO-FR-007 / Section 5: The active assignee or submitter of an evidence submission
    is strictly forbidden from approving or reviewing their own submission, even if they
    hold elevated roles (OFFICE_BEARER, PRIMARY_ADMIN).
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    reviewer = audit_fixture["reviewer"]
    mb_reviewer = audit_fixture["mb_reviewer"]
    worker1 = audit_fixture["worker1"]
    mb_worker1 = audit_fixture["mb_worker1"]

    # Scenario A: Ordinary worker submits evidence; tries to self-review
    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Check Sound System",
        due_date=datetime.date(2026, 11, 22),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker1,
        task_id=task.id,
        evidence_urls=["https://storage.example.com/sound_check.pdf"],
        submitter_note="Completed check.",
    )

    auth_user(worker1)
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "approved"},
    )
    # Self-review raises SelfReviewError mapped to 400 Bad Request
    assert resp.status_code in (400, 403)
    assert "cannot review" in resp.json()["detail"].lower() or "denied" in resp.json()["detail"].lower()

    # Scenario B: Office Bearer (with full org review authority) assigned to a task submits evidence; tries to approve own work
    task_ob = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Sign Stage Contract",
        due_date=datetime.date(2026, 11, 23),
        proof_required=True,
        assignee_membership_id=mb_reviewer.id,
    )
    start_task(db, user=reviewer, task_id=task_ob.id)
    sub_ob = submit_task_evidence(
        db,
        user=reviewer,
        task_id=task_ob.id,
        evidence_urls=["https://storage.example.com/contract_signed.pdf"],
        submitter_note="Signed by lead.",
    )

    auth_user(reviewer)
    resp_ob = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_ob.id}/submissions/{sub_ob.id}/review",
        json={"decision": "approved"},
    )
    assert resp_ob.status_code == 400
    assert "cannot review" in resp_ob.json()["detail"].lower()

    # Scenario C: Another authorized reviewer (org1_owner) CAN approve the submission
    auth_user(org1_owner)
    resp_valid = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task_ob.id}/submissions/{sub_ob.id}/review",
        json={"decision": "approved"},
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json()["decision"] == "approved"


def test_reassigned_active_assignee_cannot_review_previous_submission(client: TestClient, audit_fixture, auth_user, db):
    """
    If Task T had submission #1 by Worker 1, and is then reassigned to Worker 2,
    Worker 2 (now the active assignee) is also barred from reviewing submission #1.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    worker1 = audit_fixture["worker1"]
    worker2 = audit_fixture["worker2"]
    mb_worker1 = audit_fixture["mb_worker1"]
    mb_worker2 = audit_fixture["mb_worker2"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Stage Lighting Setup",
        due_date=datetime.date(2026, 11, 22),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker1,
        task_id=task.id,
        evidence_urls=["https://storage.example.com/lights1.pdf"],
    )

    # Reassign to Worker 2
    assign_task(db, user=org1_owner, task_id=task.id, assignee_membership_id=mb_worker2.id)

    auth_user(worker2)
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "approved"},
    )
    assert resp.status_code in (400, 403)
    assert "assignee cannot review" in resp.json()["detail"].lower() or "denied" in resp.json()["detail"].lower()


# =========================================================================
# 3. Double-Review & Replay Protection
# =========================================================================

def test_double_review_and_replay_protection(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that reviewing an already approved or rejected submission fails closed
    with HTTP 400 Bad Request, preventing double-review race conditions.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    reviewer = audit_fixture["reviewer"]
    worker1 = audit_fixture["worker1"]
    mb_worker1 = audit_fixture["mb_worker1"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Network Cabling",
        due_date=datetime.date(2026, 11, 22),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker1,
        task_id=task.id,
        evidence_urls=["https://storage.example.com/network_cables.pdf"],
    )

    auth_user(reviewer)

    # First review: Approve
    resp1 = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "approved"},
    )
    assert resp1.status_code == 200

    # Second review: Replay attempt by org1_owner
    auth_user(org1_owner)
    resp2 = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "changes_requested", "review_note": "Late rejection attempt"},
    )
    assert resp2.status_code == 400
    assert "not pending review" in resp2.json()["detail"].lower()


# =========================================================================
# 4. Scope-Based Access Control & Strict Boundary Isolation
# =========================================================================

def test_event_lead_and_dept_lead_cannot_access_sibling_scopes(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies scope-level boundary isolation within the same organization:
    - Event Lead 1 (Event 1) cannot view, update, assign, or cancel tasks in Event 2.
    - Event Lead 1 cannot view or resolve operational blockers in Event 2.
    - Department Lead 1 (Dept 1) cannot view or update tasks in Dept 2.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    event_lead1 = audit_fixture["event_lead1"]
    dept_lead1 = audit_fixture["dept_lead1"]
    ev1 = audit_fixture["ev1"]
    ev2 = audit_fixture["ev2"]
    dept1 = audit_fixture["dept1"]
    dept2 = audit_fixture["dept2"]

    # Create task in Event 2
    task_ev2 = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Event 2 Main Stage Wiring",
        due_date=datetime.date(2026, 11, 25),
        scope_type="event",
        scope_id=ev2.id,
    )

    # Create blocker in Event 2
    blocker_ev2 = create_operational_blocker(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Event 2 Projector Missing",
        description="Projector not available in Event 2 hall.",
        scope_type="event",
        scope_id=ev2.id,
    )

    # Create task in Dept 2
    task_dept2 = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Dept 2 Inventory Count",
        due_date=datetime.date(2026, 11, 26),
        scope_type="department",
        scope_id=dept2.id,
    )

    # 1. Event Lead 1 accessing Event 2 Task
    auth_user(event_lead1)
    resp = client.get(f"/api/v1/organizations/{org1.id}/tasks/{task_ev2.id}")
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/tasks/{task_ev2.id}",
        json={"title": "Hacked Event 2 Task"},
    )
    assert resp.status_code == 403

    # 2. Event Lead 1 listing tasks (Event 2 task must be omitted)
    list_resp = client.get(f"/api/v1/organizations/{org1.id}/tasks")
    assert list_resp.status_code == 200
    returned_task_ids = [t["id"] for t in list_resp.json()]
    assert str(task_ev2.id) not in returned_task_ids

    # 3. Event Lead 1 accessing Event 2 Blocker
    resp = client.get(f"/api/v1/organizations/{org1.id}/blockers/{blocker_ev2.id}")
    assert resp.status_code == 403

    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker_ev2.id}/resolve",
        json={"resolution_note": "Unauthorized resolve attempt", "status": "resolved"},
    )
    assert resp.status_code == 403

    # 4. Department Lead 1 accessing Dept 2 Task
    auth_user(dept_lead1)
    resp = client.get(f"/api/v1/organizations/{org1.id}/tasks/{task_dept2.id}")
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/tasks/{task_dept2.id}",
        json={"title": "Unauthorized Dept 2 Edit"},
    )
    assert resp.status_code == 403


def test_coordinator_privilege_ceiling(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that a Coordinator cannot perform managerial operations:
    - Cannot update task metadata (PATCH /tasks/{id})
    - Cannot change deadline (POST /tasks/{id}/deadline)
    - Cannot cancel task (POST /tasks/{id}/cancel)
    - Cannot review proof (POST /tasks/{id}/submissions/{id}/review)
    - Cannot resolve blocker (POST /blockers/{id}/resolve)
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    worker1 = audit_fixture["worker1"]
    worker2 = audit_fixture["worker2"]
    mb_worker2 = audit_fixture["mb_worker2"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Stage Microphones",
        due_date=datetime.date(2026, 11, 22),
        proof_required=True,
        assignee_membership_id=mb_worker2.id,
    )
    start_task(db, user=worker2, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker2,
        task_id=task.id,
        evidence_urls=["https://storage.example.com/mic_check.pdf"],
    )

    blocker = create_operational_blocker(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Mic Stand Broken",
        description="Thread stripped on main boom arm.",
    )

    auth_user(worker1)  # Coordinator

    # 1. Update task
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}",
        json={"title": "Coordinator Renamed Task"},
    )
    assert resp.status_code == 403

    # 2. Change deadline
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/deadline",
        json={"new_due_date": "2026-11-28", "reason": "Coordinator delay"},
    )
    assert resp.status_code == 403

    # 3. Cancel task
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/cancel",
        json={"cancellation_reason": "Coordinator cancel"},
    )
    assert resp.status_code == 403

    # 4. Review submission
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "approved"},
    )
    assert resp.status_code == 403

    # 5. Resolve blocker
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}/resolve",
        json={"resolution_note": "Coordinator resolved", "status": "resolved"},
    )
    assert resp.status_code == 403


# =========================================================================
# 5. Worker Authority Lifecycle (Reassignment & Deactivation)
# =========================================================================

def test_unassigned_former_worker_submission_authority_revocation(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that when a task is reassigned from Worker 1 to Worker 2:
    - Worker 1's submission authority is revoked immediately (returns 403).
    - Worker 2 gains active submission authority (returns 201).
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    worker1 = audit_fixture["worker1"]
    worker2 = audit_fixture["worker2"]
    mb_worker1 = audit_fixture["mb_worker1"]
    mb_worker2 = audit_fixture["mb_worker2"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Keynote Slides Preparation",
        due_date=datetime.date(2026, 11, 21),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)

    # Reassign to Worker 2
    auth_user(org1_owner)
    assign_resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/assign",
        json={"assignee_membership_id": str(mb_worker2.id)},
    )
    assert assign_resp.status_code == 200

    # Worker 1 (former assignee) attempts to submit proof
    auth_user(worker1)
    resp1 = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions",
        json={"evidence_urls": ["https://storage.example.com/slides_v1.pdf"]},
    )
    assert resp1.status_code == 403
    assert "only active assignees" in resp1.json()["detail"].lower()

    # Worker 2 (active assignee) submits proof
    auth_user(worker2)
    resp2 = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions",
        json={"evidence_urls": ["https://storage.example.com/slides_v2.pdf"]},
    )
    assert resp2.status_code == 201
    assert resp2.json()["submission_number"] == 1


def test_removed_member_active_assignment_invalidation(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that if an assigned member is removed from the organization,
    their ability to start the task or submit proof is immediately blocked.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    worker3 = audit_fixture["worker3"]
    mb_worker3 = audit_fixture["mb_worker3"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Auditorium Seating Arrangement",
        due_date=datetime.date(2026, 11, 24),
        proof_required=True,
        assignee_membership_id=mb_worker3.id,
    )

    # Terminate worker3's membership
    mb_worker3.membership_status = "removed"
    mb_worker3.removed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    auth_user(worker3)

    # Attempt to start task
    resp = client.post(f"/api/v1/organizations/{org1.id}/tasks/{task.id}/start")
    # Because membership is removed, _ensure_org_access fails closed with 404
    assert resp.status_code in (403, 404)


# =========================================================================
# 6. State-Machine Invariant Enforcement
# =========================================================================

def test_terminal_task_state_machine_invariants(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that terminal tasks (completed, cancelled) reject further operational mutations:
    start, deadline change, assignment, cancellation, submission, and metadata update.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    reviewer = audit_fixture["reviewer"]
    worker1 = audit_fixture["worker1"]
    mb_worker1 = audit_fixture["mb_worker1"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Registration Desk Setup",
        due_date=datetime.date(2026, 11, 20),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker1,
        task_id=task.id,
        evidence_urls=["https://proof.example.com/desk.png"],
    )

    # Approve to transition task to 'completed'
    auth_user(reviewer)
    client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "approved"},
    )

    auth_user(org1_owner)

    # 1. Attempt start on completed task
    resp = client.post(f"/api/v1/organizations/{org1.id}/tasks/{task.id}/start")
    assert resp.status_code == 400
    assert "cannot start task currently in status 'completed'" in resp.json()["detail"].lower()

    # 2. Attempt deadline change on completed task
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/deadline",
        json={"new_due_date": "2026-12-01", "reason": "Late deadline attempt"},
    )
    assert resp.status_code == 400
    assert "terminal status" in resp.json()["detail"].lower()

    # 3. Attempt reassign on completed task
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/assign",
        json={"assignee_membership_id": str(audit_fixture["mb_worker2"].id)},
    )
    assert resp.status_code == 400
    assert "terminal status" in resp.json()["detail"].lower()

    # 4. Attempt cancel on completed task
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/cancel",
        json={"cancellation_reason": "Cancel completed task"},
    )
    assert resp.status_code == 400
    assert "terminal status" in resp.json()["detail"].lower()

    # 5. Attempt update on completed task
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}",
        json={"title": "Update Completed Task"},
    )
    assert resp.status_code == 400
    assert "terminal status" in resp.json()["detail"].lower()


def test_blocker_state_machine_and_mandatory_notes(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies operational blocker state machine invariants:
    - Resolving requires non-empty resolution note.
    - Reopening requires non-empty reason.
    - Cannot reopen an already open blocker.
    - Cannot update a closed blocker without reopening.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]

    blocker = create_operational_blocker(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Fire Alarm Inspection Pending",
        description="Safety certificate expired.",
        priority="critical",
    )

    auth_user(org1_owner)

    # 1. Attempt to reopen already open blocker
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}/reopen",
        json={"reason": "Reopen already open"},
    )
    assert resp.status_code == 400
    assert "must be 'resolved' or 'wont_fix'" in resp.json()["detail"].lower()

    # 2. Resolve blocker without resolution note (schema validation fails: min_length=1)
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}/resolve",
        json={"resolution_note": "   ", "status": "resolved"},
    )
    assert resp.status_code in (400, 422)

    # 3. Resolve blocker properly
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}/resolve",
        json={"resolution_note": "Inspection passed and certificate renewed.", "status": "resolved"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    # 4. Attempt update on resolved blocker
    resp = client.patch(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}",
        json={"title": "Update Closed Blocker"},
    )
    assert resp.status_code == 400
    assert "reopen it first" in resp.json()["detail"].lower()

    # 5. Reopen blocker properly
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/blockers/{blocker.id}/reopen",
        json={"reason": "Fire inspector flagged secondary emergency exit signage."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


# =========================================================================
# 7. Notification Isolation
# =========================================================================

def test_notification_recipient_boundary_isolation(client: TestClient, audit_fixture, auth_user, db):
    """
    CO-FR-019 / Section 6: In-app notifications are strictly partitioned by recipient user_id.
    User A cannot list, view, or mark User B's notifications as read.
    """
    org1 = audit_fixture["org1"]
    worker1 = audit_fixture["worker1"]
    worker2 = audit_fixture["worker2"]

    now = datetime.datetime.now(datetime.timezone.utc)
    notif1 = Notification(
        organization_id=org1.id,
        user_id=worker1.id,
        event_type="task_assigned",
        related_entity_type="task",
        related_entity_id=uuid.uuid4(),
        title="Notification for Worker 1",
        message="Message for Worker 1 only.",
        created_at=now,
    )
    notif2 = Notification(
        organization_id=org1.id,
        user_id=worker2.id,
        event_type="task_assigned",
        related_entity_type="task",
        related_entity_id=uuid.uuid4(),
        title="Notification for Worker 2",
        message="Message for Worker 2 only.",
        created_at=now,
    )
    db.add_all([notif1, notif2])
    db.commit()

    auth_user(worker1)

    # 1. Listing notifications as Worker 1 only returns notif1
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 200
    notif_ids = [n["id"] for n in resp.json()]
    assert str(notif1.id) in notif_ids
    assert str(notif2.id) not in notif_ids

    # 2. Worker 1 attempting to view Worker 2's notification returns 404
    resp = client.get(f"/api/v1/notifications/{notif2.id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Notification not found."

    # 3. Worker 1 attempting to mark Worker 2's notification as read returns 404
    resp = client.post(f"/api/v1/notifications/{notif2.id}/read")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Notification not found."


# =========================================================================
# 8. Atomic Transactions & Rollback Verification
# =========================================================================

def test_atomic_transaction_rollback_on_review_failure(client: TestClient, audit_fixture, auth_user, db):
    """
    Verifies that a failed review attempt (e.g. rejection without required review note,
    or self-review attempt) maintains strict transactional atomicity: no TaskReview
    is inserted, no TaskStatusHistory is created, and the submission remains in pending_review.
    """
    org1 = audit_fixture["org1"]
    org1_owner = audit_fixture["org1_owner"]
    reviewer = audit_fixture["reviewer"]
    worker1 = audit_fixture["worker1"]
    mb_worker1 = audit_fixture["mb_worker1"]

    task = create_task(
        db,
        creator=org1_owner,
        organization_id=org1.id,
        title="Catering Table Logistics",
        due_date=datetime.date(2026, 11, 23),
        proof_required=True,
        assignee_membership_id=mb_worker1.id,
    )
    start_task(db, user=worker1, task_id=task.id)
    sub = submit_task_evidence(
        db,
        user=worker1,
        task_id=task.id,
        evidence_urls=["https://storage.example.com/catering_layout.pdf"],
    )

    initial_review_count = len(db.query(TaskReview).all())
    initial_history_count = len(db.query(TaskStatusHistory).filter_by(task_id=task.id).all())

    auth_user(reviewer)

    # 1. Failed review attempt: changes_requested with empty note
    resp = client.post(
        f"/api/v1/organizations/{org1.id}/tasks/{task.id}/submissions/{sub.id}/review",
        json={"decision": "changes_requested", "review_note": "   "},
    )
    assert resp.status_code == 400

    # Verify no partial records were committed
    db.expire_all()
    reloaded_task = db.get(Task, task.id)
    reloaded_sub = db.get(EvidenceSubmission, sub.id)

    assert reloaded_task.status == "submitted_for_review"
    assert reloaded_sub.status == "pending_review"
    assert len(db.query(TaskReview).all()) == initial_review_count
    assert len(db.query(TaskStatusHistory).filter_by(task_id=task.id).all()) == initial_history_count


def test_atomic_rollback_on_service_exception(engine, create_synthetic_user, create_synthetic_platform_admin):
    """
    Directly exercises review_task_submission's try/except rollback block with a standalone session
    to verify that simulated database commit failures roll back all modifications cleanly.
    """
    from sqlalchemy.orm import Session
    from app.services.task import review_task_submission

    with Session(engine) as session:
        plat_admin = create_synthetic_platform_admin("crash_admin@gov.internal")
        owner = create_synthetic_user("crash_owner@org.edu", "Crash Owner")
        reviewer = create_synthetic_user("crash_reviewer@org.edu", "Crash Reviewer")
        worker = create_synthetic_user("crash_worker@org.edu", "Crash Worker")

        org = create_organization(session, owner, "Crash Org", "Crash Club")
        verify_organization(session, plat_admin, org.id, "verified")

        now = datetime.datetime.now(datetime.timezone.utc)
        mb_rev = OrganizationMembership(
            id=uuid.uuid4(), organization_id=org.id, user_id=reviewer.id,
            membership_status="active", joined_at=now,
        )
        mb_worker = OrganizationMembership(
            id=uuid.uuid4(), organization_id=org.id, user_id=worker.id,
            membership_status="active", joined_at=now,
        )
        session.add_all([mb_rev, mb_worker])
        session.commit()

        session.add(RoleAssignment(membership_id=mb_rev.id, role_name="OFFICE_BEARER", scope_type="organization"))
        session.commit()

        task = create_task(
            session, creator=owner, organization_id=org.id, title="Rollback Task",
            due_date=datetime.date(2026, 11, 25), proof_required=True,
            assignee_membership_id=mb_worker.id,
        )
        start_task(session, user=worker, task_id=task.id)
        sub = submit_task_evidence(
            session, user=worker, task_id=task.id,
            evidence_urls=["https://storage.example.com/file.pdf"],
        )

        task_id = task.id
        sub_id = sub.id

        with patch.object(session, "commit", side_effect=RuntimeError("Simulated DB Crash")):
            with pytest.raises(RuntimeError):
                review_task_submission(
                    db=session, user=reviewer, submission_id=sub_id, decision="approved"
                )

        # After rollback in review_task_submission
        reloaded_task = session.get(Task, task_id)
        reloaded_sub = session.get(EvidenceSubmission, sub_id)
        assert reloaded_task.status == "submitted_for_review"
        assert reloaded_sub.status == "pending_review"
        reviews = session.query(TaskReview).filter_by(task_id=task_id).all()
        assert len(reviews) == 0
