from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class RoleSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role_name: str
    scope_type: str
    scope_id: Optional[uuid.UUID] = None


class MembershipSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    college_name: str
    membership_status: str
    roles: List[RoleSummaryResponse] = []


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    account_status: str
    email_verified: bool
    is_platform_admin: bool = False
    memberships: List[MembershipSummaryResponse] = []
