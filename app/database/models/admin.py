"""System administrator and operator database model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import AdminRole

if TYPE_CHECKING:
    from app.database.models.audit import AuditLog
    from app.database.models.report import Report


class Admin(Base):
    """Staff member or administrator with administrative privileges."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        SQLEnum(AdminRole, name="admin_role_enum"),
        default=AdminRole.OPERATOR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    assigned_reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="assigned_admin",
        lazy="selectin",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="admin",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Admin id={self.id} username='{self.username}' role='{self.role.value}'>"
