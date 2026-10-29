import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models.event import EventLeadAssignment
from app.models.invitation import Invitation
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.services.errors import (
    DuplicateMembershipError,
    InvitationEmailMismatchError,
    InvitationError,
    InvitationExpiredError,
    InvitationInvalidError,
    InvitationNotFoundError,
    PermissionDeniedError,
)
from app.services.permissions import (
    ACTION_INVITE_MEMBER,
    ACTION_MANAGE_ROLES,
    require_permission,
)

# Allowed invitable roles (PRIMARY_ADMIN cannot be invited; creator or transferred via controlled flow)
ALLOWED_INVITATION_ROLES = {
    "OFFICE_BEARER",
    "EVENT_LEAD",
    "DEPARTMENT_LEAD",
    "COORDINATOR",
    "REGISTRATION_STAFF",
}

ALLOWED_SCOPES = {"organization", "department", "event"}


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to ensure a datetime is timezone-aware UTC (handles SQLite naive timestamps)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class InvitationCreationResult:
    """Internal service result returning the persisted invitation and the single-use raw token."""
    invitation: Invitation
    raw_token: str  # Only returned for distribution/testing; never persisted


def hash_token(token: str) -> str:
    """Computes SHA-256 hex digest of the raw invitation token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_invitation(
    db: Session,
    inviter: UserProfile,
    organization_id: uuid.UUID,
    email: str,
    role_name: str,
    scope_type: str = "organization",
    scope_id: Optional[uuid.UUID] = None,
) -> InvitationCreationResult:
    """
    Creates a single-use, 7-day scoped invitation (FA-009).
    Enforces inviter permission and verified organization status.
    Stores only the SHA-256 hash of the token.
    """
    # 1. Validate role_name and scope invariants before querying permissions
    if role_name == "PRIMARY_ADMIN":
        raise PermissionDeniedError(
            "Primary Workspace Administrator cannot be granted via invitation. "
            "Administration must be transferred through a controlled transfer flow."
        )

    if role_name not in ALLOWED_INVITATION_ROLES:
        raise ValueError(
            f"Invalid invitation role '{role_name}'. Must be one of: {sorted(ALLOWED_INVITATION_ROLES)}"
        )

    if scope_type not in ALLOWED_SCOPES:
        raise ValueError(
            f"Invalid scope type '{scope_type}'. Must be one of: {sorted(ALLOWED_SCOPES)}"
        )

    if scope_type == "organization" and scope_id is not None:
        raise ValueError("Organization-scoped invitation must not specify a scope_id.")

    if scope_type in ("department", "event") and scope_id is None:
        raise ValueError(f"Scope type '{scope_type}' requires a non-null scope_id.")

    # Role/scope compatibility
    if role_name == "DEPARTMENT_LEAD" and scope_type != "department":
        raise ValueError("DEPARTMENT_LEAD role must be scoped to a department.")
    if role_name == "EVENT_LEAD" and scope_type != "event":
        raise ValueError("EVENT_LEAD role must be scoped to an event.")
    if role_name == "OFFICE_BEARER" and scope_type != "organization":
        raise ValueError("OFFICE_BEARER role must be scoped to the organization.")

    # 2. Enforce inviter permission
    require_permission(
        db,
        user=inviter,
        action=ACTION_INVITE_MEMBER,
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )

    # 3. Normalize email
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("A valid email address is required.")

    # 4. Generate high-entropy token and cryptographic hash
    raw_token = secrets.token_urlsafe(32)
    token_digest = hash_token(raw_token)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.invitation_expiry_days)

    # 5. Persist invitation
    invitation = Invitation(
        organization_id=organization_id,
        email_normalized=normalized_email,
        role_name=role_name,
        scope_type=scope_type,
        scope_id=scope_id,
        token_hash=token_digest,
        status="pending",
        invited_by_user_id=inviter.id,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return InvitationCreationResult(invitation=invitation, raw_token=raw_token)


def accept_invitation(
    db: Session,
    raw_token: str,
    accepting_user: UserProfile,
) -> OrganizationMembership:
    """
    Accepts an invitation, verifies email match, single-use validity, and non-expiration.
    Enforces atomic status transition to prevent concurrent re-use.
    Creates or reactivates an OrganizationMembership and RoleAssignment for the accepting user.
    """
    if not raw_token or not raw_token.strip():
        raise InvitationNotFoundError("Token cannot be empty.")

    token_digest = hash_token(raw_token.strip())

    # 1. Look up invitation by token hash and verify in constant time
    stmt = select(Invitation).where(Invitation.token_hash == token_digest)
    invitation = db.execute(stmt).scalar_one_or_none()
    if not invitation or not secrets.compare_digest(invitation.token_hash, token_digest):
        raise InvitationNotFoundError("Invitation not found.")

    # User integrity: accepting user must be active and email verified
    if not accepting_user or accepting_user.account_status != "active":
        raise InvitationInvalidError("Accepting user account is not active.")
    if accepting_user.email_verified_at is None:
        raise InvitationInvalidError("Accepting user email must be verified before accepting an invitation.")

    # Organization integrity: must exist, not be archived, and be verified
    org = db.get(Organization, invitation.organization_id)
    if not org or org.archived_at is not None:
        raise InvitationInvalidError("Organization does not exist or has been archived.")
    if org.verification_status != "verified":
        raise InvitationInvalidError("Organization must be verified before invitations can be accepted.")

    now = datetime.now(timezone.utc)

    # 2. Validate current state
    if invitation.status == "accepted":
        raise InvitationInvalidError("Invitation has already been accepted.")
    if invitation.status == "revoked" or invitation.revoked_at is not None:
        raise InvitationInvalidError("Invitation has been revoked.")

    # 3. Check 7-day expiration
    expires_at = ensure_utc(invitation.expires_at)
    if now >= expires_at:
        invitation.status = "expired"
        db.commit()
        raise InvitationExpiredError("Invitation has expired.")

    # 4. Enforce email match: accepting user's email must match invited email
    if accepting_user.email_normalized != invitation.email_normalized:
        raise InvitationEmailMismatchError(
            f"Invitation was issued to '{invitation.email_normalized}', not '{accepting_user.email_normalized}'."
        )

    # 5. Check if user already has a membership in this organization (prevent crashes on uq constraint)
    existing_membership = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == invitation.organization_id,
            OrganizationMembership.user_id == accepting_user.id,
        )
    ).scalar_one_or_none()

    membership_to_reactivate = None
    if existing_membership:
        if existing_membership.membership_status == "active":
            raise DuplicateMembershipError("User is already an active member of this organization.")
        elif existing_membership.membership_status == "suspended":
            raise DuplicateMembershipError("User membership in this organization is suspended.")
        elif existing_membership.membership_status == "removed":
            membership_to_reactivate = existing_membership

    # 6. Atomic state transition to prevent concurrent duplicate acceptance
    atomic_update = (
        update(Invitation)
        .where(
            Invitation.id == invitation.id,
            Invitation.status == "pending",
        )
        .values(
            status="accepted",
            accepted_at=now,
            accepted_by_user_id=accepting_user.id,
        )
    )
    result = db.execute(atomic_update)
    if result.rowcount == 0:
        db.rollback()
        raise InvitationInvalidError("Invitation was already accepted or revoked concurrently.")

    # 7. Create or reactivate organization membership
    if membership_to_reactivate:
        membership_to_reactivate.membership_status = "active"
        membership_to_reactivate.removed_at = None
        membership_to_reactivate.joined_at = now
        # Revoke any prior unrevoked role assignments so legacy privileges do not accumulate
        for old_ra in membership_to_reactivate.role_assignments:
            if old_ra.revoked_at is None:
                old_ra.revoked_at = now
        membership = membership_to_reactivate
    else:
        membership = OrganizationMembership(
            organization_id=invitation.organization_id,
            user_id=accepting_user.id,
            membership_status="active",
            created_by_user_id=invitation.invited_by_user_id,
            joined_at=now,
        )
        db.add(membership)

    db.flush()

    # 8. Grant scoped role assignment
    role_assignment = RoleAssignment(
        membership_id=membership.id,
        role_name=invitation.role_name,
        scope_type=invitation.scope_type,
        scope_id=invitation.scope_id,
        granted_by_user_id=invitation.invited_by_user_id,
        created_at=now,
    )
    db.add(role_assignment)

    # 9. Atomic Event Lead provenance synchronization (D-SLICE3-02 / Slice 3B)
    if invitation.role_name == "EVENT_LEAD" and invitation.scope_type == "event":
        event_lead = EventLeadAssignment(
            organization_id=invitation.organization_id,
            event_id=invitation.scope_id,
            membership_id=membership.id,
            assigned_by_user_id=invitation.invited_by_user_id,
            assigned_at=now,
        )
        db.add(event_lead)

    try:
        db.commit()
        db.refresh(membership)
        return membership
    except Exception:
        db.rollback()
        raise


def revoke_invitation(
    db: Session,
    revoker: UserProfile,
    invitation_id: uuid.UUID,
) -> Invitation:
    """Revokes a pending invitation. Requires role management permission."""
    invitation = db.get(Invitation, invitation_id)
    if not invitation:
        raise InvitationNotFoundError(f"Invitation '{invitation_id}' not found.")

    require_permission(
        db,
        user=revoker,
        action=ACTION_MANAGE_ROLES,
        organization_id=invitation.organization_id,
    )

    if invitation.status != "pending":
        raise InvitationInvalidError(f"Cannot revoke invitation in '{invitation.status}' status.")

    now = datetime.now(timezone.utc)
    invitation.status = "revoked"
    invitation.revoked_at = now
    invitation.revoked_by_user_id = revoker.id
    db.commit()
    db.refresh(invitation)
    return invitation
