"""
CampusOps — Slice 3A Database Integrity and Lifecycle Audit Test Suite

Validates database-enforced cross-tenant integrity constraints (composite foreign keys),
date/time sequencing check constraints, status/archival check constraints,
event-lead user eligibility, and transaction rollback / fault injection atomicity.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Department, Event, EventLeadAssignment, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.services.errors import (
    EventLeadError,
    PermissionDeniedError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.event import (
    archive_event,
    archive_program,
    assign_event_lead,
    create_department,
    create_event,
    create_program,
    revoke_event_lead,
)
from app.services.permissions import (
    ACTION_CREATE_EVENT,
    ACTION_REVIEW_PROOF,
    can_perform,
)


def create_verified_user(db: Session, email: str, account_status: str = "active", email_verified: bool = True) -> UserProfile:
    user = UserProfile(
        auth_subject_id=f"auth0|{uuid.uuid4().hex[:12]}",
        email_normalized=email.lower().strip(),
        display_name=f"User {email}",
        account_status=account_status,
        email_verified_at=datetime.now(timezone.utc) if email_verified else None,
    )
    db.add(user)
    db.flush()
    return user


def create_test_org(db: Session, creator: UserProfile, club_name: str, verified: bool = True) -> Organization:
    org = Organization(
        college_name="Engineering College",
        club_name=club_name,
        created_by_user_id=creator.id,
        verification_status="verified" if verified else "pending_verification",
    )
    db.add(org)
    db.flush()
    mb = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        membership_status="active",
    )
    db.add(mb)
    db.flush()
    ra = RoleAssignment(
        membership_id=mb.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
        scope_id=org.id,
        granted_by_user_id=creator.id,
    )
    db.add(ra)
    db.flush()
    return org


# =========================================================================
# 1. Direct Database Cross-Tenant Insert Tests (Bypassing Services)
# =========================================================================

def test_db_blocks_cross_tenant_child_event_insert(db: Session):
    """Direct DB insert of an event referencing a foreign org's program must fail via composite FK."""
    admin1 = create_verified_user(db, "admin1@org1.edu")
    admin2 = create_verified_user(db, "admin2@org2.edu")
    org1 = create_test_org(db, admin1, "Club 1")
    org2 = create_test_org(db, admin2, "Club 2")

    prog2 = Program(
        organization_id=org2.id,
        name="Program in Org 2",
        created_by_user_id=admin2.id,
    )
    db.add(prog2)
    db.flush()

    org1_id = org1.id
    prog2_id = prog2.id
    admin1_id = admin1.id

    # Attempt direct DB insert inside a savepoint: event in org1 referencing prog2 in org2
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_event = Event(
                organization_id=org1_id,
                program_id=prog2_id,
                name="Cross-tenant Child Event",
                created_by_user_id=admin1_id,
            )
            db.add(bad_event)
            db.flush()


def test_db_blocks_cross_tenant_department_inserts(db: Session):
    """Direct DB inserts of departments referencing foreign programs or events must fail via composite FKs."""
    admin1 = create_verified_user(db, "admin1_dept@org1.edu")
    admin2 = create_verified_user(db, "admin2_dept@org2.edu")
    org1 = create_test_org(db, admin1, "Club 1 Dept")
    org2 = create_test_org(db, admin2, "Club 2 Dept")

    prog2 = Program(
        organization_id=org2.id,
        name="Program in Org 2",
        created_by_user_id=admin2.id,
    )
    ev2 = Event(
        organization_id=org2.id,
        name="Standalone Event in Org 2",
        created_by_user_id=admin2.id,
    )
    db.add_all([prog2, ev2])
    db.flush()

    org1_id = org1.id
    prog2_id = prog2.id
    ev2_id = ev2.id
    admin1_id = admin1.id

    # 1. Department in org1 referencing prog2 in org2
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_dept1 = Department(
                organization_id=org1_id,
                program_id=prog2_id,
                standalone_event_id=None,
                name="Foreign Program Dept",
                created_by_user_id=admin1_id,
            )
            db.add(bad_dept1)
            db.flush()

    # 2. Department in org1 referencing ev2 in org2
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_dept2 = Department(
                organization_id=org1_id,
                program_id=None,
                standalone_event_id=ev2_id,
                name="Foreign Event Dept",
                created_by_user_id=admin1_id,
            )
            db.add(bad_dept2)
            db.flush()


