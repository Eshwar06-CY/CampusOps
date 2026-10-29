"""
CampusOps — Slice 4A Task Management and Operational Blocker Foundation Test Suite

Validates:
1. Task creation, mandatory deadlines, and scoped hierarchy (org, program, event, department).
2. Tenant isolation and scope integrity (unverified orgs, cross-tenant links, archived scopes).
3. Task assignment and reassignment audit (member eligibility, account status, unassignment tracking).
4. Workflow state machine (start, submit, URL validation, non-empty rejection notes, self-review block).
5. Evidence requirements (proof_required enforcement, HTTP/HTTPS URL validation, no direct complete).
6. Deadline adjustments with mandatory reason and history preservation.
7. Operational blockers (creation, scoping, lead-only resolution, history, reopen).
8. Durable in-app notifications.
9. Database check constraints and partial unique indexes.
10. Atomic rollback on fault injection.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Department, Event, EventLeadAssignment, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.role import PlatformAdmin, RoleAssignment
from app.models.task import (
    EvidenceArtifact,
    EvidenceSubmission,
    Notification,
    OperationalBlocker,
    OperationalBlockerHistory,
    Task,
    TaskAssignee,
    TaskDeadlineHistory,
    TaskReview,
    TaskStatusHistory,
)
from app.models.user import UserProfile
from app.services.errors import (
    EvidenceSubmissionError,
    OperationalBlockerError,
    OperationalBlockerNotFoundError,
    PermissionDeniedError,
    ReviewError,
    ScopeIntegrityError,
    SelfReviewError,
    TaskAssigneeError,
    TaskError,
    TaskNotFoundError,
    TaskWorkflowError,
)
from app.services.event import (
    archive_event,
    archive_program,
    assign_event_lead,
    create_department,
    create_event,
    create_program,
)
from app.services.organization import create_organization, verify_organization
from app.services.task import (
    archive_task,
    assign_task,
    change_task_deadline,
    complete_task_without_proof,
    create_operational_blocker,
    create_task,
    get_operational_blocker,
    get_task,
    list_notifications,
    mark_notification_as_read,
    reopen_operational_blocker,
    resolve_operational_blocker,
    review_task_submission,
    start_task,
    submit_task_evidence,
    validate_evidence_url,
)


@pytest.fixture
def task_fixture(db: Session, create_synthetic_user, create_synthetic_platform_admin):
    """Sets up an audit fixture with verified org, admin, event lead, coordinator, and members."""
    admin = create_synthetic_platform_admin("superadmin@campusops.internal")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Tech University", club_name="Robotics Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Member 1: Assigned as Event Lead
    lead_user = create_synthetic_user("event_lead@org.edu", "Event Lead")
    lead_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=lead_user.id,
        membership_status="active",
    )
    db.add(lead_mb)
    db.flush()

    # Member 2: Coordinator (worker)
    coord_user = create_synthetic_user("coord@org.edu", "Coordinator User")
    coord_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=coord_user.id,
        membership_status="active",
    )
    db.add(coord_mb)
    db.flush()

    # Member 3: Another Coordinator
    coord2_user = create_synthetic_user("coord2@org.edu", "Coordinator Two")
    coord2_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=coord2_user.id,
        membership_status="active",
    )
    db.add(coord2_mb)
    db.flush()

    # Create Program, Standalone Event, Child Event, and Departments
    prog = create_program(db, creator, org.id, name="RoboFest 2026")
    child_ev = create_event(db, creator, org.id, name="RoboWar Day 1", program_id=prog.id)
    standalone_ev = create_event(db, creator, org.id, name="Intro Workshop")

    prog_dept = create_department(db, creator, org.id, name="Tech Dept", program_id=prog.id)
    ev_dept = create_department(db, creator, org.id, name="Logistics Dept", standalone_event_id=standalone_ev.id)

    # Assign Event Lead to child event
    assign_event_lead(db, creator, org.id, child_ev.id, lead_mb.id)

    # Assign Coordinator role to coord_user in event scope
    coord_ra = RoleAssignment(
        membership_id=coord_mb.id,
        role_name="COORDINATOR",
        scope_type="event",
        scope_id=child_ev.id,
        granted_by_user_id=creator.id,
    )
    db.add(coord_ra)

    # Cross-tenant org for isolation testing
    other_creator = create_synthetic_user("alien@alien.edu", "Alien Creator")
    other_org = create_organization(db, other_creator, "Alien University", "Alien Club")
    verify_organization(db, admin, other_org.id, decision="verified")

    alien_user = create_synthetic_user("alien_member@alien.edu", "Alien Member")
    alien_mb = OrganizationMembership(
        organization_id=other_org.id,
        user_id=alien_user.id,
        membership_status="active",
    )
    db.add(alien_mb)
    db.commit()

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "lead_user": lead_user,
        "lead_mb": lead_mb,
        "coord_user": coord_user,
        "coord_mb": coord_mb,
        "coord2_user": coord2_user,
        "coord2_mb": coord2_mb,
        "prog": prog,
        "child_ev": child_ev,
        "standalone_ev": standalone_ev,
        "prog_dept": prog_dept,
        "ev_dept": ev_dept,
        "other_org": other_org,
        "other_creator": other_creator,
        "alien_user": alien_user,
        "alien_mb": alien_mb,
    }


# =========================================================================
# 1. Task Creation and Scope Validation
# =========================================================================

def test_create_task_across_valid_scopes(db: Session, task_fixture):
    """Verify task creation across organization, program, event, and department scopes."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    prog = task_fixture["prog"]
    child_ev = task_fixture["child_ev"]
    ev_dept = task_fixture["ev_dept"]

    due = date(2026, 12, 1)

    # 1. Org-scoped task
    t_org = create_task(db, creator, org.id, "Setup Club Bank Account", due, scope_type="organization")
    assert t_org.scope_type == "organization"
    assert t_org.scope_id is None
    assert t_org.status == "not_started"
    assert t_org.due_date == due
    assert t_org.timezone == "Asia/Kolkata"

    # 2. Program-scoped task
    t_prog = create_task(db, creator, org.id, "Publish Fest Schedule", due, scope_type="program", scope_id=prog.id)
    assert t_prog.scope_type == "program"
    assert t_prog.program_id == prog.id
    assert t_prog.event_id is None

    # 3. Event-scoped task
    t_ev = create_task(db, creator, org.id, "Setup Arena Rig", due, scope_type="event", scope_id=child_ev.id)
    assert t_ev.scope_type == "event"
    assert t_ev.event_id == child_ev.id
    assert t_ev.program_id == prog.id  # Automatically inherited from child event

    # 4. Department-scoped task
    t_dept = create_task(db, creator, org.id, "Procure Mics", due, scope_type="department", scope_id=ev_dept.id)
    assert t_dept.scope_type == "department"
    assert t_dept.department_id == ev_dept.id
    assert t_dept.event_id == ev_dept.standalone_event_id


