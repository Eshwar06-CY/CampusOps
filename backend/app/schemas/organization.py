from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import RoleSummaryResponse


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    college_name: str = Field(..., min_length=2, max_length=255)
    club_name: str = Field(..., min_length=2, max_length=255)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    college_name: str
    club_name: str
    verification_status: str
    created_at: datetime


class OrganizationDetailResponse(OrganizationResponse):
    model_config = ConfigDict(from_attributes=True)

    created_by_user_id: uuid.UUID
    verification_note: Optional[str] = None
    verification_reviewed_at: Optional[datetime] = None
    verification_reviewer_id: Optional[uuid.UUID] = None


class OrganizationVerificationResponse(OrganizationDetailResponse):
    """Full platform administration response including internal reviewer identity."""
    pass


class OrganizationVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(verified|rejected)$")
    note: Optional[str] = Field(None, max_length=1000)


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    email: str
    email_masked: bool = False
    membership_status: str
    joined_at: datetime
    roles: List[RoleSummaryResponse] = []
