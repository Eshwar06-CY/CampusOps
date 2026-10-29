from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.principal import get_current_user
from app.database import get_db
from app.models.user import UserProfile
from app.schemas.notification import NotificationResponse
from app.services.task import get_notification, list_notifications, mark_notification_as_read

router = APIRouter()


@router.get(
    "/notifications",
    response_model=List[NotificationResponse],
)
def get_user_notifications(
    organization_id: Optional[uuid.UUID] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NotificationResponse]:
    """Lists in-app notifications for the authenticated user."""
    notifs = list_notifications(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
        unread_only=unread_only,
    )
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    return notifs[safe_offset : safe_offset + safe_limit]


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
)
def get_single_notification(
    notification_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Retrieves a single notification for the authenticated recipient."""
    try:
        return get_notification(
            db=db,
            user=current_user,
            notification_id=notification_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Marks an in-app notification as read by the recipient."""
    try:
        return mark_notification_as_read(
            db=db,
            user=current_user,
            notification_id=notification_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

