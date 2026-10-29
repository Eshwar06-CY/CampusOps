import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization, OrganizationMembership
    from app.models.user import UserProfile


class Program(Base):
    """
    Multi-event umbrella (e.g. E-Week) belonging to an organization workspace.
    Shared departments are defined at the program level (D-SLICE3-01).
    Archival is strictly non-destructive (D-SLICE3-04).
    """
    __tablename__ = "programs"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_programs_org_name"),
        UniqueConstraint("id", "organization_id", name="uq_programs_id_org"),
        CheckConstraint(
            "planned_start_date IS NULL OR planned_end_date IS NULL OR planned_end_date >= planned_start_date",
            name="ck_programs_date_order",
        ),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
            name="ck_programs_status_archived",
        ),
        Index("ix_programs_org_status", "organization_id", "status"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    planned_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", index=True
    )
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
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    creator: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[created_by_user_id]
    )
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="program",
        foreign_keys="Event.program_id",
        cascade="all, delete-orphan",
    )
    departments: Mapped[List["Department"]] = relationship(
        "Department",
        back_populates="program",
        foreign_keys="Department.program_id",
        cascade="all, delete-orphan",
    )

    def is_active(self) -> bool:
        return self.archived_at is None

    def __repr__(self) -> str:
        return f"<Program id={self.id} name={self.name!r} org={self.organization_id}>"


class Event(Base):
    """
    Operational event instance belonging to an organization.
    Represents either:
    1. Standalone Event (program_id IS NULL)
    2. Child Event under a Program (program_id IS NOT NULL)
    """
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_events_id_org"),
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_events_program_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "event_end_date IS NULL OR event_date IS NULL OR event_end_date >= event_date",
            name="ck_events_date_order",
        ),
        CheckConstraint(
            "(planned_start_time IS NULL OR planned_end_time IS NULL) "
            "OR (event_end_date IS NOT NULL AND event_date IS NOT NULL AND event_end_date > event_date) "
            "OR (planned_end_time >= planned_start_time)",
            name="ck_events_time_order",
        ),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
            name="ck_events_status_archived",
        ),
        Index("ix_events_org_program", "organization_id", "program_id"),
        Index("ix_events_org_status", "organization_id", "status"),
        Index("ix_events_org_date", "organization_id", "event_date"),
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
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    event_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    venue: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Asia/Kolkata"
    )
    event_format: Mapped[str] = mapped_column(
        String(50), nullable=False, default="in_person"
    )
    registration_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="individual"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", index=True
    )
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
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    program: Mapped[Optional["Program"]] = relationship(
        "Program", back_populates="events", foreign_keys=[program_id]
    )
    creator: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[created_by_user_id]
    )
    standalone_departments: Mapped[List["Department"]] = relationship(
        "Department",
        back_populates="standalone_event",
        foreign_keys="Department.standalone_event_id",
        cascade="all, delete-orphan",
    )
    lead_assignments: Mapped[List["EventLeadAssignment"]] = relationship(
        "EventLeadAssignment",
        back_populates="event",
        foreign_keys="EventLeadAssignment.event_id",
        cascade="all, delete-orphan",
    )

    @property
    def is_standalone(self) -> bool:
        return self.program_id is None

    def is_active(self) -> bool:
        return self.archived_at is None

    def __repr__(self) -> str:
        return f"<Event id={self.id} name={self.name!r} org={self.organization_id} program={self.program_id}>"


class Department(Base):
    """
    Functional team within an organization.
    Exclusive-parent invariant (ck_departments_exclusive_parent):
    Must belong to exactly one of:
    - Program (shared department in multi-event program)
    - Standalone Event (owned by that standalone event)
    """
    __tablename__ = "departments"
    __table_args__ = (
        CheckConstraint(
            "((program_id IS NOT NULL AND standalone_event_id IS NULL) OR "
            "(program_id IS NULL AND standalone_event_id IS NOT NULL))",
            name="ck_departments_exclusive_parent",
        ),
        ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_departments_program_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["standalone_event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_departments_event_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
            name="ck_departments_status_archived",
        ),
        Index("ix_departments_org_program", "organization_id", "program_id"),
        Index("ix_departments_org_event", "organization_id", "standalone_event_id"),
        Index("ix_departments_org_status", "organization_id", "status"),
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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    standalone_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", index=True
    )
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
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    program: Mapped[Optional["Program"]] = relationship(
        "Program", back_populates="departments", foreign_keys=[program_id]
    )
    standalone_event: Mapped[Optional["Event"]] = relationship(
        "Event", back_populates="standalone_departments", foreign_keys=[standalone_event_id]
    )
    creator: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[created_by_user_id]
    )

    @property
    def is_program_shared(self) -> bool:
        return self.program_id is not None

    def is_active(self) -> bool:
        return self.archived_at is None

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name!r} org={self.organization_id}>"


class EventLeadAssignment(Base):
    """
    Auditable assignment relating an eligible organization member to an Event as an event lead.
    Supports multiple leads per event, but prevents duplicate active assignments for the same member.
    """
    __tablename__ = "event_lead_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_event_lead_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            name="fk_event_lead_membership_org",
            ondelete="CASCADE",
        ),
        Index("ix_event_leads_event_membership", "event_id", "membership_id"),
        Index("ix_event_leads_org_status", "organization_id", "revoked_at"),
        Index(
            "uq_event_lead_active",
            "event_id",
            "membership_id",
            unique=True,
            sqlite_where=text("revoked_at IS NULL"),
            postgresql_where=text("revoked_at IS NULL"),
        ),
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
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    event: Mapped["Event"] = relationship(
        "Event", back_populates="lead_assignments", foreign_keys=[event_id]
    )
    membership: Mapped["OrganizationMembership"] = relationship(
        "OrganizationMembership", foreign_keys=[membership_id]
    )
    assigner: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[assigned_by_user_id]
    )

    def is_active(self) -> bool:
        return self.revoked_at is None

    def __repr__(self) -> str:
        return f"<EventLeadAssignment id={self.id} event={self.event_id} member={self.membership_id} active={self.is_active()}>"