def test_create_task_rejects_missing_deadline(db: Session, task_fixture):
    """A required deadline cannot be omitted."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]

    with pytest.raises(ValueError, match="Task deadline .* is required and cannot be omitted"):
        create_task(db, creator, org.id, "No Deadline Task", due_date=None)


def test_create_task_rejects_unverified_organization(db: Session, task_fixture, create_synthetic_user):
    """Tasks cannot be created in an organization pending verification."""
    unver_creator = create_synthetic_user("unver@org.edu", "Unverified Creator")
    unver_org = create_organization(db, unver_creator, "Unverified College", "Unverified Club")

    with pytest.raises(PermissionDeniedError, match="Organization must be verified before operational tasks can be created"):
        create_task(db, unver_creator, unver_org.id, "Draft Task", date(2026, 12, 1))


def test_create_task_rejects_archived_or_alien_scopes(db: Session, task_fixture):
    """Tasks cannot reference alien or archived programs/events/departments."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    other_org = task_fixture["other_org"]
    prog = task_fixture["prog"]

    # Alien scope
    other_creator = task_fixture["other_creator"]
    alien_ev = create_event(db, other_creator, other_org.id, "Alien Event")
    with pytest.raises(ScopeIntegrityError, match="belongs to another organization"):
        create_task(db, creator, org.id, "Alien Scope Task", date(2026, 12, 1), scope_type="event", scope_id=alien_ev.id)

    # Archived program
    archive_program(db, creator, prog.id)
    with pytest.raises(ScopeIntegrityError, match="archived"):
        create_task(db, creator, org.id, "Archived Program Task", date(2026, 12, 1), scope_type="program", scope_id=prog.id)


