"""
Slice 4A Security, Integrity & Workflow Audit Test Suite (Prompt 14).
Validates database check constraints, partial unique index single-assignee invariants,
transitive parent scope archival, sibling event isolation, terminal status guards,
reassignment authority revoking, evidence URL boundaries, blocker state machine preconditions,
and notification privacy.
"""
import uuid
from datetime import date, datetime, time, timezone

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
    cancel_task,
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
def audit_fixture(db: Session, create_synthetic_user, create_synthetic_platform_admin):
    """Sets up an audit fixture with verified org, programs, events, leads, and coordinators."""
    admin = create_synthetic_platform_admin("superadmin@campusops.internal")
    creator = create_synthetic_user("creator@org.edu", "Org Creator")
    org = create_organization(db, creator=creator, college_name="Audit University", club_name="Robotics Society")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Member 1: Assigned as Event Lead for Event 1
    lead_user = create_synthetic_user("lead1@org.edu", "Event 1 Lead")
    lead_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=lead_user.id,
        membership_status="active",
    )
    db.add(lead_mb)

    # Member 2: Sibling Event Lead for Event 2
    lead2_user = create_synthetic_user("lead2@org.edu", "Event 2 Lead")
    lead2_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=lead2_user.id,
        membership_status="active",
    )
    db.add(lead2_mb)

    # Member 3: Department Lead for Dept A
    dept_lead_user = create_synthetic_user("dept_lead@org.edu", "Dept Lead")
    dept_lead_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=dept_lead_user.id,
        membership_status="active",
    )
    db.add(dept_lead_mb)

    # Member 4: Coordinator 1
    coord1_user = create_synthetic_user("coord1@org.edu", "Coordinator One")
    coord1_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=coord1_user.id,
        membership_status="active",
    )
    db.add(coord1_mb)

    # Member 5: Coordinator 2
    coord2_user = create_synthetic_user("coord2@org.edu", "Coordinator Two")
    coord2_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=coord2_user.id,
        membership_status="active",
    )
    db.add(coord2_mb)
    db.flush()

    # Create Program with two sibling child events
    prog = create_program(db, creator, org.id, name="Tech Fest 2026")
    ev1 = create_event(db, creator, org.id, name="RoboWar Arena", program_id=prog.id)
    ev2 = create_event(db, creator, org.id, name="Drone Race", program_id=prog.id)

    # Create departments
    dept_a = create_department(db, creator, org.id, name="Hardware Ops", program_id=prog.id)
    dept_b = create_department(db, creator, org.id, name="Software Ops", program_id=prog.id)

    # Assign Leads
    assign_event_lead(db, creator, org.id, ev1.id, lead_mb.id)
    assign_event_lead(db, creator, org.id, ev2.id, lead2_mb.id)

    # Assign Department Lead
    dept_lead_ra = RoleAssignment(
        membership_id=dept_lead_mb.id,
        role_name="DEPARTMENT_LEAD",
        scope_type="department",
        scope_id=dept_a.id,
        granted_by_user_id=creator.id,
    )
    db.add(dept_lead_ra)

    # Assign Coordinator 1 to ev1 scope
    coord1_ra = RoleAssignment(
        membership_id=coord1_mb.id,
        role_name="COORDINATOR",
        scope_type="event",
        scope_id=ev1.id,
        granted_by_user_id=creator.id,
    )
    db.add(coord1_ra)

    # Foreign organization for tenant isolation tests
    alien_creator = create_synthetic_user("alien@foreign.edu", "Foreign Creator")
    alien_org = create_organization(db, alien_creator, "Foreign Institute", "Foreign Club")
    verify_organization(db, admin, alien_org.id, decision="verified")
    alien_user = create_synthetic_user("alien_worker@foreign.edu", "Foreign Worker")
    alien_mb = OrganizationMembership(
        organization_id=alien_org.id,
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
        "lead2_user": lead2_user,
        "lead2_mb": lead2_mb,
        "dept_lead_user": dept_lead_user,
        "dept_lead_mb": dept_lead_mb,
        "coord1_user": coord1_user,
        "coord1_mb": coord1_mb,
        "coord2_user": coord2_user,
        "coord2_mb": coord2_mb,
        "prog": prog,
        "ev1": ev1,
        "ev2": ev2,
        "dept_a": dept_a,
        "dept_b": dept_b,
        "alien_org": alien_org,
        "alien_creator": alien_creator,
        "alien_user": alien_user,
        "alien_mb": alien_mb,
    }


