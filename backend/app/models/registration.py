import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.organization import Organization
    from app.models.user import UserProfile


class EventRegistrationSettings(Base):
    """
    Registration settings and capacity parameters for an Event.
    Strictly 1:1 with an Event instance (standalone or child event under a program).
    """
    __tablename__ = "event_registration_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_event_reg_settings_event_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "registration_format IN ('solo_only', 'team_only', 'both')",
            name="ck_event_reg_settings_format",
        ),
        CheckConstraint(
            "team_size_min >= 1 AND team_size_max >= team_size_min",
            name="ck_event_reg_settings_team_bounds",
        ),
        CheckConstraint(
            "capacity_limit IS NULL OR capacity_limit >= 0",
            name="ck_event_reg_settings_capacity",
        ),
        CheckConstraint(
            "current_confirmed_count >= 0",
            name="ck_event_reg_settings_confirmed_nonneg",
        ),
        CheckConstraint(
            "current_attended_count >= 0",
            name="ck_event_reg_settings_attended_nonneg",
        ),
        CheckConstraint(
            "registration_open_at IS NULL OR registration_close_at IS NULL OR registration_close_at >= registration_open_at",
            name="ck_event_reg_settings_dates",
        ),
        Index("ix_event_reg_settings_org", "organization_id"),
        Index(
            "uq_event_reg_settings_key_hash",
            "registration_key_hash",
            unique=True,
            sqlite_where=text("registration_key_hash IS NOT NULL"),
            postgresql_where=text("registration_key_hash IS NOT NULL"),
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    registration_format: Mapped[str] = mapped_column(
        String(30), default="both", nullable=False
    )
    capacity_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_confirmed_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    current_attended_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    waitlist_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    team_size_min: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    team_size_max: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    registration_open_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_close_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_key_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    access_code_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
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
    event: Mapped["Event"] = relationship(
        "Event",
        foreign_keys=[event_id],
        overlaps="tickets,participant,registration",
    )
    organization: Mapped["Organization"] = relationship("Organization")

    def __repr__(self) -> str:
        return f"<EventRegistrationSettings event={self.event_id} is_open={self.is_open} confirmed={self.current_confirmed_count}>"


class Registration(Base):
    """
    Administrative registration transaction header representing either an
    individual attendee submission or a team submission (D-SLICE5-01, D-SLICE5-03).
    """
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_registrations_id_org"),
        UniqueConstraint("id", "event_id", name="uq_registrations_id_event"),
        UniqueConstraint(
            "id", "event_id", "organization_id", name="uq_registrations_id_event_org"
        ),
        UniqueConstraint(
            "event_id", "confirmation_code", name="uq_registrations_event_code"
        ),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_registrations_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_registrations_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "registration_type IN ('individual', 'team')",
            name="ck_registrations_type",
        ),
        CheckConstraint(
            "registration_status IN ('confirmed', 'waitlisted', 'cancelled')",
            name="ck_registrations_status",
        ),
        CheckConstraint(
            "registration_channel IN ('native_web', 'walk_in', 'external_import')",
            name="ck_registrations_channel",
        ),
        CheckConstraint(
            "(registration_type = 'team' AND team_name IS NOT NULL) OR (registration_type = 'individual')",
            name="ck_registrations_team_name",
        ),
        CheckConstraint(
            "(registration_status = 'cancelled' AND cancelled_at IS NOT NULL) OR (registration_status != 'cancelled' AND cancelled_at IS NULL)",
            name="ck_registrations_cancellation",
        ),
        Index("ix_registrations_org_event", "organization_id", "event_id"),
        Index("ix_registrations_event_status", "event_id", "registration_status"),
        Index("ix_registrations_event_contact", "event_id", "contact_email"),
        Index(
            "uq_registrations_event_idempotency",
            "event_id",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL"),
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    registration_type: Mapped[str] = mapped_column(
        String(20), default="individual", nullable=False
    )
    registration_status: Mapped[str] = mapped_column(
        String(30), default="confirmed", nullable=False
    )
    registration_channel: Mapped[str] = mapped_column(
        String(20), default="native_web", nullable=False
    )
    team_name: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )
    contact_email: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    confirmation_code: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    source_type: Mapped[str] = mapped_column(
        String(30), default="native", nullable=False
    )
    external_source_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
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
    event: Mapped["Event"] = relationship(
        "Event",
        foreign_keys=[event_id],
        overlaps="tickets,participant,registration",
    )
    organization: Mapped["Organization"] = relationship("Organization")
    registration_participants: Mapped[List["RegistrationParticipant"]] = relationship(
        "RegistrationParticipant",
        back_populates="registration",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="registration",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Registration id={self.id} event={self.event_id} type={self.registration_type} status={self.registration_status}>"


class Participant(Base):
    """
    Canonical attendee record scoped strictly to an Event and Organization.
    Does NOT require a CampusOps UserProfile/staff account.
    Email is NOT globally unique per event; multiple distinct individuals may legitimately
    share an email address (e.g. family, lab, or mentor email) per PRD v1.1 FA-007.
    """
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_participants_id_org"),
        UniqueConstraint("id", "event_id", name="uq_participants_id_event"),
        UniqueConstraint(
            "id", "event_id", "organization_id", name="uq_participants_id_event_org"
        ),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_participants_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_participants_org",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('registered', 'cancelled', 'attended')",
            name="ck_participants_status",
        ),
        Index("ix_participants_org_event", "organization_id", "event_id"),
        Index("ix_participants_event_email", "event_id", "email_normalized"),
        Index("ix_participants_event_name", "event_id", "full_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    college_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    student_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="registered", nullable=False
    )
    custom_answers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    external_participant_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
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
    event: Mapped["Event"] = relationship(
        "Event",
        foreign_keys=[event_id],
        overlaps="tickets,participant,registration",
    )
    organization: Mapped["Organization"] = relationship("Organization")
    registration_participants: Mapped[List["RegistrationParticipant"]] = relationship(
        "RegistrationParticipant",
        back_populates="participant",
        cascade="all, delete-orphan",
        overlaps="registration_participants,registration",
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="participant",
        cascade="all, delete-orphan",
        overlaps="tickets,registration",
    )
    check_ins: Mapped[List["CheckIn"]] = relationship(
        "CheckIn",
        back_populates="participant",
        cascade="all, delete-orphan",
        overlaps="check_ins,ticket,event",
    )

    def __repr__(self) -> str:
        return f"<Participant id={self.id} event={self.event_id} name={self.full_name!r} status={self.status}>"