def test_db_blocks_cross_tenant_event_lead_assignment_inserts(db: Session):
    """Direct DB inserts of lead assignments referencing foreign events or foreign memberships must fail."""
    admin1 = create_verified_user(db, "admin1_lead@org1.edu")
    admin2 = create_verified_user(db, "admin2_lead@org2.edu")
    org1 = create_test_org(db, admin1, "Club 1 Leads")
    org2 = create_test_org(db, admin2, "Club 2 Leads")

    user_m1 = create_verified_user(db, "member1@org1.edu")
    user_m2 = create_verified_user(db, "member2@org2.edu")

    mb1 = OrganizationMembership(organization_id=org1.id, user_id=user_m1.id, membership_status="active")
    mb2 = OrganizationMembership(organization_id=org2.id, user_id=user_m2.id, membership_status="active")
    db.add_all([mb1, mb2])
    db.flush()

    ev1 = Event(organization_id=org1.id, name="Event in Org 1", created_by_user_id=admin1.id)
    ev2 = Event(organization_id=org2.id, name="Event in Org 2", created_by_user_id=admin2.id)
    db.add_all([ev1, ev2])
    db.flush()

    org1_id = org1.id
    mb1_id = mb1.id
    mb2_id = mb2.id
    ev1_id = ev1.id
    ev2_id = ev2.id
    admin1_id = admin1.id

    # 1. Lead in org1 referencing ev2 in org2 (foreign event)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_lead1 = EventLeadAssignment(
                organization_id=org1_id,
                event_id=ev2_id,
                membership_id=mb1_id,
                assigned_by_user_id=admin1_id,
            )
            db.add(bad_lead1)
            db.flush()

    # 2. Lead in org1 referencing mb2 in org2 (foreign membership)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_lead2 = EventLeadAssignment(
                organization_id=org1_id,
                event_id=ev1_id,
                membership_id=mb2_id,
                assigned_by_user_id=admin1_id,
            )
            db.add(bad_lead2)
            db.flush()


# =========================================================================
# 2. Date/Time Sequencing & Archival Status Check Constraints
# =========================================================================

def test_db_enforces_event_time_sequencing(db: Session):
    """Event with planned_end_time < planned_start_time must be rejected by check constraint ck_events_time_order."""
    admin = create_verified_user(db, "time_admin@org.edu")
    org = create_test_org(db, admin, "Time Org")

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=2)

    # 1. Service validation
    with pytest.raises(ValueError, match="Planned end time cannot be earlier than planned start time"):
        create_event(
            db,
            creator=admin,
            organization_id=org.id,
            name="Inverted Time Event",
            planned_start_time=now,
            planned_end_time=earlier,
        )

    # 2. Direct DB insert bypassing service
    org_id = org.id
    admin_id = admin.id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_event = Event(
                organization_id=org_id,
                name="Direct Inverted Time Event",
                planned_start_time=now,
                planned_end_time=earlier,
                created_by_user_id=admin_id,
            )
            db.add(bad_event)
            db.flush()


def test_db_enforces_program_date_sequencing(db: Session):
    """Program with planned_end_date < planned_start_date must be rejected by check constraint ck_programs_date_order."""
    admin = create_verified_user(db, "date_admin@org.edu")
    org = create_test_org(db, admin, "Date Org")

    today = date(2026, 11, 10)
    yesterday = date(2026, 11, 9)

    # 1. Service validation
    with pytest.raises(ValueError, match="Planned end date cannot be earlier than planned start date"):
        create_program(
            db,
            creator=admin,
            organization_id=org.id,
            name="Inverted Date Program",
            planned_start_date=today,
            planned_end_date=yesterday,
        )

    # 2. Direct DB insert bypassing service
    org_id = org.id
    admin_id = admin.id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            bad_prog = Program(
                organization_id=org_id,
                name="Direct Inverted Date Program",
                planned_start_date=today,
                planned_end_date=yesterday,
                created_by_user_id=admin_id,
            )
            db.add(bad_prog)
            db.flush()


def test_db_enforces_status_archived_consistency(db: Session):
    """Database check constraints prevent status='archived' with archived_at=NULL or vice versa."""
    admin = create_verified_user(db, "arch_admin@org.edu")
    org = create_test_org(db, admin, "Archived Org")
    org_id = org.id
    admin_id = admin.id

    # 1. Event: status='archived' but archived_at is None
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ev1 = Event(
                organization_id=org_id,
                name="Contradictory Event 1",
                status="archived",
                archived_at=None,
                created_by_user_id=admin_id,
            )
            db.add(ev1)
            db.flush()

    # 2. Event: status='draft' but archived_at is set
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ev2 = Event(
                organization_id=org_id,
                name="Contradictory Event 2",
                status="draft",
                archived_at=datetime.now(timezone.utc),
                created_by_user_id=admin_id,
            )
            db.add(ev2)
            db.flush()

    # 3. Department: status='archived' but archived_at is None
    ev_valid = Event(organization_id=org_id, name="Valid Event", created_by_user_id=admin_id)
    db.add(ev_valid)
    db.flush()
    ev_valid_id = ev_valid.id

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            dept1 = Department(
                organization_id=org_id,
                standalone_event_id=ev_valid_id,
                name="Contradictory Dept",
                status="archived",
                archived_at=None,
                created_by_user_id=admin_id,
            )
            db.add(dept1)
            db.flush()