# =========================================================================
# 1. Direct Database Invariant & Partial Unique Index Tests
# =========================================================================

def test_db_constraint_single_active_assignee_different_users(engine):
    """
    Partial unique index uq_task_assignee_active strictly forbids TWO DIFFERENT
    users from simultaneously being active assignees on the same task.
    """
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        user1 = UserProfile(id=uid, auth_subject_id=f"u1_{uid.hex[:8]}", email_normalized=f"u1_{uid.hex[:8]}@audit.edu", display_name="U1", email_verified_at=now, account_status="active")
        s.add(user1)
        uid2 = uuid.uuid4()
        user2 = UserProfile(id=uid2, auth_subject_id=f"u2_{uid2.hex[:8]}", email_normalized=f"u2_{uid2.hex[:8]}@audit.edu", display_name="U2", email_verified_at=now, account_status="active")
        s.add(user2)

        org = Organization(id=uuid.uuid4(), college_name="C_Aud", club_name="Cl_Aud", created_by_user_id=uid, verification_status="verified")
        s.add(org)
        mb1 = OrganizationMembership(id=uuid.uuid4(), organization_id=org.id, user_id=uid, membership_status="active")
        s.add(mb1)
        mb2 = OrganizationMembership(id=uuid.uuid4(), organization_id=org.id, user_id=uid2, membership_status="active")
        s.add(mb2)

        task = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Single Active Worker Enforcement",
            priority="medium",
            status="assigned",
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(task)
        s.commit()

        # First active assignee (User 1)
        a1 = TaskAssignee(
            id=uuid.uuid4(),
            task_id=task.id,
            organization_id=org.id,
            membership_id=mb1.id,
            assignment_status="active",
            assigned_by_user_id=uid,
            assigned_at=now,
        )
        s.add(a1)
        s.commit()

        # Second active assignee on same task with DIFFERENT user (User 2)
        a2 = TaskAssignee(
            id=uuid.uuid4(),
            task_id=task.id,
            organization_id=org.id,
            membership_id=mb2.id,
            assignment_status="active",
            assigned_by_user_id=uid,
            assigned_at=now,
        )
        s.add(a2)
        with pytest.raises(IntegrityError):
            s.commit()
    finally:
        s.close()


