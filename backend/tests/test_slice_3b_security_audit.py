"""
CampusOps — Slice 3B API Security, Authorization & Transaction Audit Test Suite

Validates:
1. Event scheduling invariants: rejecting end dates without start dates (service & API).
2. Cross-event lead revocation rejection & scope integrity (service & API).
3. Failure injection and atomic rollback on revoke_event_lead.
4. Failure injection and atomic rollback on accept_invitation for EVENT_LEAD.
5. Failure injection and atomic rollback on accept_invitation membership reactivation.
6. Scoped authorization: Event Lead cannot mutate sibling events under the same program.
7. Platform admin tenant boundary: read-only inspection allowed, mutations strictly forbidden (403).
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event, EventLeadAssignment, Program
from app.models.invitation import Invitation
from app.models.organization import Organization, OrganizationMembership
from app.models.role import PlatformAdmin, RoleAssignment
from app.models.user import UserProfile
from app.services.errors import (
    DuplicateEventLeadError,
    EventLeadError,
    PermissionDeniedError,
    ScopeIntegrityError,
)
from app.services.event import (
    assign_event_lead,
    create_event,
    create_program,
    get_active_event_leads,
    revoke_event_lead,
    update_event,
)
from app.services.invitation import accept_invitation, create_invitation
from app.services.organization import create_organization, verify_organization


@pytest.fixture
def audit_fixture(db: Session, create_synthetic_user, create_synthetic_platform_admin):
    """Sets up an audit fixture with verified org, creator admin, and member users."""
    admin = create_synthetic_platform_admin("audit_platform_admin@campusops.internal")
    creator = create_synthetic_user("creator_admin@audit.edu", "Creator Admin")
    org = create_organization(db, creator=creator, college_name="Audit University", club_name="Security Club")
    verify_organization(db, admin_user=admin, organization_id=org.id, decision="verified")

    # Regular workspace member
    member_user = create_synthetic_user("member@audit.edu", "Audit Member")
    member_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=member_user.id,
        membership_status="active",
    )
    db.add(member_mb)
    db.flush()

    return {
        "admin": admin,
        "creator": creator,
        "org": org,
        "member_user": member_user,
        "member_mb": member_mb,
    }


# =========================================================================
# 1. Scheduling Invariants: End Date without Start Date
# =========================================================================

def test_create_event_service_rejects_end_date_without_start_date(db: Session, audit_fixture):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]

    with pytest.raises(ValueError, match="Event end date cannot be specified without an event start date"):
        create_event(
            db=db,
            creator=creator,
            organization_id=org.id,
            name="Invalid End Date Event",
            event_date=None,
            event_end_date=date(2026, 12, 1),
        )


def test_create_event_api_rejects_end_date_without_start_date(client: TestClient, audit_fixture, auth_user):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    auth_user(creator)

    resp = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={
            "name": "Invalid End Date Event API",
            "event_end_date": "2026-12-01",
        },
    )
    assert resp.status_code == 400
    assert "Event end date cannot be specified without an event start date" in resp.json()["detail"]


def test_update_event_service_rejects_end_date_without_start_date(db: Session, audit_fixture):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]

    event = create_event(
        db=db,
        creator=creator,
        organization_id=org.id,
        name="No Date Event",
    )
    assert event.event_date is None
    assert event.event_end_date is None

    with pytest.raises(ValueError, match="Event end date cannot be specified without an event start date"):
        update_event(
            db=db,
            user=creator,
            organization_id=org.id,
            event_id=event.id,
            event_end_date=date(2026, 12, 1),
        )


def test_update_event_api_rejects_end_date_without_start_date(client: TestClient, audit_fixture, auth_user):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    auth_user(creator)

    resp_create = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={"name": "No Date Event For Update"},
    )
    assert resp_create.status_code == 201
    event_id = resp_create.json()["id"]

    resp_update = client.patch(
        f"/api/v1/organizations/{org.id}/events/{event_id}",
        json={"event_end_date": "2026-12-01"},
    )
    assert resp_update.status_code == 400
    assert "Event end date cannot be specified without an event start date" in resp_update.json()["detail"]


# =========================================================================
# 2. Cross-Event Lead Revocation Mismatch & Scope Integrity
# =========================================================================

def test_revoke_event_lead_cross_event_mismatch_service(db: Session, audit_fixture):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    member_mb = audit_fixture["member_mb"]

    ev1 = create_event(db, creator, org.id, "Event One")
    ev2 = create_event(db, creator, org.id, "Event Two")

    assignment = assign_event_lead(db, creator, org.id, ev1.id, member_mb.id)

    # Attempting to revoke assignment of ev1 specifying ev2 as the event_id must fail
    with pytest.raises(ScopeIntegrityError, match="Assignment belongs to a different event"):
        revoke_event_lead(
            db=db,
            revoker=creator,
            organization_id=org.id,
            assignment_id=assignment.id,
            event_id=ev2.id,
        )


def test_revoke_event_lead_cross_event_mismatch_api(client: TestClient, audit_fixture, auth_user, db: Session):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]
    member_mb = audit_fixture["member_mb"]
    auth_user(creator)

    ev1 = create_event(db, creator, org.id, "Event One API")
    ev2 = create_event(db, creator, org.id, "Event Two API")
    assignment = assign_event_lead(db, creator, org.id, ev1.id, member_mb.id)

    # Calling revoke route for Event Two with assignment of Event One
    resp = client.post(
        f"/api/v1/organizations/{org.id}/events/{ev2.id}/leads/{assignment.id}/revoke"
    )
    # Endpoints map ScopeIntegrityError to 404 to prevent resource existence disclosure
    assert resp.status_code == 404


# =========================================================================
# 3. Transaction Rollback & Fault Injection Atomicity
# =========================================================================

def test_revoke_event_lead_atomic_rollback_on_failure(engine):
    """Test rollback atomicity using dedicated session to test uncommitted rollback against committed baseline."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        creator = UserProfile(
            id=uid,
            auth_subject_id=f"sub_{uid.hex[:10]}",
            email_normalized="rb_admin@audit.edu",
            display_name="Admin",
            email_verified_at=now,
            account_status="active",
        )
        s.add(creator)
        org = Organization(
            id=uuid.uuid4(),
            college_name="Audit College",
            club_name="Robo Club",
            created_by_user_id=uid,
            verification_status="verified",
        )
        s.add(org)
        mb = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=uid,
            membership_status="active",
        )
        s.add(mb)
        ra = RoleAssignment(
            id=uuid.uuid4(),
            membership_id=mb.id,
            role_name="PRIMARY_ADMIN",
            scope_type="organization",
            scope_id=org.id,
        )
        s.add(ra)
        ev = Event(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Rollback Event",
            status="published",
            created_by_user_id=uid,
        )
        s.add(ev)
        s.commit()

        assignment = assign_event_lead(s, creator, org.id, ev.id, mb.id)
        assignment_id = assignment.id

        # Inject failure into s.commit during revoke_event_lead
        with patch.object(s, "commit", side_effect=RuntimeError("Simulated DB Crash during revoke")):
            with pytest.raises(RuntimeError, match="Simulated DB Crash during revoke"):
                revoke_event_lead(
                    db=s,
                    revoker=creator,
                    organization_id=org.id,
                    assignment_id=assignment_id,
                    event_id=ev.id,
                )

        # Verify atomic rollback: assignment and role assignment remain active (revoked_at is None)
        reloaded_assignment = s.get(EventLeadAssignment, assignment_id)
        assert reloaded_assignment.revoked_at is None

        role = s.execute(
            select(RoleAssignment).where(
                RoleAssignment.membership_id == mb.id,
                RoleAssignment.role_name == "EVENT_LEAD",
                RoleAssignment.scope_id == ev.id,
            )
        ).scalar_one()
        assert role.revoked_at is None
    finally:
        s.close()


