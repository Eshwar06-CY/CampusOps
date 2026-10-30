import uuid
from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.event import Department, Event, Program
    from app.models.organization import Organization, OrganizationMembership
    from app.models.user import UserProfile


class Task(Base):
    """
    Operational work item belonging to an organization workspace and scoped to an
    organization, program, event, or department (D-SLICE4-01).
    Enforces required deadline, proof requirement, priority, and auditable status lifecycle.
    """
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_tasks_id_org"),
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_tasks_program_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_tasks_event_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tasks_priority",
        ),
        CheckConstraint(
            "status IN ('not_started', 'assigned', 'in_progress', 'submitted_for_review', 'changes_requested', 'completed', 'cancelled')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "scope_type IN ('organization', 'program', 'event', 'department')",
            name="ck_tasks_scope_type",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR (status != 'completed' AND completed_at IS NULL)",
            name="ck_tasks_status_completed",
        ),
        Index("ix_tasks_org_status", "organization_id", "status"),
        Index("ix_tasks_org_scope", "organization_id", "scope_type", "scope_id"),
        Index("ix_tasks_org_event", "organization_id", "event_id"),
        Index("ix_tasks_org_due", "organization_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)

    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")
    proof_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    creator: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[created_by_user_id])
    program: Mapped[Optional["Program"]] = relationship("Program", foreign_keys=[program_id])
    event: Mapped[Optional["Event"]] = relationship("Event", foreign_keys=[event_id])
    department: Mapped[Optional["Department"]] = relationship("Department", foreign_keys=[department_id])

    assignees: Mapped[List["TaskAssignee"]] = relationship(
        "TaskAssignee",
        back_populates="task",
        foreign_keys="TaskAssignee.task_id",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[List["TaskStatusHistory"]] = relationship(
        "TaskStatusHistory",
        back_populates="task",
        foreign_keys="TaskStatusHistory.task_id",
        cascade="all, delete-orphan",
        order_by="TaskStatusHistory.created_at.asc()",
    )
    deadline_history: Mapped[List["TaskDeadlineHistory"]] = relationship(
        "TaskDeadlineHistory",
        back_populates="task",
        foreign_keys="TaskDeadlineHistory.task_id",
        cascade="all, delete-orphan",
        order_by="TaskDeadlineHistory.changed_at.asc()",
    )
    submissions: Mapped[List["EvidenceSubmission"]] = relationship(
        "EvidenceSubmission",
        back_populates="task",
        foreign_keys="EvidenceSubmission.task_id",
        cascade="all, delete-orphan",
        order_by="EvidenceSubmission.submission_number.asc()",
    )

    def is_active(self) -> bool:
        return self.archived_at is None

    @property
    def active_assignee(self) -> Optional["TaskAssignee"]:
        return next(
            (
                a for a in self.assignees
                if a.assignment_status == "active"
                and (not a.membership or (a.membership.membership_status == "active" and a.membership.removed_at is None))
            ),
            None,
        )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status} scope={self.scope_type}:{self.scope_id}>"


class TaskAssignee(Base):
    """
    Join table connecting tasks and assigned workspace members.
    Enforces active membership tenant alignment via composite foreign key.
    Maintains assignment history and supports single active assignment or reassignment.
    """
    __tablename__ = "task_assignees"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "organization_id"],
            ["tasks.id", "tasks.organization_id"],
            name="fk_task_assignees_task_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            name="fk_task_assignees_membership_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "assignment_status IN ('active', 'unassigned')",
            name="ck_task_assignees_status",
        ),
        Index(
            "uq_task_assignee_active",
            "task_id",
            unique=True,
            sqlite_where=text("assignment_status = 'active'"),
            postgresql_where=text("assignment_status = 'active'"),
        ),
        Index("ix_task_assignees_task", "task_id"),
        Index("ix_task_assignees_membership", "membership_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unassigned_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="assignees", foreign_keys=[task_id])
    membership: Mapped["OrganizationMembership"] = relationship("OrganizationMembership", foreign_keys=[membership_id])
    assigned_by: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[assigned_by_user_id])

    def __repr__(self) -> str:
        return f"<TaskAssignee id={self.id} task_id={self.task_id} membership_id={self.membership_id} status={self.assignment_status}>"


class TaskDeadlineHistory(Base):
    """
    Immutable audit history for task deadline adjustments.
    Records previous and new due dates/times, authorized actor, timestamp, and mandatory reason.
    """
    __tablename__ = "task_deadline_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_due_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    new_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_due_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="deadline_history", foreign_keys=[task_id])
    changed_by: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[changed_by_user_id])


class TaskStatusHistory(Base):
    """
    Immutable audit history recording all state transitions of a task.
    Supports progress updates and accountability across the operational lifecycle.
    """
    __tablename__ = "task_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="status_history", foreign_keys=[task_id])
    changed_by: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[changed_by_user_id])


