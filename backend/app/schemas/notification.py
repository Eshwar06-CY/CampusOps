from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    related_entity_type: str
    related_entity_id: uuid.UUID
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

