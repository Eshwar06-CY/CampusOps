from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """
    Strongly-typed authenticated identity claims from an upstream identity adapter.
    In production, this will be constructed from verified JWT claims (e.g. Supabase Auth JWKS).
    """
    auth_subject_id: str
    email: str
    email_verified: bool
    display_name: Optional[str] = None


def get_current_principal() -> AuthenticatedPrincipal:
    """
    FastAPI dependency resolving the authenticated principal.

    Fail-closed policy:
    In this slice, the production identity provider integration (FPC-04) is pending
    feasibility evaluation and selection. Normal runtime requests fail closed with
    HTTP 401 Unauthorized. Never trusts X-User-ID, query parameters, or unverified claims.

    In automated tests, this dependency is overridden using:
        app.dependency_overrides[get_current_principal] = lambda: test_principal
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: identity provider adapter is not configured.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UserProfile:
    """
    FastAPI dependency resolving and synchronizing the internal UserProfile
    from the trusted AuthenticatedPrincipal.

    Enforces that:
    - The profile is linked to the trusted principal's auth_subject_id and normalized email.
    - Caller-supplied IDs cannot spoof another user profile.
    - Inactive/suspended user accounts are denied with HTTP 403 Forbidden.
    - Unverified emails are denied with HTTP 403 Forbidden.
    """
    email_norm = principal.email.strip().lower()

    # 1. Look up primarily by immutable external auth_subject_id
    stmt = select(UserProfile).where(UserProfile.auth_subject_id == principal.auth_subject_id)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        # 2. Check if email is already claimed by an existing user profile
        stmt_email = select(UserProfile).where(UserProfile.email_normalized == email_norm)
        existing_by_email = db.execute(stmt_email).scalar_one_or_none()

        if existing_by_email is not None:
            # An unverified principal can NEVER link or access an existing profile
            if not principal.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email address must be verified before performing organization operations.",
                )
            # If the profile is already linked to a different auth_subject_id, reject conflict
            if existing_by_email.auth_subject_id and existing_by_email.auth_subject_id != principal.auth_subject_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Identity conflict: email is already associated with another authentication subject.",
                )
            # Link previously unlinked profile
            existing_by_email.auth_subject_id = principal.auth_subject_id
            if existing_by_email.email_verified_at is None:
                existing_by_email.email_verified_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_by_email)
            user = existing_by_email
        else:
            # New email: require email verification before creating an active profile
            if not principal.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email address must be verified before performing organization operations.",
                )
            user = UserProfile(
                auth_subject_id=principal.auth_subject_id,
                email_normalized=email_norm,
                display_name=principal.display_name or email_norm.split("@")[0].capitalize(),
                email_verified_at=datetime.now(timezone.utc),
                account_status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # User found by immutable auth_subject_id. Check if email changed at identity provider.
        if user.email_normalized != email_norm:
            if not principal.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="New email address must be verified before updating profile.",
                )
            # Check if new email is already claimed by another user profile
            conflict = db.execute(
                select(UserProfile).where(
                    UserProfile.email_normalized == email_norm,
                    UserProfile.id != user.id,
                )
            ).scalar_one_or_none()
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="New email address is already associated with another profile.",
                )
            user.email_normalized = email_norm
            user.email_verified_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
        elif principal.email_verified and user.email_verified_at is None:
            user.email_verified_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)

    # Invariant enforcement
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended, disabled, or locked.",
        )

    if not principal.email_verified or user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be verified before performing organization operations.",
        )

    return user