class EvidenceSubmission(Base):
    """
    Versioned attempt by an assigned member to prove task completion.
    Tracks submitter identity, submission version number, note, and review status.
    """
    __tablename__ = "evidence_submissions"
    __table_args__ = (
        UniqueConstraint("task_id", "submission_number", name="uq_evidence_submissions_task_num"),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'changes_requested')",
            name="ck_evidence_submissions_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    submission_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitter_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="submissions", foreign_keys=[task_id])
    submitter_user: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[submitted_by_user_id])
    submitter_membership: Mapped["OrganizationMembership"] = relationship("OrganizationMembership", foreign_keys=[submitted_by_membership_id])
    artifacts: Mapped[List["EvidenceArtifact"]] = relationship(
        "EvidenceArtifact",
        back_populates="submission",
        foreign_keys="EvidenceArtifact.submission_id",
        cascade="all, delete-orphan",
    )
    review: Mapped[Optional["TaskReview"]] = relationship(
        "TaskReview",
        back_populates="submission",
        foreign_keys="TaskReview.evidence_submission_id",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EvidenceArtifact(Base):
    """
    Individual evidence item within an EvidenceSubmission.
    Currently supports valid absolute HTTP/HTTPS URLs (external links).
    File upload references are reserved for future private object-storage adapter.
    """
    __tablename__ = "evidence_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('url', 'file_reference')",
            name="ck_evidence_artifacts_type",
        ),
        CheckConstraint(
            "(artifact_type = 'url' AND url IS NOT NULL AND file_reference IS NULL) OR "
            "(artifact_type = 'file_reference' AND file_reference IS NOT NULL AND url IS NULL)",
            name="ck_evidence_artifacts_payload",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evidence_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False, default="url")
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    submission: Mapped["EvidenceSubmission"] = relationship("EvidenceSubmission", back_populates="artifacts", foreign_keys=[submission_id])


class TaskReview(Base):
    """
    Formal review decision (approval or rejection with changes requested) against a specific submission.
    Enforces that rejection requires a non-empty review note.
    Self-approval is strictly forbidden.
    """
    __tablename__ = "task_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'changes_requested')",
            name="ck_task_reviews_decision",
        ),
        CheckConstraint(
            "(decision = 'changes_requested' AND review_note IS NOT NULL) OR (decision = 'approved')",
            name="ck_task_reviews_note_on_rejection",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    evidence_submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evidence_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    submission: Mapped["EvidenceSubmission"] = relationship("EvidenceSubmission", back_populates="review", foreign_keys=[evidence_submission_id])
    task: Mapped["Task"] = relationship("Task", foreign_keys=[task_id])
    reviewer_user: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[reviewer_user_id])
    reviewer_membership: Mapped["OrganizationMembership"] = relationship("OrganizationMembership", foreign_keys=[reviewer_membership_id])


class OperationalBlocker(Base):
    """
    Internal staff-only operational impediment tracking (CO-FR-012).
    Captures operational issues (e.g. room locked, equipment missing, vendor delayed)
    scoped to organization, program, event, department, or task.
    Strictly isolated from public or participant-facing access.
    """
    __tablename__ = "operational_blockers"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('organization', 'program', 'event', 'department', 'task')",
            name="ck_operational_blockers_scope",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_operational_blockers_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'wont_fix')",
            name="ck_operational_blockers_status",
        ),
        CheckConstraint(
            "(status IN ('resolved', 'wont_fix') AND resolved_at IS NOT NULL) OR "
            "(status IN ('open', 'in_progress') AND resolved_at IS NULL)",
            name="ck_operational_blockers_resolved",
        ),
        Index("ix_operational_blockers_org_status", "organization_id", "status"),
        Index("ix_operational_blockers_org_scope", "organization_id", "scope_type", "scope_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)

    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_membership_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    creator: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[created_by_user_id])
    owner_membership: Mapped[Optional["OrganizationMembership"]] = relationship("OrganizationMembership", foreign_keys=[owner_membership_id])
    resolved_by: Mapped[Optional["UserProfile"]] = relationship("UserProfile", foreign_keys=[resolved_by_user_id])
    task: Mapped[Optional["Task"]] = relationship("Task", foreign_keys=[task_id])
    event: Mapped[Optional["Event"]] = relationship("Event", foreign_keys=[event_id])

    history: Mapped[List["OperationalBlockerHistory"]] = relationship(
        "OperationalBlockerHistory",
        back_populates="blocker",
        foreign_keys="OperationalBlockerHistory.blocker_id",
        cascade="all, delete-orphan",
        order_by="OperationalBlockerHistory.created_at.asc()",
    )


class OperationalBlockerHistory(Base):
    """
    Audit history tracking status transitions, owner updates, and resolution notes for blockers.
    """
    __tablename__ = "operational_blocker_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    blocker_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("operational_blockers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    blocker: Mapped["OperationalBlocker"] = relationship("OperationalBlocker", back_populates="history", foreign_keys=[blocker_id])
    changed_by: Mapped["UserProfile"] = relationship("UserProfile", foreign_keys=[changed_by_user_id])


class Notification(Base):
    """
    Durable in-app notification record (CO-FR-019).
    Stores operational event alerts (task assigned, deadline changed, proof reviewed, blocker resolved)
    within the workspace boundary without external provider dependency.
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    related_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    related_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped["UserProfile"] = relationship("UserProfile")
