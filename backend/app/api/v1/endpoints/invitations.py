import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.invitation import Invitation
from app.models.organization import Organization
from app.models.user import UserProfile
from app.schemas.invitation import (
    InvitationAcceptRequest,
    InvitationAcceptResponse,
    InvitationCreateRequest,
    InvitationResponse,
)
from app.services.email import EmailDeliveryService, get_email_service
from app.services.errors import (
    DepartmentNotFoundError,
    DuplicateMembershipError,
    EventNotFoundError,
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationInvalidError,
    InvitationNotFoundError,
    PermissionDeniedError,
    ScopeIntegrityError,
)
from app.services.event import (
    validate_department_scope_assignment,
    validate_event_scope_assignment,
)
from app.services.invitation import (
    accept_invitation,
    create_invitation,
    revoke_invitation,
)

router = APIRouter()


@router.post(
    "/organizations/{organization_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org_invitation(
    organization_id: uuid.UUID,
    payload: InvitationCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
    email_service: EmailDeliveryService = Depends(get_email_service),
) -> InvitationResponse:
    """
    Creates a single-use organization, department, or event invitation (Slice 3B).

    Enforces:
    - Scoped validation for organization, department, and event targets.
    - Fail-closed if transactional email provider is unconfigured (FPC-06).
    - Raw token is never returned in HTTP responses.
    """
    # 1. Scope and target entity validation
    if payload.scope_type not in ("organization", "department", "event"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope_type '{payload.scope_type}'. Must be 'organization', 'department', or 'event'.",
        )

    if payload.scope_type == "organization" and payload.scope_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization-scoped invitations must not specify a scope_id.",
        )

    if payload.scope_type in ("department", "event") and payload.scope_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scope type '{payload.scope_type}' requires a valid scope_id.",
        )

    # 2. Check organization exists
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    # Validate target entity exists and belongs to this organization
    if payload.scope_type == "department":
        try:
            validate_department_scope_assignment(
                db, organization_id=organization_id, department_id=payload.scope_id
            )
        except (DepartmentNotFoundError, ScopeIntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    if payload.scope_type == "event":
        try:
            validate_event_scope_assignment(
                db, organization_id=organization_id, event_id=payload.scope_id
            )
        except (EventNotFoundError, ScopeIntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # 3. Email delivery provider integration check (FPC-06 fail-closed rule)
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invitation delivery is unavailable: transactional email provider is not configured (FPC-06).",
        )

    # 4. Create invitation via domain service
    try:
        result = create_invitation(
            db=db,
            inviter=current_user,
            organization_id=organization_id,
            email=payload.email,
            role_name=payload.role_name,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
        )
    except PermissionDeniedError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

    # 5. Dispatch email containing the token
    try:
        email_sent = email_service.send_invitation_email(
            recipient_email=payload.email,
            organization_name=org.club_name,
            role_name=payload.role_name,
            raw_token=result.raw_token,
            expires_at=result.invitation.expires_at,
        )
    except Exception:
        email_sent = False

    if not email_sent:
        # If delivery failed or encountered an error, delete the persisted invitation
        # to avoid orphan undeliverable tokens (FA-009 / FPC-06).
        db.delete(result.invitation)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to deliver invitation email.",
        )

    # 6. Return response: strictly excludes raw_token and token_hash
    return InvitationResponse.model_validate(result.invitation)


@router.post(
    "/invitations/accept",
    response_model=InvitationAcceptResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invite(
    payload: InvitationAcceptRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationAcceptResponse:
    """
    Accepts an invitation using the single-use token provided in the JSON request body.
    Associates the authenticated principal with the granted organization membership.
    """
    try:
        membership = accept_invitation(
            db=db,
            raw_token=payload.token,
            accepting_user=current_user,
        )
        role = membership.role_assignments[0] if membership.role_assignments else None
        return InvitationAcceptResponse(
            membership_id=membership.id,
            organization_id=membership.organization_id,
            role_name=role.role_name if role else "MEMBER",
            scope_type=role.scope_type if role else "organization",
            status=membership.membership_status,
        )
    except InvitationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token is invalid or does not exist.",
        )
    except InvitationEmailMismatchError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )
    except DuplicateMembershipError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        )
    except (InvitationExpiredError, InvitationInvalidError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.post(
    "/organizations/{organization_id}/invitations/{invitation_id}/revoke",
    response_model=InvitationResponse,
    status_code=status.HTTP_200_OK,
)
def revoke_org_invitation(
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    """
    Revokes a pending invitation. Requires role management permission in the organization.
    """
    # Verify the invitation belongs to this organization before attempting revocation
    invitation = db.get(Invitation, invitation_id)
    if not invitation or invitation.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    try:
        revoked = revoke_invitation(
            db=db,
            revoker=current_user,
            invitation_id=invitation_id,
        )
        return InvitationResponse.model_validate(revoked)
    except InvitationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )
    except PermissionDeniedError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )
    except InvitationInvalidError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
