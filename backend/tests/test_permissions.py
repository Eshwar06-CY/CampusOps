import uuid
import pytest

from app.models.event import Department, Event
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.services.errors import PermissionDeniedError
from app.services.permissions import (
    ACTION_EDIT_ORG_PROFILE,
    ACTION_MANAGE_DEPARTMENT,
    ACTION_REVIEW_PROOF,
    ACTION_SUBMIT_PROOF,
    ACTION_VIEW_DEPARTMENT,
    ACTION_VIEW_ORG_PROFILE,
    ACTION_VERIFY_ORG,
    can_perform,
    is_active_platform_admin,
    require_permission,
)


def test_deny_by_default_without_role(db, create_synthetic_user):
    """Verify any action without an explicit role grant is denied by default."""
    user = create_synthetic_user("random@campus.edu")
    org_id = uuid.uuid4()

    assert can_perform(db, user, ACTION_VIEW_ORG_PROFILE, org_id) is False
    with pytest.raises(PermissionDeniedError):
        require_permission(db, user, ACTION_VIEW_ORG_PROFILE, org_id)


def test_cross_organization_tenant_isolation(db, create_synthetic_user):
    """Verify user in Organization A cannot access resources in Organization B."""
    user_a = create_synthetic_user("user_a@campus.edu")
    user_b = create_synthetic_user("user_b@campus.edu")

    org_a = Organization(college_name="College A", club_name="Club A", created_by_user_id=user_a.id)
    org_b = Organization(college_name="College B", club_name="Club B", created_by_user_id=user_b.id)
    db.add_all([org_a, org_b])
    db.flush()

    m_a = OrganizationMembership(organization_id=org_a.id, user_id=user_a.id)
    m_b = OrganizationMembership(organization_id=org_b.id, user_id=user_b.id)
    db.add_all([m_a, m_b])
    db.flush()

    r_a = RoleAssignment(membership_id=m_a.id, role_name="PRIMARY_ADMIN", scope_type="organization")
    r_b = RoleAssignment(membership_id=m_b.id, role_name="PRIMARY_ADMIN", scope_type="organization")
    db.add_all([r_a, r_b])
    db.flush()

    # User A has access to Org A, but denied on Org B
    assert can_perform(db, user_a, ACTION_VIEW_ORG_PROFILE, org_a.id) is True
    assert can_perform(db, user_a, ACTION_VIEW_ORG_PROFILE, org_b.id) is False
    assert can_perform(db, user_a, ACTION_EDIT_ORG_PROFILE, org_b.id) is False

    with pytest.raises(PermissionDeniedError):
        require_permission(db, user_a, ACTION_EDIT_ORG_PROFILE, org_b.id)


def test_department_scoped_role_does_not_leak_across_departments(db, create_synthetic_user):
    """Verify department lead permissions are strictly confined to the assigned department."""
    lead = create_synthetic_user("lead@campus.edu")
    org = Organization(college_name="College", club_name="Club", verification_status="verified", created_by_user_id=lead.id)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(organization_id=org.id, user_id=lead.id)
    db.add(membership)
    db.flush()

    event = Event(organization_id=org.id, name="Annual Fest", created_by_user_id=lead.id)
    db.add(event)
    db.flush()

    dept_1 = Department(
        organization_id=org.id,
        standalone_event_id=event.id,
        name="Logistics",
        created_by_user_id=lead.id,
    )
    dept_2 = Department(
        organization_id=org.id,
        standalone_event_id=event.id,
        name="Sponsorship",
        created_by_user_id=lead.id,
    )
    db.add_all([dept_1, dept_2])
    db.flush()

    dept_1_id = dept_1.id
    dept_2_id = dept_2.id

    # Grant Department Lead on Dept 1 only
    dept_assignment = RoleAssignment(
        membership_id=membership.id,
        role_name="DEPARTMENT_LEAD",
        scope_type="department",
        scope_id=dept_1_id,
    )
    db.add(dept_assignment)
    db.flush()

    # Permitted on Dept 1
    assert can_perform(db, lead, ACTION_VIEW_DEPARTMENT, org.id, "department", dept_1_id) is True
    assert can_perform(db, lead, ACTION_MANAGE_DEPARTMENT, org.id, "department", dept_1_id) is True
    assert can_perform(db, lead, ACTION_REVIEW_PROOF, org.id, "department", dept_1_id) is True

    # Strictly denied on Dept 2 (no scope leakage!)
    assert can_perform(db, lead, ACTION_VIEW_DEPARTMENT, org.id, "department", dept_2_id) is False
    assert can_perform(db, lead, ACTION_MANAGE_DEPARTMENT, org.id, "department", dept_2_id) is False
    assert can_perform(db, lead, ACTION_REVIEW_PROOF, org.id, "department", dept_2_id) is False

    with pytest.raises(PermissionDeniedError):
        require_permission(db, lead, ACTION_MANAGE_DEPARTMENT, org.id, "department", dept_2_id)