def test_db_check_constraint_task_status_completed(engine):
    """Database check constraint ck_tasks_status_completed enforces completed_at presence."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        user = UserProfile(id=uid, auth_subject_id=f"u_stat_{uid.hex[:8]}", email_normalized=f"u_stat_{uid.hex[:8]}@audit.edu", display_name="U", email_verified_at=now, account_status="active")
        s.add(user)
        org = Organization(id=uuid.uuid4(), college_name="C_Stat", club_name="Cl_Stat", created_by_user_id=uid, verification_status="verified")
        s.add(org)
        s.commit()

        # Status 'completed' with completed_at=NULL must fail
        t1 = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Broken Completed Task",
            priority="medium",
            status="completed",
            completed_at=None,
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(t1)
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()

        # Status 'in_progress' with completed_at!=NULL must fail
        t2 = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Broken InProgress Task",
            priority="medium",
            status="in_progress",
            completed_at=now,
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(t2)
        with pytest.raises(IntegrityError):
            s.commit()
    finally:
        s.close()


def test_db_check_constraint_task_reviews_note_on_rejection(engine):
    """Database check constraint ck_task_reviews_note_on_rejection requires review_note on rejection."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        user = UserProfile(id=uid, auth_subject_id=f"u_rev_{uid.hex[:8]}", email_normalized=f"u_rev_{uid.hex[:8]}@audit.edu", display_name="U", email_verified_at=now, account_status="active")
        s.add(user)
        org = Organization(id=uuid.uuid4(), college_name="C_Rev", club_name="Cl_Rev", created_by_user_id=uid, verification_status="verified")
        s.add(org)
        mb = OrganizationMembership(id=uuid.uuid4(), organization_id=org.id, user_id=uid, membership_status="active")
        s.add(mb)
        task = Task(
            id=uuid.uuid4(),
            organization_id=org.id,
            scope_type="organization",
            title="Review Task",
            due_date=date(2026, 12, 1),
            created_by_user_id=uid,
            created_at=now,
            updated_at=now,
        )
        s.add(task)
        sub = EvidenceSubmission(
            id=uuid.uuid4(),
            task_id=task.id,
            submitted_by_user_id=uid,
            submitted_by_membership_id=mb.id,
            submission_number=1,
            status="pending_review",
            submitted_at=now,
        )
        s.add(sub)
        s.commit()

        # Review with 'changes_requested' and review_note=NULL must fail
        rev = TaskReview(
            id=uuid.uuid4(),
            evidence_submission_id=sub.id,
            task_id=task.id,
            reviewer_user_id=uid,
            reviewer_membership_id=mb.id,
            decision="changes_requested",
            review_note=None,
            reviewed_at=now,
        )
        s.add(rev)
        with pytest.raises(IntegrityError):
            s.commit()
    finally:
        s.close()


# =========================================================================
# 2. Scope Isolation & Sibling Event Protection
# =========================================================================

def test_event_scoped_task_isolated_from_sibling_event_leads(db: Session, audit_fixture):
    """
    An Event Lead for Event 1 CANNOT view, assign, or mutate tasks belonging to
    sibling Event 2 under the same parent program.
    """
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    ev2 = audit_fixture["ev2"]
    lead1_user = audit_fixture["lead_user"]
    coord1_mb = audit_fixture["coord1_mb"]

    # Task created under Event 2 (managed by lead2_user)
    t2 = create_task(
        db, creator, org.id, "Setup Drone Obstacle Course", date(2026, 12, 1),
        scope_type="event", scope_id=ev2.id,
    )

    # Lead 1 attempts to view Task on Event 2 -> Denied
    with pytest.raises(PermissionDeniedError):
        get_task(db, t2.id, user=lead1_user)

    # Lead 1 attempts to assign Task on Event 2 -> Denied
    with pytest.raises(PermissionDeniedError):
        assign_task(db, lead1_user, t2.id, coord1_mb.id)

    # Lead 1 attempts to change deadline on Event 2 -> Denied
    with pytest.raises(PermissionDeniedError):
        change_task_deadline(db, lead1_user, t2.id, date(2026, 12, 5), reason="Unauthorized delay")


