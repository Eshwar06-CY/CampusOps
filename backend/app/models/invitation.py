import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import UserProfile


class Invitation(Base):
    """
    Single-use, scoped invitation bound to an email address and organization workspace (FA-009).
    Token is stored strictly as a cryptographic hash (SHA-256).
    """
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_normalized: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    role_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="invitations"
    )
    inviter: Mapped["UserProfile"] = relationship(
        "UserProfile", foreign_keys=[invited_by_user_id]
    )
    acceptor: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", foreign_keys=[accepted_by_user_id]
    )

    def is_valid_for_acceptance(self, now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return self.status == "pending" and expires > now and self.revoked_at is None

    def __repr__(self) -> str:
        return f"<Invitation id={self.id} org_id={self.organization_id} email={self.email_normalized} status={self.status}>"
