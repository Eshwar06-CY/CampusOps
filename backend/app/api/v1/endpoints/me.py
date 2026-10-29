from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.role import PlatformAdmin, RoleAssignment
from app.models.user import UserProfile
from app.schemas.user import (
    CurrentUserResponse,
    MembershipSummaryResponse,
    RoleSummaryResponse,
)

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    """
    Returns the authenticated user's profile and active organization memberships.
    Excludes passwords, credentials, external auth internals, and other tenants.
    """
    # Query active memberships
    memberships_stmt = (
        select(OrganizationMembership, Organization)
        .join(Organization, OrganizationMembership.organization_id == Organization.id)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.removed_at == None,
            Organization.archived_at == None,
        )
    )
    results = db.execute(memberships_stmt).all()

    memberships_data = []
    for membership, org in results:
        roles_stmt = select(RoleAssignment).where(
            RoleAssignment.membership_id == membership.id,
            RoleAssignment.revoked_at == None,
        )
        active_roles = list(db.execute(roles_stmt).scalars().all())
        roles_data = [
            RoleSummaryResponse(
                id=r.id,
                role_name=r.role_name,
                scope_type=r.scope_type,
                scope_id=r.scope_id,
            )
            for r in active_roles
        ]
        memberships_data.append(
            MembershipSummaryResponse(
                id=membership.id,
                organization_id=org.id,
                organization_name=org.club_name,
                college_name=org.college_name,
                membership_status=membership.membership_status,
                roles=roles_data,
            )
        )

    # Check if user is an active platform admin
    admin_stmt = select(PlatformAdmin).where(
        PlatformAdmin.user_id == current_user.id,
        PlatformAdmin.is_active == True,
    )
    is_platform_admin = db.execute(admin_stmt).scalar_one_or_none() is not None

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email_normalized,
        display_name=current_user.display_name,
        account_status=current_user.account_status,
        email_verified=current_user.email_verified_at is not None,
        is_platform_admin=is_platform_admin,
        memberships=memberships_data,
    )