def test_department_scoped_task_isolated_from_unrelated_departments(db: Session, audit_fixture):
    """Department Lead for Department A cannot view or mutate tasks on Department B."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    dept_b = audit_fixture["dept_b"]
    dept_lead_user = audit_fixture["dept_lead_user"]
    coord1_mb = audit_fixture["coord1_mb"]

    # Task on Department B (Software Ops)
    t_dept_b = create_task(
        db, creator, org.id, "Configure Server Cluster", date(2026, 12, 1),
        scope_type="department", scope_id=dept_b.id,
    )

    # Hardware Department Lead attempts to view or assign Software Dept task -> Denied
    with pytest.raises(PermissionDeniedError):
        get_task(db, t_dept_b.id, user=dept_lead_user)

    with pytest.raises(PermissionDeniedError):
        assign_task(db, dept_lead_user, t_dept_b.id, coord1_mb.id)


def test_task_creation_rejected_under_archived_parent_program_or_event(db: Session, audit_fixture):
    """
    Tasks cannot be created under a child event or department whose parent program is archived.
    """
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    prog = audit_fixture["prog"]
    ev1 = audit_fixture["ev1"]
    dept_a = audit_fixture["dept_a"]

    # Archive the umbrella program
    archive_program(db, creator, prog.id)

    # Attempting to create task under child event of archived program -> ScopeIntegrityError
    with pytest.raises(ScopeIntegrityError, match="Parent program of target event .* is archived"):
        create_task(db, creator, org.id, "Post-Archive Event Task", date(2026, 12, 1), scope_type="event", scope_id=ev1.id)

    # Attempting to create task under department of archived program -> ScopeIntegrityError
    with pytest.raises(ScopeIntegrityError, match="Parent program of target department .* is archived"):
        create_task(db, creator, org.id, "Post-Archive Dept Task", date(2026, 12, 1), scope_type="department", scope_id=dept_a.id)


def test_task_mutations_rejected_when_parent_event_is_archived(db: Session, audit_fixture):
    """Active task mutations are blocked if its parent event is subsequently archived."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    lead1_user = audit_fixture["lead_user"]
    coord1_mb = audit_fixture["coord1_mb"]

    # Create task under active event
    task = create_task(
        db, creator, org.id, "Rig Main Lights", date(2026, 12, 1),
        scope_type="event", scope_id=ev1.id,
    )

    # Archive the parent event
    archive_event(db, creator, ev1.id)

    # Attempting to assign task on archived event -> Denied
    with pytest.raises(PermissionDeniedError):
        assign_task(db, lead1_user, task.id, coord1_mb.id)

    # Attempting to change deadline on archived event -> Denied
    with pytest.raises(PermissionDeniedError):
        change_task_deadline(db, lead1_user, task.id, date(2026, 12, 5), reason="Post-mortem extension")


# =========================================================================
# 3. Assignment, Reassignment & Authority Revocation
# =========================================================================

def test_reassigned_worker_cannot_retain_authority(db: Session, audit_fixture):
    """
    When a task is reassigned from Worker 1 to Worker 2, Worker 1 loses all
    authority to submit evidence or advance the task.
    """
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    coord1_user = audit_fixture["coord1_user"]
    coord1_mb = audit_fixture["coord1_mb"]
    coord2_user = audit_fixture["coord2_user"]
    coord2_mb = audit_fixture["coord2_mb"]

    task = create_task(
        db, creator, org.id, "Solder Circuit Boards", date(2026, 12, 1),
        scope_type="event", scope_id=ev1.id, proof_required=True,
        assignee_membership_id=coord1_mb.id,
    )
    start_task(db, coord1_user, task.id)
    assert task.status == "in_progress"

    # Reassign task to Worker 2
    assign_task(db, creator, task.id, coord2_mb.id)

    # Verify Worker 1 is now marked unassigned
    reloaded_a1 = next(a for a in task.assignees if a.membership_id == coord1_mb.id)
    assert reloaded_a1.assignment_status == "unassigned"
    assert reloaded_a1.unassigned_at is not None
    assert reloaded_a1.unassigned_by_user_id == creator.id

    # Worker 1 attempts to submit evidence -> PermissionDeniedError
    with pytest.raises(PermissionDeniedError, match="Only active assignees can submit evidence"):
        submit_task_evidence(db, coord1_user, task.id, evidence_urls=["https://storage.cloud.gov/proof/boards.jpg"])

    # Worker 2 submits evidence -> Success
    sub = submit_task_evidence(db, coord2_user, task.id, evidence_urls=["https://storage.cloud.gov/proof/boards_v2.jpg"])
    assert sub.status == "pending_review"
    assert task.status == "submitted_for_review"


