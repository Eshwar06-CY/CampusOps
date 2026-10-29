import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.services.errors import OrganizationVerificationError, PermissionDeniedError
from app.services.permissions import (
    ACTION_EDIT_ORG_PROFILE,
    ACTION_VIEW_ORG_PROFILE,
    ACTION_VERIFY_ORG,
    require_permission,
)


def create_organization(
    db: Session,
    creator: UserProfile,
    college_name: str,
    club_name: str,
) -> Organization:
    """
    Creates an organization in pending_verification state (FPC-02).
    Assigns the creator as an active member with Primary Workspace Administrator role (FPC-03).
    """
    college = college_name.strip()
    club = club_name.strip()
    if not college or not club:
        raise ValueError("College name and club name cannot be empty.")

    if not creator or creator.account_status != "active":
        raise OrganizationVerificationError("Creator user account must be active.")
    if creator.email_verified_at is None:
        raise OrganizationVerificationError("Creator email must be verified before creating an organization workspace.")

    org = Organization(
        college_name=college,
        club_name=club,
        verification_status="pending_verification",
        created_by_user_id=creator.id,
    )
    db.add(org)
    db.flush()  # populate org.id

    # Create creator membership
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        membership_status="active",
        created_by_user_id=creator.id,
    )
    db.add(membership)
    db.flush()  # populate membership.id

    # Grant Primary Workspace Administrator role at organization scope
    role_assignment = RoleAssignment(
        membership_id=membership.id,
        role_name="PRIMARY_ADMIN",
        scope_type="organization",
        scope_id=None,
        granted_by_user_id=creator.id,
    )
    db.add(role_assignment)
    db.commit()
    db.refresh(org)
    return org


def verify_organization(
    db: Session,
    admin_user: UserProfile,
    organization_id: uuid.UUID,
    decision: str,
    note: Optional[str] = None,
) -> Organization:
    """
    Platform administrator verifies or rejects an organization workspace.
    Requires explicit platform admin authority. Rejections require a reason (FPC-02).
    """
    # 1. Enforce platform admin authority
    require_permission(db, user=admin_user, action=ACTION_VERIFY_ORG)

    # 2. Validate decision
    if decision not in ("verified", "rejected"):
        raise OrganizationVerificationError(
            f"Invalid verification decision '{decision}'. Must be 'verified' or 'rejected'."
        )

    if decision == "rejected" and (not note or not note.strip()):
        raise OrganizationVerificationError("Rejection requires a documented reason.")

    # 3. Retrieve organization
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise OrganizationVerificationError(f"Organization '{organization_id}' not found.")

    # 4. Apply auditable decision
    org.verification_status = decision
    org.verification_reviewed_at = datetime.now(timezone.utc)
    org.verification_reviewer_id = admin_user.id
    org.verification_note = note.strip() if note else None

    db.commit()
    db.refresh(org)
    return org


def get_organization(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
) -> Organization:
    """Retrieve organization details after verifying permission."""
    require_permission(
        db,
        user=user,
        action=ACTION_VIEW_ORG_PROFILE,
        organization_id=organization_id,
    )
    return db.get(Organization, organization_id)
