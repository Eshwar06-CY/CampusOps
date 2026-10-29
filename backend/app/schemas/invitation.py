from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=255)
    role_name: str = Field(..., min_length=2, max_length=100)
    scope_type: str = Field(default="organization", max_length=50)
    scope_id: Optional[uuid.UUID] = None


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    email: str = Field(validation_alias="email_normalized")
    email_normalized: str
    role_name: str
    scope_type: str
    scope_id: Optional[uuid.UUID] = None
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=16, max_length=255)


class InvitationAcceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    membership_id: uuid.UUID
    organization_id: uuid.UUID
    role_name: str
    scope_type: str
    status: str
