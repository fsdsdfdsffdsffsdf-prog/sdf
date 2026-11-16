"""Telegram user database model."""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.notification import Notification
    from app.database.models.report import Report


class User(Base, TimestampMixin):
    """Registered Telegram user who reports graffiti incidents."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_users_telegram_id_active", "telegram_id", "is_active"),
    )

    @property
    def full_name(self) -> str:
        """Helper to return user's human-readable name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.telegram_id} username='{self.username}'>"