class RegistrationParticipant(Base):
    """
    Join table linking an individual Participant to a Registration header.
    Maintains role mapping ('solo', 'leader', 'member') and contact accountability.
    """
    __tablename__ = "registration_participants"
    __table_args__ = (
        UniqueConstraint(
            "registration_id", "participant_id", name="uq_reg_part_reg_participant"
        ),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_reg_parts_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["registration_id", "event_id", "organization_id"],
            [
                "registrations.id",
                "registrations.event_id",
                "registrations.organization_id",
            ],
            name="fk_reg_parts_registration",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["participant_id", "event_id", "organization_id"],
            [
                "participants.id",
                "participants.event_id",
                "participants.organization_id",
            ],
            name="fk_reg_parts_participant",
            ondelete="CASCADE",
        ),
        Index("ix_reg_parts_participant", "participant_id"),
        Index("ix_reg_parts_registration", "registration_id"),
        Index("ix_reg_parts_event", "event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    is_primary_contact: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    team_role: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    registration: Mapped["Registration"] = relationship(
        "Registration",
        foreign_keys=[registration_id],
        back_populates="registration_participants",
        overlaps="participant,registration_participants,event",
    )
    participant: Mapped["Participant"] = relationship(
        "Participant",
        foreign_keys=[participant_id],
        back_populates="registration_participants",
        overlaps="registration,registration_participants,event",
    )

    def __repr__(self) -> str:
        return f"<RegistrationParticipant reg={self.registration_id} part={self.participant_id} role={self.team_role}>"


class Ticket(Base):
    """
    Non-payment digital admission pass issued to an individual participant (D-SLICE5-02).
    Stores only the SHA-256 digest (pass_code_hash) of the high-entropy unguessable token.
    The raw credential is never persisted in the database.
    Enforces strictly at most one active ('issued') pass per participant via partial index.
    """
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_tickets_id_org"),
        UniqueConstraint("id", "event_id", name="uq_tickets_id_event"),
        UniqueConstraint(
            "id", "event_id", "organization_id", name="uq_tickets_id_event_org"
        ),
        UniqueConstraint("event_id", "pass_code_hash", name="uq_tickets_event_hash"),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_tickets_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["participant_id", "event_id", "organization_id"],
            [
                "participants.id",
                "participants.event_id",
                "participants.organization_id",
            ],
            name="fk_tickets_participant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["registration_id", "event_id", "organization_id"],
            [
                "registrations.id",
                "registrations.event_id",
                "registrations.organization_id",
            ],
            name="fk_tickets_registration",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('issued', 'used', 'revoked', 'cancelled')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "(status = 'used' AND used_at IS NOT NULL) OR (status != 'used')",
            name="ck_tickets_used_at",
        ),
        CheckConstraint(
            "(status = 'revoked' AND revoked_at IS NOT NULL) OR (status != 'revoked' AND revoked_at IS NULL)",
            name="ck_tickets_revoked_at",
        ),
        Index(
            "uq_ticket_participant_active",
            "participant_id",
            unique=True,
            sqlite_where=text("status = 'issued'"),
            postgresql_where=text("status = 'issued'"),
        ),
        Index("ix_tickets_participant", "participant_id"),
        Index("ix_tickets_registration", "registration_id"),
        Index("ix_tickets_event_hash", "event_id", "pass_code_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    ticket_reference: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    pass_code_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="issued", nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        "Event",
        foreign_keys=[event_id],
        overlaps="tickets",
    )
    participant: Mapped["Participant"] = relationship(
        "Participant",
        foreign_keys=[participant_id],
        back_populates="tickets",
        overlaps="registration,tickets,event",
    )
    registration: Mapped["Registration"] = relationship(
        "Registration",
        foreign_keys=[registration_id],
        back_populates="tickets",
        overlaps="participant,tickets,event",
    )
    check_ins: Mapped[List["CheckIn"]] = relationship(
        "CheckIn",
        back_populates="ticket",
        overlaps="check_ins,participant,event",
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} ref={self.ticket_reference} status={self.status}>"


