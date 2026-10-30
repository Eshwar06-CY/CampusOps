from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationVerificationResponse,
    OrganizationVerifyRequest,
)
from app.schemas.user import RoleSummaryResponse
from app.services.errors import OrganizationVerificationError, PermissionDeniedError
from app.services.organization import (
    create_organization,
    get_organization,
    verify_organization,
)
from app.services.permissions import (
    ACTION_MANAGE_ROLES,
    can_perform,
    is_active_platform_admin,
)
from app.services.registration import mask_email

router = APIRouter()


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org(
    payload: OrganizationCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    """
    Creates an organization workspace with the authenticated user as creator and Primary Admin.
    Workspace begins in pending_verification status per FPC-02.
    """
    try:
        org = create_organization(
            db=db,
            creator=current_user,
            college_name=payload.college_name,
            club_name=payload.club_name,
        )
        return OrganizationResponse.model_validate(org)
    except (ValueError, OrganizationVerificationError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.get("/organizations", response_model=List[OrganizationResponse])
def list_my_organizations(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrganizationResponse]:
    """
    Returns only organizations where the authenticated user holds an active membership.
    Strict tenant boundary enforcement: does not leak foreign organizations.
    """
    stmt = (
        select(Organization)
        .join(OrganizationMembership, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.removed_at == None,
            Organization.archived_at == None,
        )
        .order_by(Organization.created_at.desc())
    )
    orgs = list(db.execute(stmt).scalars().all())
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.get("/organizations/{organization_id}", response_model=OrganizationDetailResponse)
def get_org_details(
    organization_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationDetailResponse:
    """
    Retrieves organization profile and verification state after checking authorization.
    Unauthorized or non-existent requests return 404 to prevent tenant enumeration.

    Information disclosure control:
    - Platform Admins: see all audit fields (reviewer ID, note, timestamp).
    - Primary Workspace Admins: see verification note and timestamp (to fix rejections), but reviewer ID is censored.
    - Ordinary Members (leads, coordinators, staff): see workspace details, but review notes and reviewer ID are censored (None).
    """
    try:
        org = get_organization(db=db, user=current_user, organization_id=organization_id)
        if not org or org.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        is_platform = is_active_platform_admin(db, current_user.id)
        is_primary_admin = False
        membership = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.membership_status == "active",
                OrganizationMembership.removed_at == None,
            )
        ).scalar_one_or_none()

        if membership:
            primary_ra = db.execute(
                select(RoleAssignment).where(
                    RoleAssignment.membership_id == membership.id,
                    RoleAssignment.role_name == "PRIMARY_ADMIN",
                    RoleAssignment.revoked_at == None,
                )
            ).scalar_one_or_none()
            is_primary_admin = primary_ra is not None

        return OrganizationDetailResponse(
            id=org.id,
            college_name=org.college_name,
            club_name=org.club_name,
            verification_status=org.verification_status,
            created_at=org.created_at,
            created_by_user_id=org.created_by_user_id,
            verification_note=org.verification_note if (is_platform or is_primary_admin) else None,
            verification_reviewed_at=org.verification_reviewed_at if (is_platform or is_primary_admin) else None,
            verification_reviewer_id=org.verification_reviewer_id if is_platform else None,
        )
    except PermissionDeniedError:
        # Uniform 404 response to avoid revealing organization existence to unauthorized users
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )


@router.post("/organizations/{organization_id}/verify", response_model=OrganizationVerificationResponse)
def verify_org(
    organization_id: uuid.UUID,
    payload: OrganizationVerifyRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationVerificationResponse:
    """
    Platform administrator verifies or rejects an organization workspace.
    Requires explicit platform admin authority. Rejection requires a reason.
    Returns full platform verification audit details.
    """
    try:
        org = verify_organization(
            db=db,
            admin_user=current_user,
            organization_id=organization_id,
            decision=payload.decision,
            note=payload.note,
        )
        return OrganizationVerificationResponse.model_validate(org)
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator authority is required to review organization verification.",
        )
    except OrganizationVerificationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.get(
    "/organizations/{organization_id}/members",
    response_model=List[OrganizationMemberResponse],
)
def get_organization_members(
    organization_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrganizationMemberResponse]:
    """
    Returns organization members with roles and privacy-aware contact disclosure.
    - Tenant-isolated: only active members or platform administrators can query.
    - Non-member access returns uniform 404.
    - Role managers and platform admins view unmasked emails; others receive masked emails.
    - Excludes credentials, tokens, hashes, and internal secrets.
    """
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    is_platform = is_active_platform_admin(db, current_user.id)
    caller_membership = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.removed_at == None,
        )
    ).scalar_one_or_none()

    if not caller_membership and not is_platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    # Privacy control: only workspace managers or platform admins view unmasked emails for other members
    can_view_unmasked = is_platform or can_perform(
        db=db,
        user=current_user,
        action=ACTION_MANAGE_ROLES,
        organization_id=organization_id,
        scope_type="organization",
    )

    stmt = (
        select(OrganizationMembership)
        .join(UserProfile, OrganizationMembership.user_id == UserProfile.id)
        .where(OrganizationMembership.organization_id == organization_id)
    )

    if status_filter:
        stmt = stmt.where(OrganizationMembership.membership_status == status_filter)
    else:
        # Default: active members (non-removed)
        stmt = stmt.where(OrganizationMembership.removed_at == None)

    stmt = stmt.order_by(OrganizationMembership.joined_at.asc()).offset(offset).limit(limit)
    memberships = list(db.execute(stmt).scalars().all())

    results: List[OrganizationMemberResponse] = []
    for mem in memberships:
        roles_stmt = select(RoleAssignment).where(
            RoleAssignment.membership_id == mem.id,
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

        is_self = mem.user_id == current_user.id
        raw_email = mem.user.email_normalized
        if is_self or can_view_unmasked:
            email = raw_email
            is_masked = False
        else:
            email = mask_email(raw_email)
            is_masked = True

        results.append(
            OrganizationMemberResponse(
                id=mem.id,
                organization_id=mem.organization_id,
                user_id=mem.user_id,
                display_name=mem.user.display_name,
                email=email,
                email_masked=is_masked,
                membership_status=mem.membership_status,
                joined_at=mem.joined_at,
                roles=roles_data,
            )
        )

    return results
