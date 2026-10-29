import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import PlatformAdmin
from app.models.user import UserProfile
from app.services.errors import PermissionDeniedError
from app.services.permissions import is_active_platform_admin


def appoint_platform_admin(
    db: Session,
    target_user: UserProfile,
    appointing_admin: Optional[UserProfile] = None,
    notes: Optional[str] = None,
) -> PlatformAdmin:
    """
    Explicit platform administrator appointment and bootstrap mechanism.
    Safety rules:
    - Target user must exist, have an active account, and have a verified email.
    - If any active platform administrators already exist, appointing_admin is mandatory
      and must be an active platform administrator.
    - If NO active platform administrators exist (first-time system bootstrap),
      appointing_admin may be None to safely establish the initial administrator.
    - Prevents duplicate active platform admin records.
    - Completely server-side; not exposed to any public or unauthenticated HTTP endpoint.
    """
    if not target_user or target_user.account_status != "active":
        raise ValueError("Target user must have an active account.")
    if target_user.email_verified_at is None:
        raise ValueError("Target user email must be verified.")

    # Check if active platform admins already exist in the database
    existing_admins = list(
        db.execute(
            select(PlatformAdmin).where(
                PlatformAdmin.is_active == True,
                PlatformAdmin.revoked_at == None,
            )
        ).scalars().all()
    )

    if existing_admins:
        if appointing_admin is None:
            raise PermissionDeniedError(
                "Appointing administrator is required when active platform administrators exist."
            )
        if not is_active_platform_admin(db, appointing_admin.id):
            raise PermissionDeniedError(
                "Only an active platform administrator can appoint another platform administrator."
            )

    # Check target user's existing record
    existing_for_target = db.execute(
        select(PlatformAdmin).where(PlatformAdmin.user_id == target_user.id)
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if existing_for_target:
        if existing_for_target.is_active and existing_for_target.revoked_at is None:
            raise ValueError("Target user is already an active platform administrator.")
        # Reactivate previously revoked platform admin
        existing_for_target.is_active = True
        existing_for_target.revoked_at = None
        existing_for_target.appointed_at = now
        existing_for_target.appointed_by_user_id = appointing_admin.id if appointing_admin else None
        existing_for_target.notes = notes
        db.commit()
        db.refresh(existing_for_target)
        return existing_for_target

    admin = PlatformAdmin(
        user_id=target_user.id,
        is_active=True,
        appointed_by_user_id=appointing_admin.id if appointing_admin else None,
        appointed_at=now,
        notes=notes,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
