from datetime import date, datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    program_id: Optional[uuid.UUID] = None
    event_date: Optional[date] = None
    event_end_date: Optional[date] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=200)
    event_format: str = Field("in_person", max_length=50)
    registration_mode: str = Field("individual", max_length=50)
    timezone: str = Field("Asia/Kolkata", max_length=50)


class EventUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    event_date: Optional[date] = None
    event_end_date: Optional[date] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=200)
    event_format: Optional[str] = Field(None, max_length=50)
    registration_mode: Optional[str] = Field(None, max_length=50)
    timezone: Optional[str] = Field(None, max_length=50)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    program_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    event_date: Optional[date] = None
    event_end_date: Optional[date] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    venue: Optional[str] = None
    event_format: str
    registration_mode: str
    timezone: str
    status: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None


class EventLeadAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: uuid.UUID


class EventLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    event_id: uuid.UUID
    membership_id: uuid.UUID
    assigned_by_user_id: uuid.UUID
    assigned_at: datetime
    revoked_at: Optional[datetime] = None

