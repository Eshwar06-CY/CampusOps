import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.event import Department, Event, EventLeadAssignment, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.services.errors import (
    DepartmentNotFoundError,
    DuplicateEventLeadError,
    EventLeadError,
    EventNotFoundError,
    PermissionDeniedError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.event import (
    archive_department,
    archive_event,
    archive_program,
    assign_event_lead,
    create_department,
    create_event,
    create_program,
    get_active_event_leads,
    get_department,
    get_event,
    get_program,
    revoke_event_lead,
    validate_department_scope_assignment,
    validate_event_lead_eligibility,
    validate_event_scope_assignment,
    validate_program_scope_assignment,
)
from app.services.permissions import (
    ACTION_REVIEW_PROOF,
    can_perform,
)


@pytest.fixture
def verified_org_setup(db, create_synthetic_user):
    """Fixture providing a verified organization with an active Primary Administrator."""
    admin_user = create_synthetic_user("primary_admin@campus.edu")
    org = Organization(
        college_name="Engineering College",
        club_name="Tech Club",
        verification_status="verified",
        created_by_user_id=admin_user.id,
    )
    db.add(org)
    db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=admin_user.id,
        membership_status="active",
    )
    db.add(membership)
    db.flush()

    role = RoleAssignment(
        membership_id=membership.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
    )
    db.add(role)
    db.flush()

    return org, admin_user, membership


@pytest.fixture
def unverified_org_setup(db, create_synthetic_user):
    """Fixture providing a pending_verification organization."""
    creator = create_synthetic_user("creator@campus.edu")
    org = Organization(
        college_name="Medical College",
        club_name="Health Club",
        verification_status="pending_verification",
        created_by_user_id=creator.id,
    )
    db.add(org)
    db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        membership_status="active",
    )
    db.add(membership)
    db.flush()

    role = RoleAssignment(
        membership_id=membership.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
    )
    db.add(role)
    db.flush()

    return org, creator, membership


# =========================================================================
# 1. Database Relational Constraints & Invariants
# =========================================================================