# =========================================================================
# 3. Event-Lead Eligibility and Rollback Atomicity
# =========================================================================

def test_assign_event_lead_rejects_suspended_or_unverified_member(db: Session):
    """Assigning event lead must reject members whose user account is suspended or email unverified."""
    admin = create_verified_user(db, "el_admin@org.edu")
    org = create_test_org(db, admin, "Lead Eligibility Org")
    event = create_event(db, admin, org.id, "Lead Eligibility Event")

    # 1. Suspended user
    suspended_user = create_verified_user(db, "suspended_lead@org.edu", account_status="suspended")
    mb_susp = OrganizationMembership(organization_id=org.id, user_id=suspended_user.id, membership_status="active")
    db.add(mb_susp)
    db.flush()

    with pytest.raises(EventLeadError, match="Target member user account is not active or email is unverified"):
        assign_event_lead(db, admin, org.id, event.id, mb_susp.id)

    # 2. Unverified email user
    unverified_user = create_verified_user(db, "unverified_lead@org.edu", account_status="active", email_verified=False)
    mb_unver = OrganizationMembership(organization_id=org.id, user_id=unverified_user.id, membership_status="active")
    db.add(mb_unver)
    db.flush()

    with pytest.raises(EventLeadError, match="Target member user account is not active or email is unverified"):
        assign_event_lead(db, admin, org.id, event.id, mb_unver.id)


def test_assign_event_lead_transaction_rollback_on_failure(db: Session):
    """Simulated database or commit failure during assign_event_lead must roll back both records."""
    admin = create_verified_user(db, "rb_admin@org.edu")
    org = create_test_org(db, admin, "Rollback Org")
    event = create_event(db, admin, org.id, "Rollback Event")
    lead_user = create_verified_user(db, "rb_lead@org.edu")
    mb = OrganizationMembership(organization_id=org.id, user_id=lead_user.id, membership_status="active")
    db.add(mb)
    db.flush()

    org_id = org.id
    event_id = event.id
    mb_id = mb.id

    # Inject failure into db.commit
    with patch.object(db, "commit", side_effect=RuntimeError("Simulated DB Crash")):
        with pytest.raises(RuntimeError, match="Simulated DB Crash"):
            assign_event_lead(db, admin, org_id, event_id, mb_id)

    # Verify that neither EventLeadAssignment nor RoleAssignment was persisted
    lead_rows = db.execute(select(EventLeadAssignment).where(EventLeadAssignment.event_id == event_id)).scalars().all()
    assert len(lead_rows) == 0

    role_rows = db.execute(
        select(RoleAssignment).where(
            RoleAssignment.membership_id == mb_id,
            RoleAssignment.role_name == "EVENT_LEAD"
        )
    ).scalars().all()
    assert len(role_rows) == 0


def test_archiving_event_ceases_lead_scoped_authority(db: Session):
    """When an event is archived, assigned event leads immediately lose permission to perform scoped actions."""
    admin = create_verified_user(db, "cease_admin@org.edu")
    org = create_test_org(db, admin, "Cease Authority Org")
    event = create_event(db, admin, org.id, "Lead Authority Event")
    lead_user = create_verified_user(db, "active_lead@org.edu")
    mb = OrganizationMembership(organization_id=org.id, user_id=lead_user.id, membership_status="active")
    db.add(mb)
    db.flush()

    assign_event_lead(db, admin, org.id, event.id, mb.id)

    # Before archival: lead can perform event actions
    assert can_perform(
        db,
        user=lead_user,
        action=ACTION_REVIEW_PROOF,
        organization_id=org.id,
        scope_type="event",
        scope_id=event.id,
    ) is True

    # Archive the event
    archive_event(db, admin, event.id)

    # After archival: lead can no longer perform actions on the archived event
    assert can_perform(
        db,
        user=lead_user,
        action=ACTION_REVIEW_PROOF,
        organization_id=org.id,
        scope_type="event",
        scope_id=event.id,
    ) is False


def test_event_timezone_persisted_and_default(db: Session):
    """Event model explicitly persists timezone with Asia/Kolkata default."""
    admin = create_verified_user(db, "tz_admin@org.edu")
    org = create_test_org(db, admin, "Timezone Org")

    event_default = create_event(db, admin, org.id, "Default TZ Event")
    assert event_default.timezone == "Asia/Kolkata"

    event_custom = create_event(db, admin, org.id, "Custom TZ Event", timezone_name="UTC")
    assert event_custom.timezone == "UTC"