# =========================================================================
# 2. Assignment, Reassignment and Eligibility
# =========================================================================

def test_assign_and_reassign_task_audit(db: Session, task_fixture):
    """Assigning and reassigning preserves history, emits notification, and updates status."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]
    coord_mb = task_fixture["coord_mb"]
    coord_user = task_fixture["coord_user"]
    coord2_mb = task_fixture["coord2_mb"]

    task = create_task(db, creator, org.id, "Deploy Arena Sensors", date(2026, 12, 1), scope_type="event", scope_id=child_ev.id)
    assert task.status == "not_started"

    # 1. First assignment
    a1 = assign_task(db, creator, task.id, coord_mb.id)
    assert a1.assignment_status == "active"
    assert a1.assigned_by_user_id == creator.id
    assert a1.unassigned_at is None
    assert task.status == "assigned"

    # Verify notification created
    notifs = list_notifications(db, coord_user.id, org.id)
    assert len(notifs) >= 1
    assert notifs[0].event_type == "task_assigned"

    # 2. Reassignment to second coordinator
    a2 = assign_task(db, creator, task.id, coord2_mb.id)
    assert a2.assignment_status == "active"
    assert a2.membership_id == coord2_mb.id

    # Verify previous assignment was marked unassigned
    reloaded_a1 = db.get(TaskAssignee, a1.id)
    assert reloaded_a1.assignment_status == "unassigned"
    assert reloaded_a1.unassigned_at is not None
    assert reloaded_a1.unassigned_by_user_id == creator.id


def test_assign_task_rejects_cross_tenant_and_ineligible_members(db: Session, task_fixture, create_synthetic_user):
    """Assigning task rejects cross-tenant members, suspended users, or unverified emails."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]
    alien_mb = task_fixture["alien_mb"]

    task = create_task(db, creator, org.id, "Security Sweep", date(2026, 12, 1), scope_type="event", scope_id=child_ev.id)

    # 1. Cross-tenant member
    with pytest.raises(ScopeIntegrityError, match="Assignee belongs to a different organization"):
        assign_task(db, creator, task.id, alien_mb.id)

    # 2. Suspended member
    susp_user = create_synthetic_user("susp@org.edu", "Suspended Member", account_status="suspended")
    susp_mb = OrganizationMembership(organization_id=org.id, user_id=susp_user.id, membership_status="active")
    db.add(susp_mb)
    db.flush()
    with pytest.raises(TaskAssigneeError, match="user account is not active"):
        assign_task(db, creator, task.id, susp_mb.id)

    # 3. Unverified email member
    unver_user = create_synthetic_user("unver_email@org.edu", "Unverified Member", verified=False)
    unver_mb = OrganizationMembership(organization_id=org.id, user_id=unver_user.id, membership_status="active")
    db.add(unver_mb)
    db.flush()
    with pytest.raises(TaskAssigneeError, match="email is unverified"):
        assign_task(db, creator, task.id, unver_mb.id)


# =========================================================================
# 3. Deadline Change Audit
# =========================================================================

