"""AI vision inspection result database model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.report import Report


class AIAnalysis(Base):
    """Structured result of automated AI computer vision analysis."""

    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reports.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    is_graffiti: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    graffiti_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    surface_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    estimated_area: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    removal_difficulty: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full raw JSON response received from OpenAI Vision API",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="ai_analysis")

    __table_args__ = (
        Index("idx_ai_analysis_graffiti_conf", "is_graffiti", "confidence"),
    )

    def __repr__(self) -> str:
        return f"<AIAnalysis id={self.id} report_id={self.report_id} graffiti={self.is_graffiti} conf={self.confidence:.2f}>"
