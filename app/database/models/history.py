"""Report status transition audit trail database model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import ReportStatus

if TYPE_CHECKING:
    from app.database.models.report import Report


class ReportHistory(Base):
    """Historical timeline entry recording status transitions for a report."""

    __tablename__ = "report_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[Optional[ReportStatus]] = mapped_column(
        SQLEnum(ReportStatus, name="report_status_enum", create_type=False),
        nullable=True,
    )
    new_status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, name="report_status_enum", create_type=False),
        nullable=False,
    )
    changed_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Username of admin or 'SYSTEM_AI'",
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="history")

    __table_args__ = (
        Index("idx_report_history_created", "report_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ReportHistory report={self.report_id} {self.old_status} -> {self.new_status}>"