def test_terminal_status_guards_on_task_mutations(db: Session, audit_fixture):
    """Tasks in terminal status (completed, cancelled) reject further operational mutations."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    coord1_mb = audit_fixture["coord1_mb"]

    # 1. Complete task without proof
    task = create_task(
        db, creator, org.id, "Print Name Badges", date(2026, 12, 1),
        scope_type="event", scope_id=ev1.id, proof_required=False,
    )
    complete_task_without_proof(db, creator, task.id, completion_note="Badges printed")
    assert task.status == "completed"

    # Attempting duplicate completion -> TaskWorkflowError
    with pytest.raises(TaskWorkflowError, match="terminal status"):
        complete_task_without_proof(db, creator, task.id)

    # Attempting to assign completed task -> TaskWorkflowError
    with pytest.raises(TaskWorkflowError, match="terminal status"):
        assign_task(db, creator, task.id, coord1_mb.id)

    # Attempting to change deadline on completed task -> TaskWorkflowError
    with pytest.raises(TaskWorkflowError, match="terminal status"):
        change_task_deadline(db, creator, task.id, date(2026, 12, 10), reason="Extension")

    # Attempting to cancel completed task -> TaskWorkflowError
    with pytest.raises(TaskWorkflowError, match="terminal status"):
        cancel_task(db, creator, task.id, cancellation_reason="No longer needed")


def test_task_cancellation_lifecycle(db: Session, audit_fixture):
    """An active task can be cancelled by authorized manager with mandatory reason."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    coord1_user = audit_fixture["coord1_user"]
    coord1_mb = audit_fixture["coord1_mb"]

    task = create_task(
        db, creator, org.id, "Order Fireworks", date(2026, 12, 1),
        scope_type="event", scope_id=ev1.id, assignee_membership_id=coord1_mb.id,
    )

    # Cancel without reason -> ValueError
    with pytest.raises(ValueError, match="cancellation reason is mandatory"):
        cancel_task(db, creator, task.id, cancellation_reason="")

    # Cancel with valid reason
    cancelled_task = cancel_task(db, creator, task.id, cancellation_reason="Permit denied by local fire department")
    assert cancelled_task.status == "cancelled"

    # Worker cannot start cancelled task
    with pytest.raises(TaskWorkflowError, match="Cannot start task currently in status 'cancelled'"):
        start_task(db, coord1_user, task.id)

    # Cannot cancel already cancelled task
    with pytest.raises(TaskWorkflowError, match="terminal status"):
        cancel_task(db, creator, task.id, cancellation_reason="Second cancel")


# =========================================================================
# 4. Evidence URL Validation Boundaries
# =========================================================================

def test_evidence_url_validation_edge_cases():
    """Validates URL parsing rules, scheme restrictions, and length bounding."""
    # Valid URLs
    assert validate_evidence_url("https://drive.google.com/file/d/123/view") == "https://drive.google.com/file/d/123/view"
    assert validate_evidence_url("http://storage.internal.org/proof.pdf") == "http://storage.internal.org/proof.pdf"

    # Rejection of dangerous or non-HTTP schemes
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_evidence_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_evidence_url("javascript:alert(1)")

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_evidence_url("data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==")

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_evidence_url("ftp://ftp.example.com/file.zip")

    # Relative paths
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_evidence_url("/uploads/proof.jpg")

    # Missing netloc / hostname
    with pytest.raises(ValueError, match="malformed or missing hostname"):
        validate_evidence_url("http://")

    # Empty string
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_evidence_url("   ")

    # Oversized URL (>2048 chars)
    long_url = "https://example.com/" + ("a" * 2050)
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        validate_evidence_url(long_url)


# =========================================================================
# 5. Operational Blocker Preconditions
# =========================================================================

