"""Notification log database model for tracking Telegram push deliveries."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import NotificationStatus

if TYPE_CHECKING:
    from app.database.models.report import Report
    from app.database.models.user import User


class Notification(Base):
    """Log record of notification sent or queued to be sent to a user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus, name="notification_status_enum"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    report: Mapped["Report"] = relationship("Report", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} status={self.status.value}>"