def test_program_name_unique_per_organization(db, verified_org_setup):
    """Verify uq_programs_org_name constraint prevents duplicate program names in the same organization."""
    org, admin, _ = verified_org_setup

    prog1 = Program(
        organization_id=org.id,
        name="Tech Week 2027",
        created_by_user_id=admin.id,
    )
    db.add(prog1)
    db.flush()

    prog2 = Program(
        organization_id=org.id,
        name="Tech Week 2027",
        created_by_user_id=admin.id,
    )
    db.add(prog2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_department_exclusive_parent_check_constraint(db, verified_org_setup):
    """Verify ck_departments_exclusive_parent check constraint at database level."""
    org, admin, _ = verified_org_setup

    prog = Program(organization_id=org.id, name="Fest 2027", created_by_user_id=admin.id)
    ev = Event(organization_id=org.id, name="Hackathon", created_by_user_id=admin.id)
    db.add_all([prog, ev])
    db.flush()

    # 1. Both parent keys NULL -> rejected by check constraint
    dept_none = Department(
        organization_id=org.id,
        name="Orphan Dept",
        program_id=None,
        standalone_event_id=None,
        created_by_user_id=admin.id,
    )
    db.add(dept_none)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    # 2. Both parent keys populated -> rejected by check constraint
    dept_both = Department(
        organization_id=org.id,
        name="Dual Parent Dept",
        program_id=prog.id,
        standalone_event_id=ev.id,
        created_by_user_id=admin.id,
    )
    db.add(dept_both)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_event_lead_active_uniqueness_constraint(db, verified_org_setup, create_synthetic_user):
    """Verify uq_event_lead_active partial index prevents duplicate active leads for the same member."""
    org, admin, _ = verified_org_setup
    lead_user = create_synthetic_user("lead1@campus.edu")
    membership = OrganizationMembership(organization_id=org.id, user_id=lead_user.id, membership_status="active")
    event = Event(organization_id=org.id, name="Summit 2027", created_by_user_id=admin.id)
    db.add_all([membership, event])
    db.flush()

    # First active assignment succeeds
    lead1 = EventLeadAssignment(
        organization_id=org.id,
        event_id=event.id,
        membership_id=membership.id,
        assigned_by_user_id=admin.id,
        revoked_at=None,
    )
    db.add(lead1)
    db.flush()

    # Second active assignment for same member & event fails
    lead2 = EventLeadAssignment(
        organization_id=org.id,
        event_id=event.id,
        membership_id=membership.id,
        assigned_by_user_id=admin.id,
        revoked_at=None,
    )
    db.add(lead2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# =========================================================================
# 2. Dual Setup Journeys: Standalone vs Multi-Event Program Workflows
# =========================================================================


def test_standalone_event_workflow_lifecycle(db, verified_org_setup):
    """Test Workflow A: Standalone event creation with dedicated standalone departments."""
    org, admin, _ = verified_org_setup

    # 1. Create Standalone Event (program_id is None)
    event = create_event(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="Standalone Robotics Workshop",
        program_id=None,
        event_date=date(2027, 3, 15),
        venue="Lab 402",
        event_format="in_person",
        registration_mode="individual",
    )
    assert event.is_standalone is True
    assert event.program_id is None
    assert event.status == "draft"

    # 2. Create Standalone Department belonging to this standalone event
    dept = create_department(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="Workshop Logistics",
        standalone_event_id=event.id,
    )
    assert dept.is_program_shared is False
    assert dept.standalone_event_id == event.id
    assert dept.program_id is None


def test_multi_event_program_workflow_lifecycle(db, verified_org_setup, create_synthetic_user):
    """Test Workflow B: Multi-event program with shared departments, child events, and multiple leads."""
    org, admin, _ = verified_org_setup

    # 1. Create Program
    program = create_program(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="E-Week 2027",
        description="Entrepreneurship Week",
        planned_start_date=date(2027, 4, 1),
        planned_end_date=date(2027, 4, 7),
    )
    assert program.id is not None
    assert program.is_active() is True

    # 2. Create Shared Program Department (D-SLICE3-01)
    shared_dept = create_department(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="Program Sponsorship",
        program_id=program.id,
    )
    assert shared_dept.is_program_shared is True
    assert shared_dept.program_id == program.id

    # 3. Create Child Event 1 under Program
    child_event_1 = create_event(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="Startup Pitch",
        program_id=program.id,
        event_date=date(2027, 4, 2),
    )
    assert child_event_1.is_standalone is False
    assert child_event_1.program_id == program.id

    # 4. Create Child Event 2 under Program
    child_event_2 = create_event(
        db=db,
        creator=admin,
        organization_id=org.id,
        name="Keynote Conclave",
        program_id=program.id,
        event_date=date(2027, 4, 5),
    )

    # 5. Assign multiple leads to Child Event 1 (D-SLICE3-02)
    lead_user_1 = create_synthetic_user("lead_pitch_1@campus.edu")
    lead_user_2 = create_synthetic_user("lead_pitch_2@campus.edu")

    m1 = OrganizationMembership(organization_id=org.id, user_id=lead_user_1.id, membership_status="active")
    m2 = OrganizationMembership(organization_id=org.id, user_id=lead_user_2.id, membership_status="active")
    db.add_all([m1, m2])
    db.flush()

    assign1 = assign_event_lead(db, admin, org.id, child_event_1.id, m1.id)
    assign2 = assign_event_lead(db, admin, org.id, child_event_1.id, m2.id)

    active_leads = get_active_event_leads(db, child_event_1.id)
    assert len(active_leads) == 2
    assert assign1.id in [l.id for l in active_leads]
    assert assign2.id in [l.id for l in active_leads]


def test_child_event_cannot_own_standalone_department_in_v1(db, verified_org_setup):
    """Verify D-SLICE3-01: child events under a program cannot create standalone departments."""
    org, admin, _ = verified_org_setup

    prog = create_program(db, admin, org.id, "Cultural Fest")
    child_event = create_event(db, admin, org.id, "Dance Night", program_id=prog.id)

    with pytest.raises(ValueError, match="Child events share program departments"):
        create_department(
            db,
            creator=admin,
            organization_id=org.id,
            name="Stage Crew",
            standalone_event_id=child_event.id,
        )


# =========================================================================
# 3. Cross-Tenant Isolation & Scope Integrity
# =========================================================================


def test_cross_tenant_child_event_rejected(db, verified_org_setup, create_synthetic_user):
    """Verify an event in Org A cannot reference a Program in Org B."""
    org_a, admin_a, _ = verified_org_setup

    # Create Org B
    admin_b = create_synthetic_user("admin_b@campus.edu")
    org_b = Organization(college_name="Org B College", club_name="Org B Club", verification_status="verified", created_by_user_id=admin_b.id)
    db.add(org_b)
    db.flush()
    mb = OrganizationMembership(organization_id=org_b.id, user_id=admin_b.id, membership_status="active")
    db.add(mb)
    db.flush()
    db.add(RoleAssignment(membership_id=mb.id, role_name="PRIMARY_ADMIN", scope_type="organization"))
    db.flush()

    prog_b = create_program(db, admin_b, org_b.id, "Org B Program")

    # Attempt to create event in Org A pointing to Program in Org B
    with pytest.raises(ScopeIntegrityError, match="different organization"):
        create_event(db, admin_a, org_a.id, "Alien Event", program_id=prog_b.id)


def test_cross_tenant_department_rejected(db, verified_org_setup, create_synthetic_user):
    """Verify a department in Org A cannot reference a parent in Org B."""
    org_a, admin_a, _ = verified_org_setup

    admin_b = create_synthetic_user("admin_b2@campus.edu")
    org_b = Organization(college_name="Org B2", club_name="Club B2", verification_status="verified", created_by_user_id=admin_b.id)
    db.add(org_b)
    db.flush()
    mb = OrganizationMembership(organization_id=org_b.id, user_id=admin_b.id, membership_status="active")
    db.add(mb)
    db.flush()
    db.add(RoleAssignment(membership_id=mb.id, role_name="PRIMARY_ADMIN", scope_type="organization"))
    db.flush()

    prog_b = create_program(db, admin_b, org_b.id, "Org B2 Program")

    with pytest.raises(ScopeIntegrityError, match="Parent program belongs to a different organization"):
        create_department(db, admin_a, org_a.id, "Alien Dept", program_id=prog_b.id)


def test_cross_tenant_event_lead_assignment_rejected(db, verified_org_setup, create_synthetic_user):
    """Verify an Event Lead cannot be assigned from a foreign organization membership."""
    org_a, admin_a, _ = verified_org_setup

    admin_b = create_synthetic_user("admin_b3@campus.edu")
    org_b = Organization(college_name="Org B3", club_name="Club B3", verification_status="verified", created_by_user_id=admin_b.id)
    db.add(org_b)
    db.flush()

    foreign_member = create_synthetic_user("foreign_student@campus.edu")
    mb_foreign = OrganizationMembership(organization_id=org_b.id, user_id=foreign_member.id, membership_status="active")
    db.add(mb_foreign)
    db.flush()

    event_a = create_event(db, admin_a, org_a.id, "Org A Hackathon")

    with pytest.raises(ScopeIntegrityError, match="Target member belongs to a different organization"):
        assign_event_lead(db, admin_a, org_a.id, event_a.id, mb_foreign.id)


# =========================================================================
# 4. Pending Verification Restrictions & Non-Destructive Archival
# =========================================================================


def test_unverified_organization_cannot_create_operational_entities(db, unverified_org_setup):
    """Verify FPC-02 / FPC-03: privileged operational domain actions are blocked in pending_verification."""
    org, creator, _ = unverified_org_setup

    with pytest.raises(PermissionDeniedError):
        create_program(db, creator, org.id, "Unauthorized Program")

    with pytest.raises(PermissionDeniedError):
        create_event(db, creator, org.id, "Unauthorized Event")


def test_non_destructive_archival_and_mutation_blocking(db, verified_org_setup, create_synthetic_user):
    """Verify D-SLICE3-04: archival is non-destructive, but blocks new operational assignments."""
    org, admin, _ = verified_org_setup

    program = create_program(db, admin, org.id, "Summer Festival")
    child_event = create_event(db, admin, org.id, "Music Fest", program_id=program.id)

    member_user = create_synthetic_user("fest_lead@campus.edu")
    membership = OrganizationMembership(organization_id=org.id, user_id=member_user.id, membership_status="active")
    db.add(membership)
    db.flush()

    # Archive the program non-destructively
    archive_program(db, admin, program.id)
    assert program.is_active() is False
    assert program.archived_at is not None

    # Child event record remains preserved
    db.refresh(child_event)
    assert child_event.name == "Music Fest"

    # But operational mutations targeting the archived hierarchy are rejected
    with pytest.raises(ScopeIntegrityError, match="Parent program is archived or inaccessible"):
        assign_event_lead(db, admin, org.id, child_event.id, membership.id)


# =========================================================================
# 5. Event Lead Authorization Synchronization & Revocation Lifecycle
# =========================================================================


def test_event_lead_synchronization_and_revocation_lifecycle(db, verified_org_setup, create_synthetic_user):
    """
    Verify that EventLeadAssignment creation transactionally grants RoleAssignment,
    and revocation synchronously revokes the role, preventing further authorization.
    """
    org, admin, _ = verified_org_setup
    lead_user = create_synthetic_user("event_lead_sync@campus.edu")
    membership = OrganizationMembership(organization_id=org.id, user_id=lead_user.id, membership_status="active")
    event = create_event(db, admin, org.id, "Esports Cup")
    db.add(membership)
    db.flush()

    # 1. Assign Event Lead
    assignment = assign_event_lead(db, admin, org.id, event.id, membership.id)
    assert assignment.is_active() is True

    # 2. Verify synchronized RoleAssignment exists and grants permission
    role_stmt = select(RoleAssignment).where(
        RoleAssignment.membership_id == membership.id,
        RoleAssignment.role_name == "EVENT_LEAD",
        RoleAssignment.scope_type == "event",
        RoleAssignment.scope_id == event.id,
        RoleAssignment.revoked_at == None,
    )
    role_ra = db.execute(role_stmt).scalar_one_or_none()
    assert role_ra is not None

    # Authorized to review proof within event scope
    assert can_perform(db, lead_user, ACTION_REVIEW_PROOF, org.id, "event", event.id) is True

    # 3. Attempting duplicate active assignment raises DuplicateEventLeadError
    with pytest.raises(DuplicateEventLeadError):
        assign_event_lead(db, admin, org.id, event.id, membership.id)

    # 4. Revoke Event Lead
    revoke_event_lead(db, admin, org.id, assignment.id)
    assert assignment.is_active() is False
    assert assignment.revoked_at is not None

    # Synchronized RoleAssignment must also be revoked
    db.refresh(role_ra)
    assert role_ra.is_active() is False
    assert role_ra.revoked_at is not None

    # Immediately ceases to authorize actions
    assert can_perform(db, lead_user, ACTION_REVIEW_PROOF, org.id, "event", event.id) is False


# =========================================================================
# 6. Scope Validation Helpers for Invitations & Permissions
# =========================================================================


def test_scope_validation_helpers(db, verified_org_setup, create_synthetic_user):
    """Verify domain scope validation helpers correctly validate operational entities and reject invalid ones."""
    org, admin, _ = verified_org_setup

    prog = create_program(db, admin, org.id, "Science Fair")
    event = create_event(db, admin, org.id, "Robotics Challenge", program_id=prog.id)
    dept = create_department(db, admin, org.id, "Evaluation Committee", program_id=prog.id)

    # Positive validations
    assert validate_program_scope_assignment(db, org.id, prog.id).id == prog.id
    assert validate_event_scope_assignment(db, org.id, event.id).id == event.id
    assert validate_department_scope_assignment(db, org.id, dept.id).id == dept.id

    # Nonexistent UUIDs raise Domain NotFound errors
    fake_id = uuid.uuid4()
    with pytest.raises(ProgramNotFoundError):
        validate_program_scope_assignment(db, org.id, fake_id)

    with pytest.raises(EventNotFoundError):
        validate_event_scope_assignment(db, org.id, fake_id)

    with pytest.raises(DepartmentNotFoundError):
        validate_department_scope_assignment(db, org.id, fake_id)
