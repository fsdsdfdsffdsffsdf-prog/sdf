"""Pydantic v2 schemas for admin authentication and management."""

from datetime import datetime
from pydantic import BaseModel, Field
from app.database.models.enums import AdminRole


class AdminLoginRequest(BaseModel):
    """Login form payload for the admin panel."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=256)


class AdminCreateRequest(BaseModel):
    """Payload for creating a new admin user (SUPER_ADMIN only)."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=10, max_length=256)
    role: AdminRole = AdminRole.OPERATOR


class AdminOut(BaseModel):
    """Public admin profile for display in admin panel."""

    id: int
    username: str
    role: AdminRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminSessionPayload(BaseModel):
    """JWT token payload stored in admin session cookie."""

    admin_id: int
    username: str
    role: AdminRole
