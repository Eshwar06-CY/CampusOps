from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# =========================================================================
# Request Models (extra="forbid")
# =========================================================================

class OperationalBlockerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    scope_type: str = Field("organization", max_length=20)
    scope_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    priority: str = Field("medium", max_length=20)
    owner_membership_id: Optional[uuid.UUID] = None


class OperationalBlockerUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    priority: Optional[str] = Field(None, max_length=20)
    owner_membership_id: Optional[uuid.UUID] = None


class OperationalBlockerResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_note: str = Field(..., min_length=1, max_length=2000)
    status: str = Field("resolved", pattern="^(resolved|wont_fix)$")


class OperationalBlockerReopenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=1000)


# =========================================================================
# Response Models (from_attributes=True)
# =========================================================================

class OperationalBlockerHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    blocker_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    note: Optional[str] = None
    changed_by_user_id: uuid.UUID
    created_at: datetime


class OperationalBlockerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    scope_type: str
    scope_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    title: str
    description: str
    status: str
    priority: str
    owner_membership_id: Optional[uuid.UUID] = None
    resolved_by_user_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OperationalBlockerDetailResponse(OperationalBlockerResponse):
    history: List[OperationalBlockerHistoryResponse] = Field(default_factory=list)

