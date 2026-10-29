import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, update

from app.models.invitation import Invitation
from app.models.organization import OrganizationMembership
from app.models.role import RoleAssignment
from app.services.errors import (
    DuplicateMembershipError,
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationInvalidError,
    InvitationNotFoundError,
    PermissionDeniedError,
)
from app.services.invitation import (
    accept_invitation,
    create_invitation,
    hash_token,
    revoke_invitation,
)
from app.services.organization import create_organization, verify_organization


def test_invitation_lifecycle_success(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify invitation creation, token hashing, 7-day expiry, and successful acceptance."""
    creator = create_synthetic_user("creator@campus.edu")
    admin = create_synthetic_platform_admin("admin@campusops.internal")
    org = create_organization(db, creator, "Tech University", "Robotics Club")
    verify_organization(db, admin, org.id, "verified")

    # 1. Create invitation
    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="new_lead@campus.edu",
        role_name="OFFICE_BEARER",
        scope_type="organization",
    )
    raw_token = result.raw_token
    invitation = result.invitation

    assert raw_token is not None
    assert len(raw_token) >= 32
    assert invitation.token_hash == hash_token(raw_token)
    assert invitation.status == "pending"

    # Verify 7-day expiry (FA-009)
    time_diff = invitation.expires_at - invitation.created_at
    assert abs(time_diff.total_seconds() - 7 * 86400) < 5

    # Verify raw token is NOT in database
    db_invitation = db.get(Invitation, invitation.id)
    assert not hasattr(db_invitation, "raw_token")
    assert db_invitation.token_hash != raw_token
    assert db_invitation.token_hash == hash_token(raw_token)

    # 2. Accept invitation with matching user
    invitee = create_synthetic_user("new_lead@campus.edu", "New Department Lead")
    membership = accept_invitation(db, raw_token=raw_token, accepting_user=invitee)

    assert membership.user_id == invitee.id
    assert membership.organization_id == org.id
    assert membership.membership_status == "active"

    # Verify role assignment created
    roles = list(db.execute(select(RoleAssignment).where(RoleAssignment.membership_id == membership.id)).scalars().all())
    assert len(roles) == 1
    assert roles[0].role_name == "OFFICE_BEARER"

    # Verify invitation state updated
    db.refresh(invitation)
    assert invitation.status == "accepted"
    assert invitation.accepted_by_user_id == invitee.id
    assert invitation.accepted_at is not None


def test_invitation_creation_blocked_for_unverified_organization(db, create_synthetic_user):
    """Verify team member invitations are blocked while organization is pending_verification."""
    creator = create_synthetic_user("creator_pending@campus.edu")
    org = create_organization(db, creator, "College", "Pending Club")

    with pytest.raises(PermissionDeniedError):
        create_invitation(
            db,
            inviter=creator,
            organization_id=org.id,
            email="invitee@campus.edu",
            role_name="COORDINATOR",
        )


def test_invitation_email_mismatch_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify accepting user's email must match the invitation's email_normalized."""
    creator = create_synthetic_user("creator_m@campus.edu")
    admin = create_synthetic_platform_admin("admin_m@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="intended@campus.edu",
        role_name="COORDINATOR",
    )

    different_user = create_synthetic_user("imposter@campus.edu")
    with pytest.raises(InvitationEmailMismatchError, match="not 'imposter@campus.edu'"):
        accept_invitation(db, raw_token=result.raw_token, accepting_user=different_user)


def test_expired_invitation_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify invitation past its 7-day expiry cannot be accepted (FA-009)."""
    creator = create_synthetic_user("creator_exp@campus.edu")
    admin = create_synthetic_platform_admin("admin_exp@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="exp_user@campus.edu",
        role_name="COORDINATOR",
    )

    # Force expiration back into the past
    result.invitation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    invitee = create_synthetic_user("exp_user@campus.edu")
    with pytest.raises(InvitationExpiredError):
        accept_invitation(db, raw_token=result.raw_token, accepting_user=invitee)

    db.refresh(result.invitation)
    assert result.invitation.status == "expired"


def test_revoked_invitation_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify revoked invitation cannot be accepted."""
    creator = create_synthetic_user("creator_rev@campus.edu")
    admin = create_synthetic_platform_admin("admin_rev@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="rev_user@campus.edu",
        role_name="COORDINATOR",
    )

    # Revoke invitation
    revoke_invitation(db, revoker=creator, invitation_id=result.invitation.id)

    invitee = create_synthetic_user("rev_user@campus.edu")
    with pytest.raises(InvitationInvalidError, match="revoked"):
        accept_invitation(db, raw_token=result.raw_token, accepting_user=invitee)


def test_replayed_invitation_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify replaying an already accepted invitation is rejected (single-use guarantee)."""
    creator = create_synthetic_user("creator_replay@campus.edu")
    admin = create_synthetic_platform_admin("admin_replay@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="replay_user@campus.edu",
        role_name="COORDINATOR",
    )

    invitee = create_synthetic_user("replay_user@campus.edu")
    # First acceptance succeeds
    accept_invitation(db, raw_token=result.raw_token, accepting_user=invitee)

    # Second acceptance attempt must fail
    with pytest.raises(InvitationInvalidError, match="already been accepted"):
        accept_invitation(db, raw_token=result.raw_token, accepting_user=invitee)


def test_duplicate_membership_prevented(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify user who already has active membership cannot accept invitation to same org."""
    creator = create_synthetic_user("creator_dup@campus.edu")
    admin = create_synthetic_platform_admin("admin_dup@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    # Invite user for first role
    r1 = create_invitation(db, creator, org.id, "dup_user@campus.edu", "COORDINATOR")
    user = create_synthetic_user("dup_user@campus.edu")
    accept_invitation(db, r1.raw_token, user)

    # Issue a second invitation to the same user
    r2 = create_invitation(db, creator, org.id, "dup_user@campus.edu", "OFFICE_BEARER")

    # Attempting to accept when already active member raises DuplicateMembershipError
    with pytest.raises(DuplicateMembershipError):
        accept_invitation(db, r2.raw_token, user)


def test_concurrent_single_use_acceptance_simulation(db, create_synthetic_user, create_synthetic_platform_admin, monkeypatch):
    """
    Verify atomic concurrency guard: if another transaction commits an acceptance or revocation
    between this caller's initial lookup and the atomic update query, the atomic update
    matches zero rows (rowcount == 0), rolls back the transaction, and raises InvitationInvalidError.
    """
    creator = create_synthetic_user("creator_conc@campus.edu")
    admin = create_synthetic_platform_admin("admin_conc@campusops.internal")
    org = create_organization(db, creator, "College", "Verified Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(
        db,
        inviter=creator,
        organization_id=org.id,
        email="conc_user@campus.edu",
        role_name="COORDINATOR",
    )
    user = create_synthetic_user("conc_user@campus.edu")

    # Simulate race condition: mutate the row in the DB directly before atomic update runs
    original_execute = db.execute

    def simulated_race_execute(statement, *args, **kwargs):
        if hasattr(statement, "is_update") and statement.is_update:
            # Another concurrent transaction accepted the invitation first
            db.connection().execute(
                update(Invitation)
                .where(Invitation.id == result.invitation.id)
                .values(status="accepted")
            )
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", simulated_race_execute)

    with pytest.raises(InvitationInvalidError, match="already accepted or revoked concurrently"):
        accept_invitation(db, raw_token=result.raw_token, accepting_user=user)


def test_invitation_primary_admin_role_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify PRIMARY_ADMIN role cannot be granted via invitation."""
    creator = create_synthetic_user("creator_pa@campus.edu")
    admin = create_synthetic_platform_admin("admin_pa@campusops.internal")
    org = create_organization(db, creator, "College", "PA Club")
    verify_organization(db, admin, org.id, "verified")

    with pytest.raises(PermissionDeniedError, match="Primary Workspace Administrator cannot be granted via invitation"):
        create_invitation(
            db,
            inviter=creator,
            organization_id=org.id,
            email="new_pa@campus.edu",
            role_name="PRIMARY_ADMIN",
        )


def test_invitation_invalid_role_or_scope_rejected(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify invalid roles and scope mismatches are rejected at creation."""
    creator = create_synthetic_user("creator_val@campus.edu")
    admin = create_synthetic_platform_admin("admin_val@campusops.internal")
    org = create_organization(db, creator, "College", "Validation Club")
    verify_organization(db, admin, org.id, "verified")

    # 1. Unrecognized role
    with pytest.raises(ValueError, match="Invalid invitation role"):
        create_invitation(db, creator, org.id, "x@campus.edu", "SUPER_ADMIN")

    # 2. Invalid scope type
    with pytest.raises(ValueError, match="Invalid scope type"):
        create_invitation(db, creator, org.id, "x@campus.edu", "COORDINATOR", scope_type="global")

    # 3. Organization scope with scope_id
    with pytest.raises(ValueError, match="Organization-scoped invitation must not specify a scope_id"):
        create_invitation(db, creator, org.id, "x@campus.edu", "OFFICE_BEARER", scope_type="organization", scope_id=uuid.uuid4())

    # 4. Department scope without scope_id
    with pytest.raises(ValueError, match="requires a non-null scope_id"):
        create_invitation(db, creator, org.id, "x@campus.edu", "DEPARTMENT_LEAD", scope_type="department", scope_id=None)

    # 5. Role/scope incompatibility: DEPARTMENT_LEAD with organization scope
    with pytest.raises(ValueError, match="DEPARTMENT_LEAD role must be scoped to a department"):
        create_invitation(db, creator, org.id, "x@campus.edu", "DEPARTMENT_LEAD", scope_type="organization")


def test_invitation_accept_rejected_for_unverified_or_suspended_user(db, create_synthetic_user, create_synthetic_platform_admin):
    """Verify accepting user must be active and have a verified email."""
    creator = create_synthetic_user("creator_user_check@campus.edu")
    admin = create_synthetic_platform_admin("admin_user_check@campusops.internal")
    org = create_organization(db, creator, "College", "User Check Club")
    verify_organization(db, admin, org.id, "verified")

    result = create_invitation(db, creator, org.id, "target@campus.edu", "COORDINATOR")

    # Suspended user
    suspended_user = create_synthetic_user("target@campus.edu")
    suspended_user.account_status = "suspended"
    db.flush()

    with pytest.raises(InvitationInvalidError, match="account is not active"):
        accept_invitation(db, result.raw_token, suspended_user)

    # Unverified email user
    suspended_user.account_status = "active"
    suspended_user.email_verified_at = None
    db.flush()

    with pytest.raises(InvitationInvalidError, match="email must be verified"):
        accept_invitation(db, result.raw_token, suspended_user)


def test_invitation_accept_rejected_for_unverified_organization(db, create_synthetic_user):
    """Verify invitation cannot be accepted if organization is not in verified state."""
    creator = create_synthetic_user("creator_unv_org@campus.edu")
    org = create_organization(db, creator, "College", "Unverified Org")

    # Manually create invitation to test acceptance gate
    from app.services.invitation import hash_token
    import secrets
    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=org.id,
        email_normalized="invitee_unv@campus.edu",
        role_name="COORDINATOR",
        scope_type="organization",
        token_hash=hash_token(raw_token),
        status="pending",
        invited_by_user_id=creator.id,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()

    invitee = create_synthetic_user("invitee_unv@campus.edu")
    with pytest.raises(InvitationInvalidError, match="Organization must be verified"):
        accept_invitation(db, raw_token, invitee)


def test_reaccept_invitation_for_previously_removed_member_reactivates_membership(
    db, create_synthetic_user, create_synthetic_platform_admin
):
    """
    Verify that when a previously removed member accepts a new invitation,
    their membership is reactivated without raising an IntegrityError on the unique constraint.
    """
    creator = create_synthetic_user("creator_react@campus.edu")
    admin = create_synthetic_platform_admin("admin_react@campusops.internal")
    org = create_organization(db, creator, "College", "Reactivation Club")
    verify_organization(db, admin, org.id, "verified")

    # First invitation and acceptance
    r1 = create_invitation(db, creator, org.id, "member_react@campus.edu", "COORDINATOR")
    member_user = create_synthetic_user("member_react@campus.edu")
    m1 = accept_invitation(db, r1.raw_token, member_user)
    assert m1.membership_status == "active"

    # Member is subsequently removed from organization
    m1.membership_status = "removed"
    m1.removed_at = datetime.now(timezone.utc)
    db.commit()

    # Issue a new invitation to the removed member
    r2 = create_invitation(db, creator, org.id, "member_react@campus.edu", "OFFICE_BEARER")

    # Accepting the new invitation should reactivate the existing membership record
    m2 = accept_invitation(db, r2.raw_token, member_user)
    assert m2.id == m1.id  # Same membership row reactivated
    assert m2.membership_status == "active"
    assert m2.removed_at is None

    # Finding 2 Regression Check: Verify old role was revoked and only the new role is active
    active_roles = [ra for ra in m2.role_assignments if ra.revoked_at is None]
    assert len(active_roles) == 1
    assert active_roles[0].role_name == "OFFICE_BEARER"
