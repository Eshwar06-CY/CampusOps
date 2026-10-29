from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    program_id: Optional[uuid.UUID] = None
    standalone_event_id: Optional[uuid.UUID] = None


class DepartmentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    program_id: Optional[uuid.UUID] = None
    standalone_event_id: Optional[uuid.UUID] = None
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

