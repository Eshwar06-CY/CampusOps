import pytest

from app.services.errors import OrganizationVerificationError, PermissionDeniedError
from app.services.organization import (
    create_organization,
    get_organization,
    verify_organization,
)
from app.services.permissions import (
    ACTION_CREATE_EVENT,
    ACTION_EDIT_ORG_PROFILE,
    ACTION_INVITE_MEMBER,
    ACTION_VIEW_ORG_PROFILE,
    can_perform,
    has_active_primary_admin,
    require_permission,
)
from app.services.platform import appoint_platform_admin


def test_organization_creation_sets_pending_and_primary_admin(db, create_synthetic_user):
    """Verify organization starts in pending_verification and creator is Primary Admin."""
    creator = create_synthetic_user("creator@campus.edu", "Org Creator")
    org = create_organization(
        db,
        creator=creator,
        college_name="Engineering College",
        club_name="ACM Student Chapter",
    )

    assert org.id is not None
    assert org.verification_status == "pending_verification"
    assert org.created_by_user_id == creator.id

    # Verify creator has membership and Primary Admin role
    assert len(org.memberships) == 1
    membership = org.memberships[0]
    assert membership.user_id == creator.id
    assert membership.membership_status == "active"
    assert len(membership.role_assignments) == 1
    role_assignment = membership.role_assignments[0]
    assert role_assignment.role_name == "PRIMARY_ADMIN"
    assert role_assignment.scope_type == "organization"


def test_creator_has_limited_permissions_in_pending_verification(db, create_synthetic_user):
    """Verify creator can view/edit profile but cannot create events or invite members before verification."""
    creator = create_synthetic_user("creator2@campus.edu", "Org Creator 2")
    org = create_organization(
        db,
        creator=creator,
        college_name="Medical College",
        club_name="Bio Club",
    )

    # Allowed actions in pending_verification
    assert can_perform(db, creator, ACTION_VIEW_ORG_PROFILE, org.id) is True
    assert can_perform(db, creator, ACTION_EDIT_ORG_PROFILE, org.id) is True

    # Restricted actions in pending_verification (FPC-02, FPC-03)
    assert can_perform(db, creator, ACTION_CREATE_EVENT, org.id) is False
    assert can_perform(db, creator, ACTION_INVITE_MEMBER, org.id) is False

    with pytest.raises(PermissionDeniedError):
        require_permission(db, creator, ACTION_CREATE_EVENT, org.id)

    with pytest.raises(PermissionDeniedError):
        require_permission(db, creator, ACTION_INVITE_MEMBER, org.id)


def test_verification_rejected_if_not_platform_admin(db, create_synthetic_user):
    """Verify non-platform administrators cannot verify or reject an organization."""
    creator = create_synthetic_user("creator3@campus.edu")
    unauthorized_user = create_synthetic_user("stranger@campus.edu")
    org = create_organization(db, creator, "Law College", "Moot Court")

    with pytest.raises(PermissionDeniedError):
        verify_organization(
            db,
            admin_user=unauthorized_user,
            organization_id=org.id,
            decision="verified",
        )


def test_verification_rejection_requires_reason(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify rejecting an organization requires a documented reason."""
    creator = create_synthetic_user("creator4@campus.edu")
    admin = create_synthetic_platform_admin("admin1@campusops.internal")
    org = create_organization(db, creator, "Science College", "Physics Club")

    # Rejection without note must fail
    with pytest.raises(OrganizationVerificationError, match="requires a documented reason"):
        verify_organization(
            db,
            admin_user=admin,
            organization_id=org.id,
            decision="rejected",
            note="",
        )


def test_successful_verification_by_platform_admin_unblocks_permissions(
    db, create_synthetic_user, create_synthetic_platform_admin
):
    """Verify platform admin can approve organization, enabling creator's full admin capabilities."""
    creator = create_synthetic_user("creator5@campus.edu")
    admin = create_synthetic_platform_admin("admin2@campusops.internal")
    org = create_organization(db, creator, "Commerce College", "Finance Club")

    # Verify organization
    verified_org = verify_organization(
        db,
        admin_user=admin,
        organization_id=org.id,
        decision="verified",
        note="Official university faculty confirmation verified.",
    )

    assert verified_org.verification_status == "verified"
    assert verified_org.verification_reviewer_id == admin.id
    assert verified_org.verification_reviewed_at is not None
    assert verified_org.verification_note == "Official university faculty confirmation verified."

    # Now creator can invite members and create events!
    assert can_perform(db, creator, ACTION_INVITE_MEMBER, org.id) is True
    assert can_perform(db, creator, ACTION_CREATE_EVENT, org.id) is True


def test_organization_creation_rejected_for_unverified_or_suspended_creator(db, create_synthetic_user):
    """Verify organization creation requires an active creator with a verified email."""
    # 1. Unverified email
    unverified_creator = create_synthetic_user("unverified_creator@campus.edu")
    unverified_creator.email_verified_at = None
    db.flush()

    with pytest.raises(OrganizationVerificationError, match="email must be verified"):
        create_organization(db, unverified_creator, "College A", "Club A")

    # 2. Suspended creator
    suspended_creator = create_synthetic_user("suspended_creator@campus.edu")
    suspended_creator.account_status = "suspended"
    db.flush()

    with pytest.raises(OrganizationVerificationError, match="account must be active"):
        create_organization(db, suspended_creator, "College B", "Club B")


def test_organization_has_active_primary_admin_invariant(db, create_synthetic_user):
    """Verify organization has exactly one Primary Administrator tracked by transactional helper."""
    creator = create_synthetic_user("admin_inv@campus.edu")
    org = create_organization(db, creator, "College", "Invariant Club")

    # The organization creator is the active Primary Admin
    assert has_active_primary_admin(db, org.id) is True


def test_platform_admin_bootstrap_and_appointment_lifecycle(db, create_synthetic_user):
    """
    Verify safe bootstrap of the initial platform admin and strict enforcement
    that subsequent appointments require an active platform admin.
    """
    initial_user = create_synthetic_user("first_admin@campusops.internal")
    second_user = create_synthetic_user("second_admin@campusops.internal")
    unauthorized_user = create_synthetic_user("regular_user@campus.edu")

    # 1. Initial bootstrap succeeds without an appointing admin
    first_admin = appoint_platform_admin(
        db,
        target_user=initial_user,
        appointing_admin=None,
        notes="First platform administrator bootstrap",
    )
    assert first_admin.user_id == initial_user.id
    assert first_admin.is_active is True

    # 2. Subsequent appointment without an appointing admin is rejected
    with pytest.raises(PermissionDeniedError, match="Appointing administrator is required"):
        appoint_platform_admin(db, target_user=second_user, appointing_admin=None)

    # 3. Subsequent appointment by a non-platform admin is rejected
    with pytest.raises(PermissionDeniedError, match="Only an active platform administrator"):
        appoint_platform_admin(
            db, target_user=second_user, appointing_admin=unauthorized_user
        )

    # 4. Subsequent appointment by the active platform admin succeeds
    second_admin = appoint_platform_admin(
        db,
        target_user=second_user,
        appointing_admin=initial_user,
        notes="Appointed by initial platform admin",
    )
    assert second_admin.user_id == second_user.id
    assert second_admin.appointed_by_user_id == initial_user.id

    # 5. Appointing an inactive user fails
    inactive_user = create_synthetic_user("inactive@campus.edu")
    inactive_user.account_status = "suspended"
    db.flush()

    with pytest.raises(ValueError, match="must have an active account"):
        appoint_platform_admin(
            db, target_user=inactive_user, appointing_admin=initial_user
        )
