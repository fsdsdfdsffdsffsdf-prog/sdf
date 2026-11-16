"""Administrator actions audit trail database model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.admin import Admin


class AuditLog(Base):
    """Immutable audit trail for all sensitive administrative actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="e.g. LOGIN, UPDATE_STATUS, REASSIGN, EXPORT_CSV",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="e.g. report, admin, system",
    )
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="ID or identifier of the affected entity",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    admin: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_action_date", "action", "created_at"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} admin_id={self.admin_id} action='{self.action}'>"
