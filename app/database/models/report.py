"""Graffiti incident report database model."""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin
from app.database.models.enums import ReportStatus

if TYPE_CHECKING:
    from app.database.models.admin import Admin
    from app.database.models.ai_analysis import AIAnalysis
    from app.database.models.history import ReportHistory
    from app.database.models.notification import Notification
    from app.database.models.user import User


class Report(Base, TimestampMixin):
    """Incident report submitted by a citizen via Telegram."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique reference number e.g. AG-2026-000001",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Absolute or relative file path to the verified photo on disk",
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, name="report_status_enum"),
        default=ReportStatus.NEW,
        nullable=False,
        index=True,
    )
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reports", lazy="selectin")
    assigned_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        back_populates="assigned_reports",
        lazy="selectin",
    )
    ai_analysis: Mapped[Optional["AIAnalysis"]] = relationship(
        "AIAnalysis",
        back_populates="report",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    history: Mapped[List["ReportHistory"]] = relationship(
        "ReportHistory",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportHistory.created_at.desc()",
        lazy="selectin",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_reports_status_district", "status", "district"),
        Index("idx_reports_coords", "latitude", "longitude"),
        Index("idx_reports_created_desc", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} number='{self.report_number}' status='{self.status.value}'>"