class CheckIn(Base):
    """
    Verified attendance arrival record for an individual participant (CO-FR-009, FA-005).
    Enforces strictly at most one valid check-in per participant per event via partial unique index.
    """
    __tablename__ = "check_ins"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_check_ins_id_org"),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_check_ins_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["participant_id", "event_id", "organization_id"],
            [
                "participants.id",
                "participants.event_id",
                "participants.organization_id",
            ],
            name="fk_check_ins_participant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["ticket_id", "event_id", "organization_id"],
            ["tickets.id", "tickets.event_id", "tickets.organization_id"],
            name="fk_check_ins_ticket",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["checked_in_by_user_id"],
            ["user_profiles.id"],
            name="fk_check_ins_checked_by",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["voided_by_user_id"],
            ["user_profiles.id"],
            name="fk_check_ins_voided_by",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "check_in_status IN ('valid', 'voided')",
            name="ck_check_ins_status",
        ),
        CheckConstraint(
            "method IN ('qr_scan', 'manual_search', 'walk_in_direct')",
            name="ck_check_ins_method",
        ),
        CheckConstraint(
            "((check_in_status = 'voided' AND voided_at IS NOT NULL AND voided_by_user_id IS NOT NULL) "
            "OR (check_in_status = 'valid' AND voided_at IS NULL AND voided_by_user_id IS NULL))",
            name="ck_check_ins_void_integrity",
        ),
        Index(
            "uq_check_in_event_participant",
            "event_id",
            "participant_id",
            unique=True,
            sqlite_where=text("check_in_status = 'valid'"),
            postgresql_where=text("check_in_status = 'valid'"),
        ),
        Index("ix_check_ins_org_event", "organization_id", "event_id"),
        Index("ix_check_ins_participant", "participant_id"),
        Index("ix_check_ins_ticket", "ticket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    check_in_status: Mapped[str] = mapped_column(
        String(30), default="valid", nullable=False
    )
    method: Mapped[str] = mapped_column(
        String(30), default="qr_scan", nullable=False
    )
    station_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    checked_in_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        "Event",
        foreign_keys=[event_id],
        overlaps="participant,check_ins,ticket",
    )
    participant: Mapped["Participant"] = relationship(
        "Participant",
        foreign_keys=[participant_id],
        back_populates="check_ins",
        overlaps="ticket,check_ins,event",
    )
    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        foreign_keys=[ticket_id],
        back_populates="check_ins",
        overlaps="participant,check_ins,event",
    )
    checker: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[checked_in_by_user_id]
    )
    voider: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", foreign_keys=[voided_by_user_id]
    )
    corrections: Mapped[List["CheckInCorrection"]] = relationship(
        "CheckInCorrection",
        back_populates="check_in",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CheckIn id={self.id} event={self.event_id} participant={self.participant_id} status={self.check_in_status}>"


class CheckInCorrection(Base):
    """
    Append-only immutable audit trail for check-in corrections and voids (D-SLICE5-04).
    Every void operation requires an authorized manager, audit timestamp, and mandatory explanation.
    """
    __tablename__ = "check_in_corrections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["check_in_id"],
            ["check_ins.id"],
            name="fk_corrections_check_in",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["corrected_by_user_id"],
            ["user_profiles.id"],
            name="fk_corrections_corrected_by",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(trim(reason)) >= 10",
            name="ck_corrections_reason_min_length",
        ),
        Index("ix_check_in_corrections_item", "check_in_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    check_in_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(30), nullable=False)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False
    )
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    check_in: Mapped["CheckIn"] = relationship(
        "CheckIn", back_populates="corrections"
    )
    corrector: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[corrected_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<CheckInCorrection id={self.id} check_in={self.check_in_id} status={self.new_status}>"
