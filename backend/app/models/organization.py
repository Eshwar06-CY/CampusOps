import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.invitation import Invitation
    from app.models.role import RoleAssignment
    from app.models.user import UserProfile


class Organization(Base):
    """
    Organization/club workspace.
    Begins in pending_verification state per FPC-02.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    college_name: Mapped[str] = mapped_column(String(255), nullable=False)
    club_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_verification",
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    creator: Mapped["UserProfile"] = relationship(
        "UserProfile",
        foreign_keys=[created_by_user_id],
    )
    verification_reviewer: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        foreign_keys=[verification_reviewer_id],
    )
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} club={self.club_name} status={self.verification_status}>"


class OrganizationMembership(Base):
    """
    Links a UserProfile to an Organization.
    Maintains active/invited/suspended/removed status and prevents duplicate memberships.
    """
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_membership_user"),
        UniqueConstraint("id", "organization_id", name="uq_org_memberships_id_org"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    membership_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    removed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
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
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships"
    )
    user: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="memberships", foreign_keys=[user_id]
    )
    role_assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        back_populates="membership",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<OrganizationMembership id={self.id} org_id={self.organization_id} user_id={self.user_id}>"
