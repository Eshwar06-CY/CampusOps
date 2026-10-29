import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import OrganizationMembership
    from app.models.user import UserProfile


class RoleAssignment(Base):
    """
    Explicit role assignment bound to a specific scope.
    Scope types: 'organization', 'program', 'event', 'department', 'task'.
    Scope ID is null for workspace/organization scope, or UUID for specific child resource.
    """
    __tablename__ = "role_assignments"
    __table_args__ = (
        Index("ix_role_assignments_membership_scope", "membership_id", "scope_type", "scope_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    scope_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True, index=True
    )
    granted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    membership: Mapped["OrganizationMembership"] = relationship(
        "OrganizationMembership", back_populates="role_assignments"
    )

    def is_active(self) -> bool:
        return self.revoked_at is None

    def __repr__(self) -> str:
        return f"<RoleAssignment id={self.id} role={self.role_name} scope={self.scope_type}:{self.scope_id}>"


class PlatformAdmin(Base):
    """
    Explicit, auditable platform-administrator authority for organization verification
    and platform operations. Strict no-backdoor design.
    """
    __tablename__ = "platform_admins"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    appointed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    appointed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    user: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="platform_admin_role", foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<PlatformAdmin id={self.id} user_id={self.user_id} active={self.is_active}>"