def test_change_task_deadline_audit(db: Session, task_fixture):
    """Deadline changes require authorized actor, mandatory reason, and preserve history."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]
    coord_mb = task_fixture["coord_mb"]

    initial_due = date(2026, 12, 1)
    task = create_task(
        db, creator, org.id, "Assemble Stage", initial_due,
        scope_type="event", scope_id=child_ev.id, assignee_membership_id=coord_mb.id
    )

    # Reject empty reason
    with pytest.raises(ValueError, match="meaningful reason is mandatory"):
        change_task_deadline(db, creator, task.id, date(2026, 12, 5), reason="")

    # Authorized change
    history = change_task_deadline(
        db, creator, task.id, new_due_date=date(2026, 12, 5), new_due_time=time(18, 0),
        reason="Vendor shipment delayed by rain"
    )
    assert history.previous_due_date == initial_due
    assert history.new_due_date == date(2026, 12, 5)
    assert history.new_due_time == time(18, 0)
    assert history.reason == "Vendor shipment delayed by rain"
    assert history.changed_by_user_id == creator.id

    # Verify task updated
    assert task.due_date == date(2026, 12, 5)
    assert task.due_time == time(18, 0)


# =========================================================================
# 4. Workflow State Machine, Evidence & Review Lifecycle
# =========================================================================

def test_task_full_workflow_with_rejection_and_approval(db: Session, task_fixture):
    """
    Validates complete workflow:
    not_started -> assigned -> in_progress -> submitted_for_review ->
    changes_requested (with mandatory note) -> resubmitted -> approved -> completed.
    """
    creator = task_fixture["creator"]
    lead_user = task_fixture["lead_user"]
    coord_user = task_fixture["coord_user"]
    coord_mb = task_fixture["coord_mb"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]

    # 1. Create task requiring proof
    task = create_task(
        db, creator, org.id, "Build Main Stage Backdrop", date(2026, 12, 1),
        scope_type="event", scope_id=child_ev.id, proof_required=True,
        assignee_membership_id=coord_mb.id
    )
    assert task.status == "assigned"

    # 2. Worker starts task
    start_task(db, coord_user, task.id)
    assert task.status == "in_progress"

    # 3. Submitting proof without evidence is rejected
    with pytest.raises(EvidenceSubmissionError, match="requires completion proof"):
        submit_task_evidence(db, coord_user, task.id, evidence_urls=[])

    # 4. Unsafe or malformed URLs rejected
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        submit_task_evidence(db, coord_user, task.id, evidence_urls=["ftp://fileserver/proof.pdf"])

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        submit_task_evidence(db, coord_user, task.id, evidence_urls=["javascript:alert(1)"])

    # 5. Worker submits first evidence attempt
    sub1 = submit_task_evidence(
        db, coord_user, task.id,
        evidence_urls=["https://storage.cloud.gov/proof/backdrop_v1.jpg"],
        submitter_note="Completed framing"
    )
    assert sub1.submission_number == 1
    assert sub1.status == "pending_review"
    assert task.status == "submitted_for_review"

    # 6. Self-Review Block: Worker cannot approve their own submission
    with pytest.raises(SelfReviewError, match="cannot review or approve their own"):
        review_task_submission(db, coord_user, sub1.id, decision="approved")

    # 7. Rejection without a reason is rejected
    with pytest.raises(ValueError, match="rejection reason / review note is mandatory"):
        review_task_submission(db, lead_user, sub1.id, decision="changes_requested", review_note="")

    # 8. Lead requests changes
    rev1 = review_task_submission(
        db, lead_user, sub1.id, decision="changes_requested",
        review_note="Framing is crooked on the left side; please reinforce."
    )
    assert rev1.decision == "changes_requested"
    assert sub1.status == "changes_requested"
    assert task.status == "changes_requested"
    assert task.completed_at is None

    # 9. Duplicate review on already reviewed submission rejected
    with pytest.raises(TaskWorkflowError, match="not pending review"):
        review_task_submission(db, lead_user, sub1.id, decision="approved")

    # 10. Worker resubmits revised evidence
    sub2 = submit_task_evidence(
        db, coord_user, task.id,
        evidence_urls=["https://storage.cloud.gov/proof/backdrop_v2_reinforced.jpg"],
        submitter_note="Reinforced and straightened framing."
    )
    assert sub2.submission_number == 2
    assert sub2.status == "pending_review"
    assert task.status == "submitted_for_review"

    # 11. Lead approves
    rev2 = review_task_submission(
        db, lead_user, sub2.id, decision="approved",
        review_note="Looks solid and aligned. Approved."
    )
    assert rev2.decision == "approved"
    assert sub2.status == "approved"
    assert task.status == "completed"
    assert task.completed_at is not None

    # 12. Direct completion of proof-required task without review is forbidden
    with pytest.raises(TaskWorkflowError, match="requires evidence submission and formal review"):
        complete_task_without_proof(db, creator, task.id)


def test_complete_task_without_proof_rule(db: Session, task_fixture):
    """Tasks with proof_required=False can be completed directly by authorized manager."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]
    coord_mb = task_fixture["coord_mb"]

    task = create_task(
        db, creator, org.id, "Send Reminder Email to Club Members", date(2026, 12, 1),
        scope_type="event", scope_id=child_ev.id, proof_required=False,
        assignee_membership_id=coord_mb.id
    )
    assert task.proof_required is False

    # Complete without proof
    complete_task_without_proof(db, creator, task.id, completion_note="Email sent via club list")
    assert task.status == "completed"
    assert task.completed_at is not None