def test_accept_invitation_event_lead_atomic_rollback(engine):
    """Test atomic rollback when an exception occurs during accept_invitation for EVENT_LEAD."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        admin = UserProfile(
            id=uid,
            auth_subject_id=f"sub_{uid.hex[:10]}",
            email_normalized="invite_admin@audit.edu",
            display_name="Admin",
            email_verified_at=now,
            account_status="active",
        )
        s.add(admin)
        org = Organization(
            id=uuid.uuid4(),
            college_name="Audit College",
            club_name="Cyber Club",
            created_by_user_id=uid,
            verification_status="verified",
        )
        s.add(org)
        mb_admin = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=uid,
            membership_status="active",
        )
        s.add(mb_admin)
        ra_admin = RoleAssignment(
            id=uuid.uuid4(),
            membership_id=mb_admin.id,
            role_name="PRIMARY_ADMIN",
            scope_type="organization",
            scope_id=org.id,
        )
        s.add(ra_admin)
        ev = Event(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Invited Lead Event",
            status="published",
            created_by_user_id=uid,
        )
        s.add(ev)
        s.commit()

        invitee_email = "invited_lead@audit.edu"
        res = create_invitation(
            s,
            inviter=admin,
            organization_id=org.id,
            email=invitee_email,
            role_name="EVENT_LEAD",
            scope_type="event",
            scope_id=ev.id,
        )
        raw_token = res.raw_token
        inv_id = res.invitation.id

        invitee = UserProfile(
            id=uuid.uuid4(),
            auth_subject_id=f"sub_{uuid.uuid4().hex[:10]}",
            email_normalized=invitee_email,
            display_name="Invited Lead",
            email_verified_at=now,
            account_status="active",
        )
        s.add(invitee)
        s.commit()

        # Inject failure into s.commit during accept_invitation
        with patch.object(s, "commit", side_effect=RuntimeError("Simulated DB Crash on accept")):
            with pytest.raises(RuntimeError, match="Simulated DB Crash on accept"):
                accept_invitation(s, raw_token=raw_token, accepting_user=invitee)

        # Verify atomic rollback
        inv = s.get(Invitation, inv_id)
        assert inv.status == "pending"
        assert inv.accepted_at is None
        assert inv.accepted_by_user_id is None

        # No membership created
        mb = s.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == invitee.id,
            )
        ).scalar_one_or_none()
        assert mb is None

        # No event lead assignment
        leads = s.execute(
            select(EventLeadAssignment).where(
                EventLeadAssignment.organization_id == org.id,
                EventLeadAssignment.event_id == ev.id,
            )
        ).scalars().all()
        assert len(leads) == 0
    finally:
        s.close()


def test_accept_invitation_reactivation_atomic_rollback(engine):
    """Test atomic rollback when an exception occurs during membership reactivation."""
    s = Session(engine)
    try:
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        admin = UserProfile(
            id=uid,
            auth_subject_id=f"sub_{uid.hex[:10]}",
            email_normalized="react_admin@audit.edu",
            display_name="Admin",
            email_verified_at=now,
            account_status="active",
        )
        s.add(admin)
        org = Organization(
            id=uuid.uuid4(),
            college_name="Audit College",
            club_name="Reactivation Club",
            created_by_user_id=uid,
            verification_status="verified",
        )
        s.add(org)
        mb_admin = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=uid,
            membership_status="active",
        )
        s.add(mb_admin)
        ra_admin = RoleAssignment(
            id=uuid.uuid4(),
            membership_id=mb_admin.id,
            role_name="PRIMARY_ADMIN",
            scope_type="organization",
            scope_id=org.id,
        )
        s.add(ra_admin)

        reactivate_user = UserProfile(
            id=uuid.uuid4(),
            auth_subject_id=f"sub_{uuid.uuid4().hex[:10]}",
            email_normalized="reactivate@audit.edu",
            display_name="Reactivate",
            email_verified_at=now,
            account_status="active",
        )
        s.add(reactivate_user)
        removed_at_time = now - timedelta(days=10)
        old_mb = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=reactivate_user.id,
            membership_status="removed",
            removed_at=removed_at_time,
        )
        s.add(old_mb)
        old_ra = RoleAssignment(
            id=uuid.uuid4(),
            membership_id=old_mb.id,
            role_name="COORDINATOR",
            scope_type="organization",
            scope_id=org.id,
            granted_by_user_id=admin.id,
            revoked_at=None,
        )
        s.add(old_ra)
        s.commit()

        res = create_invitation(
            s,
            inviter=admin,
            organization_id=org.id,
            email="reactivate@audit.edu",
            role_name="OFFICE_BEARER",
            scope_type="organization",
        )
        raw_token = res.raw_token
        inv_id = res.invitation.id

        with patch.object(s, "commit", side_effect=RuntimeError("Commit crash on reactivation")):
            with pytest.raises(RuntimeError, match="Commit crash on reactivation"):
                accept_invitation(s, raw_token=raw_token, accepting_user=reactivate_user)

        # Verify rollback: invitation remains pending, membership remains removed, old role untouched
        inv = s.get(Invitation, inv_id)
        assert inv.status == "pending"

        reloaded_mb = s.get(OrganizationMembership, old_mb.id)
        assert reloaded_mb.membership_status == "removed"
        assert reloaded_mb.removed_at is not None

        reloaded_ra = s.get(RoleAssignment, old_ra.id)
        assert reloaded_ra.revoked_at is None
    finally:
        s.close()


# =========================================================================
# 4. Scoped Authorization: Sibling Event Isolation
# =========================================================================

def test_event_lead_cannot_mutate_sibling_event_in_same_program(
    client: TestClient, audit_fixture, auth_user, db: Session, create_synthetic_user
):
    creator = audit_fixture["creator"]
    org = audit_fixture["org"]

    # 1. Create a parent program and two child events
    prog = create_program(db, creator, org.id, name="Hackfest Program")
    ev1 = create_event(db, creator, org.id, name="Hackfest Day 1", program_id=prog.id)
    ev2 = create_event(db, creator, org.id, name="Hackfest Day 2", program_id=prog.id)

    # 2. Add an eligible member and assign as lead ONLY for Event 1
    lead_user = create_synthetic_user("day1_lead@audit.edu", "Day 1 Lead")
    lead_mb = OrganizationMembership(
        organization_id=org.id,
        user_id=lead_user.id,
        membership_status="active",
    )
    db.add(lead_mb)
    db.flush()
    assign_event_lead(db, creator, org.id, ev1.id, lead_mb.id)

    # 3. Authenticate as Day 1 Lead
    auth_user(lead_user)

    # Can update Event 1 (permitted)
    resp_ev1 = client.patch(
        f"/api/v1/organizations/{org.id}/events/{ev1.id}",
        json={"name": "Hackfest Day 1 - Updated by Lead"},
    )
    assert resp_ev1.status_code == 200
    assert resp_ev1.json()["name"] == "Hackfest Day 1 - Updated by Lead"

    # CANNOT update sibling Event 2 (forbidden)
    resp_ev2 = client.patch(
        f"/api/v1/organizations/{org.id}/events/{ev2.id}",
        json={"name": "Hackfest Day 2 - Unauthorized Mutation"},
    )
    assert resp_ev2.status_code == 403
    assert "denied action" in resp_ev2.json()["detail"]

    # CANNOT assign leads on sibling Event 2 (forbidden)
    resp_assign = client.post(
        f"/api/v1/organizations/{org.id}/events/{ev2.id}/leads",
        json={"membership_id": str(lead_mb.id)},
    )
    assert resp_assign.status_code == 403


# =========================================================================
# 5. Platform Admin Tenant Boundary: Read Inspection vs Mutation
# =========================================================================

def test_platform_admin_cannot_mutate_unjoined_organization(client: TestClient, audit_fixture, auth_user, db: Session):
    admin = audit_fixture["admin"]
    org = audit_fixture["org"]
    creator = audit_fixture["creator"]

    ev = create_event(db, creator, org.id, "Existing Event")

    # Authenticate as Platform Admin (who has NO membership in org)
    auth_user(admin)

    # 1. Inspection (read-only) is permitted for verification / audit
    resp_list_events = client.get(f"/api/v1/organizations/{org.id}/events")
    assert resp_list_events.status_code == 200
    assert len(resp_list_events.json()) == 1

    resp_get_event = client.get(f"/api/v1/organizations/{org.id}/events/{ev.id}")
    assert resp_get_event.status_code == 200
    assert resp_get_event.json()["name"] == "Existing Event"

    # 2. Mutating operations are strictly forbidden (403)
    resp_create_prog = client.post(
        f"/api/v1/organizations/{org.id}/programs",
        json={"name": "Admin Injected Program"},
    )
    assert resp_create_prog.status_code == 403

    resp_create_ev = client.post(
        f"/api/v1/organizations/{org.id}/events",
        json={"name": "Admin Injected Event"},
    )
    assert resp_create_ev.status_code == 403

    resp_update_ev = client.patch(
        f"/api/v1/organizations/{org.id}/events/{ev.id}",
        json={"name": "Admin Hijacked Event"},
    )
    assert resp_update_ev.status_code == 403

    resp_archive_ev = client.post(
        f"/api/v1/organizations/{org.id}/events/{ev.id}/archive"
    )
    assert resp_archive_ev.status_code == 403
