from datetime import date, datetime, time
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# =========================================================================
# Request Models (extra="forbid")
# =========================================================================

class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    due_date: date
    due_time: Optional[time] = None
    timezone: str = Field("Asia/Kolkata", max_length=50)
    priority: str = Field("medium", max_length=20)
    proof_required: bool = True
    scope_type: str = Field("organization", max_length=20)
    scope_id: Optional[uuid.UUID] = None
    assignee_membership_id: Optional[uuid.UUID] = None


class TaskUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: Optional[str] = Field(None, max_length=20)


class TaskAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_membership_id: uuid.UUID


class TaskCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancellation_reason: str = Field(..., min_length=1, max_length=1000)


class TaskDeadlineChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_due_date: date
    new_due_time: Optional[time] = None
    reason: str = Field(..., min_length=1, max_length=1000)


class EvidenceSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_urls: List[str] = Field(default_factory=list)
    submitter_note: Optional[str] = Field(None, max_length=2000)


class TaskReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(approved|changes_requested)$")
    review_note: Optional[str] = Field(None, max_length=2000)


# =========================================================================
# Response Models (from_attributes=True)
# =========================================================================

class TaskAssigneeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    organization_id: uuid.UUID
    membership_id: uuid.UUID
    assignment_status: str
    assigned_by_user_id: uuid.UUID
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None
    unassigned_by_user_id: Optional[uuid.UUID] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    scope_type: str
    scope_id: Optional[uuid.UUID] = None
    program_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    proof_required: bool
    due_date: date
    due_time: Optional[time] = None
    timezone: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    active_assignee: Optional[TaskAssigneeResponse] = None


class TaskStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    changed_by_user_id: uuid.UUID
    created_at: datetime


class TaskDeadlineHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    previous_due_date: date
    previous_due_time: Optional[time] = None
    new_due_date: date
    new_due_time: Optional[time] = None
    reason: str
    changed_by_user_id: uuid.UUID
    changed_at: datetime


class TaskHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_history: List[TaskStatusHistoryResponse]
    deadline_history: List[TaskDeadlineHistoryResponse]
    assignees: List[TaskAssigneeResponse]


class EvidenceArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    submission_id: uuid.UUID
    artifact_type: str
    url: Optional[str] = None
    file_reference: Optional[str] = None
    created_at: datetime


class TaskReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    evidence_submission_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    reviewer_membership_id: uuid.UUID
    decision: str
    review_note: Optional[str] = None
    reviewed_at: datetime


class EvidenceSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    submitted_by_user_id: uuid.UUID
    submitted_by_membership_id: uuid.UUID
    submission_number: int
    submitter_note: Optional[str] = None
    status: str
    submitted_at: datetime
    artifacts: List[EvidenceArtifactResponse] = Field(default_factory=list)
    review: Optional[TaskReviewResponse] = None