def test_event_scoped_role_does_not_leak_across_events(db, create_synthetic_user):
    """Verify event lead permissions are strictly confined to the assigned event."""
    lead = create_synthetic_user("event_lead@campus.edu")
    org = Organization(college_name="College", club_name="Club", verification_status="verified", created_by_user_id=lead.id)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(organization_id=org.id, user_id=lead.id)
    db.add(membership)
    db.flush()

    event_1 = Event(organization_id=org.id, name="Event 1", created_by_user_id=lead.id)
    event_2 = Event(organization_id=org.id, name="Event 2", created_by_user_id=lead.id)
    db.add_all([event_1, event_2])
    db.flush()

    event_1_id = event_1.id
    event_2_id = event_2.id

    # Grant Event Lead on Event 1
    event_assignment = RoleAssignment(
        membership_id=membership.id,
        role_name="EVENT_LEAD",
        scope_type="event",
        scope_id=event_1_id,
    )
    db.add(event_assignment)
    db.flush()

    assert can_perform(db, lead, ACTION_REVIEW_PROOF, org.id, "event", event_1_id) is True
    assert can_perform(db, lead, ACTION_REVIEW_PROOF, org.id, "event", event_2_id) is False

    with pytest.raises(PermissionDeniedError):
        require_permission(db, lead, ACTION_REVIEW_PROOF, org.id, "event", event_2_id)


def test_suspended_user_denied_all_actions(db, create_synthetic_user):
    """Verify suspended or inactive users cannot retain access through existing roles."""
    user = create_synthetic_user("suspended@campus.edu")
    org = Organization(college_name="College", club_name="Club", verification_status="verified", created_by_user_id=user.id)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(organization_id=org.id, user_id=user.id, membership_status="active")
    db.add(membership)
    db.flush()

    role = RoleAssignment(membership_id=membership.id, role_name="PRIMARY_ADMIN", scope_type="organization")
    db.add(role)
    db.flush()

    assert can_perform(db, user, ACTION_VIEW_ORG_PROFILE, org.id) is True

    # Suspend user account
    user.account_status = "suspended"
    db.flush()

    assert can_perform(db, user, ACTION_VIEW_ORG_PROFILE, org.id) is False
    with pytest.raises(PermissionDeniedError):
        require_permission(db, user, ACTION_VIEW_ORG_PROFILE, org.id)


def test_unverified_email_user_denied_actions(db, create_synthetic_user):
    """Verify user with unverified email cannot perform organization operations."""
    user = create_synthetic_user("unverified@campus.edu")
    user.email_verified_at = None
    db.flush()

    org = Organization(college_name="College", club_name="Club", verification_status="verified", created_by_user_id=user.id)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(organization_id=org.id, user_id=user.id, membership_status="active")
    db.add(membership)
    db.flush()

    role = RoleAssignment(membership_id=membership.id, role_name="PRIMARY_ADMIN", scope_type="organization")
    db.add(role)
    db.flush()

    assert can_perform(db, user, ACTION_VIEW_ORG_PROFILE, org.id) is False


def test_suspended_platform_admin_denied_verification(db, create_synthetic_platform_admin):
    """Verify platform admin whose user account is suspended cannot verify organizations."""
    admin_user = create_synthetic_platform_admin("platform_admin_susp@campusops.internal")
    assert is_active_platform_admin(db, admin_user.id) is True
    assert can_perform(db, admin_user, ACTION_VERIFY_ORG) is True

    # Suspend user
    admin_user.account_status = "suspended"
    db.flush()

    assert is_active_platform_admin(db, admin_user.id) is False
    assert can_perform(db, admin_user, ACTION_VERIFY_ORG) is False


def test_invalid_target_resource_scope_rejected(db, create_synthetic_user):
    """Verify malformed target scopes are strictly rejected."""
    user = create_synthetic_user("scoped_user@campus.edu")
    org = Organization(college_name="College", club_name="Club", verification_status="verified", created_by_user_id=user.id)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(organization_id=org.id, user_id=user.id)
    db.add(membership)
    db.flush()

    role = RoleAssignment(membership_id=membership.id, role_name="PRIMARY_ADMIN", scope_type="organization")
    db.add(role)
    db.flush()

    # Organization scope with an alien scope_id must be rejected
    assert can_perform(db, user, ACTION_VIEW_ORG_PROFILE, org.id, scope_type="organization", scope_id=uuid.uuid4()) is False

    # Department scope with None scope_id must be rejected
    assert can_perform(db, user, ACTION_VIEW_DEPARTMENT, org.id, scope_type="department", scope_id=None) is False