def test_operational_blocker_reopen_and_resolve_preconditions(db: Session, audit_fixture):
    """Tests blocker resolution and reopening state transition rules."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]

    blocker = create_operational_blocker(
        db,
        creator=creator,
        organization_id=org.id,
        title="Microphone feedback on stage",
        description="Acoustic echo on front speakers",
        scope_type="event",
        scope_id=ev1.id,
    )
    assert blocker.status == "open"

    # Reopening an already open blocker -> OperationalBlockerError
    with pytest.raises(OperationalBlockerError, match="Must be 'resolved' or 'wont_fix'"):
        reopen_operational_blocker(db, creator, blocker.id, reason="Already open")

    # Resolving without a note -> ValueError
    with pytest.raises(ValueError, match="resolution note is mandatory"):
        resolve_operational_blocker(db, creator, blocker.id, resolution_note="")

    # Resolve blocker
    resolve_operational_blocker(db, creator, blocker.id, resolution_note="Re-positioned microphones away from monitors")
    assert blocker.status == "resolved"
    assert blocker.resolved_at is not None

    # Resolving an already resolved blocker -> OperationalBlockerError
    with pytest.raises(OperationalBlockerError, match="already in status 'resolved'"):
        resolve_operational_blocker(db, creator, blocker.id, resolution_note="Second resolve")

    # Reopen without reason -> ValueError
    with pytest.raises(ValueError, match="meaningful reason is mandatory"):
        reopen_operational_blocker(db, creator, blocker.id, reason="")

    # Reopen with reason -> status becomes open
    reopened = reopen_operational_blocker(db, creator, blocker.id, reason="Echo returned during rehearsal")
    assert reopened.status == "open"
    assert reopened.resolved_at is None
    assert reopened.resolved_by_user_id is None


# =========================================================================
# 6. Notification Privacy & In-App Isolation
# =========================================================================

def test_notification_privacy_and_isolation(db: Session, audit_fixture):
    """Notifications are strictly in-app and can only be marked as read by the recipient."""
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    ev1 = audit_fixture["ev1"]
    coord1_user = audit_fixture["coord1_user"]
    coord1_mb = audit_fixture["coord1_mb"]
    coord2_user = audit_fixture["coord2_user"]

    # Assign task to Coord 1 -> notification generated for Coord 1
    task = create_task(
        db, creator, org.id, "Setup Video Cameras", date(2026, 12, 1),
        scope_type="event", scope_id=ev1.id, assignee_membership_id=coord1_mb.id,
    )
    notifs = list_notifications(db, coord1_user.id, org.id)
    assert len(notifs) >= 1
    target_notif = notifs[0]
    assert target_notif.user_id == coord1_user.id
    assert target_notif.is_read is False

    # Coord 2 attempts to mark Coord 1's notification as read -> ValueError
    with pytest.raises(ValueError, match="Notification not found or access denied"):
        mark_notification_as_read(db, coord2_user, target_notif.id)

    # Coord 1 marks notification as read -> Success
    read_notif = mark_notification_as_read(db, coord1_user, target_notif.id)
    assert read_notif.is_read is True
    assert read_notif.read_at is not None


# =========================================================================
# 7. Active Task Assignee Can View Org-Scoped Task
# =========================================================================

def test_active_task_assignee_can_view_org_scoped_task(db: Session, audit_fixture):
    """
    A coordinator assigned to an organization-scoped task is authorized to view
    the task while actively assigned, and loses access once unassigned.
    """
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    coord1_user = audit_fixture["coord1_user"]
    coord1_mb = audit_fixture["coord1_mb"]
    coord2_mb = audit_fixture["coord2_mb"]

    # Org-level task assigned to Coord 1
    t_org = create_task(
        db, creator, org.id, "Draft Club Budget", date(2026, 12, 1),
        scope_type="organization", assignee_membership_id=coord1_mb.id,
    )

    # Coord 1 can view their assigned task
    task_view = get_task(db, t_org.id, user=coord1_user)
    assert task_view.id == t_org.id

    # Creator reassigns task to Coord 2
    assign_task(db, creator, t_org.id, coord2_mb.id)

    # Coord 1 can no longer view the organization-level task
    with pytest.raises(PermissionDeniedError):
        get_task(db, t_org.id, user=coord1_user)