# =========================================================================
# 5. Operational Blockers (CO-FR-012)
# =========================================================================

def test_operational_blocker_lifecycle(db: Session, task_fixture):
    """Verifies creation, scoping, resolution with mandatory note, and reopen."""
    creator = task_fixture["creator"]
    lead_user = task_fixture["lead_user"]
    coord_user = task_fixture["coord_user"]
    org = task_fixture["org"]
    child_ev = task_fixture["child_ev"]

    # 1. Coordinator reports an operational blocker in event scope
    blocker = create_operational_blocker(
        db,
        creator=coord_user,
        organization_id=org.id,
        title="Main Seminar Hall Locked",
        description="Keys are missing from security desk; cannot setup sound gear.",
        scope_type="event",
        scope_id=child_ev.id,
        priority="high",
    )
    assert blocker.status == "open"
    assert blocker.priority == "high"
    assert blocker.resolved_at is None

    # 2. Coordinator cannot resolve blocker (requires lead authority)
    with pytest.raises(PermissionDeniedError):
        resolve_operational_blocker(db, coord_user, blocker.id, resolution_note="Found key")

    # 3. Resolution without note rejected
    with pytest.raises(ValueError, match="meaningful resolution note is mandatory"):
        resolve_operational_blocker(db, lead_user, blocker.id, resolution_note="")

    # 4. Lead resolves blocker
    resolved = resolve_operational_blocker(
        db, lead_user, blocker.id,
        resolution_note="Obtained spare master key from Estate Office."
    )
    assert resolved.status == "resolved"
    assert resolved.resolved_by_user_id == lead_user.id
    assert resolved.resolved_at is not None

    # 5. Lead reopens blocker if issue recurs
    reopened = reopen_operational_blocker(db, lead_user, blocker.id, reason="Door lock mechanism jammed again")
    assert reopened.status == "open"
    assert reopened.resolved_at is None
    assert reopened.resolution_note is None


def test_operational_blocker_cross_tenant_rejected(db: Session, task_fixture):
    """Blocker cannot reference entities from another organization."""
    creator = task_fixture["creator"]
    org = task_fixture["org"]
    other_org = task_fixture["other_org"]
    other_creator = task_fixture["other_creator"]
    alien_ev = create_event(db, other_creator, other_org.id, "Alien Event")

    with pytest.raises(ScopeIntegrityError, match="belongs to another organization"):
        create_operational_blocker(
            db,
            creator=creator,
            organization_id=org.id,
            title="Alien Event Issue",
            description="Trying to link alien event",
            scope_type="event",
            scope_id=alien_ev.id,
            event_id=alien_ev.id,
        )


# =========================================================================
# 6. Database Constraints and Partial Unique Index
# =========================================================================

def test_db_constraint_task_priority(engine):
    """Database check constraint rejects invalid task priority."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        user = UserProfile(id=uid, auth_subject_id="u1", email_normalized="u1@a.edu", display_name="U1", email_verified_at=now, account_status="active")
        s.add(user)
        org = Organization(id=uuid.uuid4(), college_name="C", club_name="Cl", created_by_user_id=uid, verification_status="verified")
        s.add(org)
        s.commit()

        bad_task = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Bad Priority Task",
            priority="invalid_super_urgent",
            status="not_started",
            proof_required=True,
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(bad_task)
        with pytest.raises(IntegrityError):
            s.commit()
    finally:
        s.close()


def test_db_constraint_duplicate_active_assignee(engine):
    """Partial unique index uq_task_assignee_active rejects duplicate active assignment."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        user = UserProfile(id=uid, auth_subject_id="u2", email_normalized="u2@a.edu", display_name="U2", email_verified_at=now, account_status="active")
        s.add(user)
        org = Organization(id=uuid.uuid4(), college_name="C2", club_name="Cl2", created_by_user_id=uid, verification_status="verified")
        s.add(org)
        mb = OrganizationMembership(id=uuid.uuid4(), organization_id=org.id, user_id=uid, membership_status="active")
        s.add(mb)
        task = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Uniq Task",
            priority="medium",
            status="assigned",
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(task)
        s.commit()

        a1 = TaskAssignee(
            id=uuid.uuid4(),
            task_id=task.id,
            organization_id=org.id,
            membership_id=mb.id,
            assignment_status="active",
            assigned_by_user_id=uid,
            assigned_at=now,
        )
        s.add(a1)
        s.commit()

        # Duplicate active assignee
        a2 = TaskAssignee(
            id=uuid.uuid4(),
            task_id=task.id,
            organization_id=org.id,
            membership_id=mb.id,
            assignment_status="active",
            assigned_by_user_id=uid,
            assigned_at=now,
        )
        s.add(a2)
        with pytest.raises(IntegrityError):
            s.commit()
    finally:
        s.close()


# =========================================================================
# 7. Atomic Rollback on Fault Injection
# =========================================================================

def test_review_task_submission_atomic_rollback_on_failure(engine):
    """Failure during review commit rolls back submission status and review record atomically."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        admin_id = uuid.uuid4()
        admin = UserProfile(id=admin_id, auth_subject_id="admin_rb", email_normalized="admin_rb@a.edu", display_name="Admin", email_verified_at=now, account_status="active")
        s.add(admin)

        worker_id = uuid.uuid4()
        worker = UserProfile(id=worker_id, auth_subject_id="worker_rb", email_normalized="worker_rb@a.edu", display_name="Worker", email_verified_at=now, account_status="active")
        s.add(worker)

        org_id = uuid.uuid4()
        org = Organization(id=org_id, college_name="Rollback University", club_name="Rollback Club", created_by_user_id=admin_id, verification_status="verified")
        s.add(org)

        admin_mb = OrganizationMembership(id=uuid.uuid4(), organization_id=org_id, user_id=admin_id, membership_status="active")
        s.add(admin_mb)
        admin_ra = RoleAssignment(id=uuid.uuid4(), membership_id=admin_mb.id, role_name="PRIMARY_ADMIN", scope_type="organization", scope_id=org_id)
        s.add(admin_ra)

        worker_mb = OrganizationMembership(id=uuid.uuid4(), organization_id=org_id, user_id=worker_id, membership_status="active")
        s.add(worker_mb)

        task = Task(
            id=uuid.uuid4(),
            organization_id=org_id,
            scope_type="organization",
            title="Rollback Proof Task",
            priority="medium",
            status="submitted_for_review",
            due_date=date(2026, 12, 1),
            created_by_user_id=admin_id,
            created_at=now,
            updated_at=now,
        )
        s.add(task)

        submission = EvidenceSubmission(
            id=uuid.uuid4(),
            task_id=task.id,
            submitted_by_user_id=worker_id,
            submitted_by_membership_id=worker_mb.id,
            submission_number=1,
            status="pending_review",
            submitted_at=now,
        )
        s.add(submission)
        s.commit()

        sub_id = submission.id
        task_id = task.id

        # Inject failure into s.commit during review_task_submission
        with patch.object(s, "commit", side_effect=RuntimeError("Simulated DB Crash on review")):
            with pytest.raises(RuntimeError, match="Simulated DB Crash on review"):
                review_task_submission(s, admin, sub_id, decision="approved", review_note="Approved")

        # Verify atomic rollback
        reloaded_sub = s.get(EvidenceSubmission, sub_id)
        assert reloaded_sub.status == "pending_review"

        reloaded_task = s.get(Task, task_id)
        assert reloaded_task.status == "submitted_for_review"
        assert reloaded_task.completed_at is None

        reviews = s.execute(select(TaskReview).where(TaskReview.evidence_submission_id == sub_id)).scalars().all()
        assert len(reviews) == 0
    finally:
        s.close()
