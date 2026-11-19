"""Pydantic v2 schemas for graffiti report creation, listing, and detail view."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.database.models.enums import ReportStatus


class ReportCreate(BaseModel):
    """Data required to create a new graffiti report."""

    user_telegram_id: int
    photo_path: str = Field(..., max_length=512)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = Field(None, max_length=512)
    district: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=2048)


class ReportStatusUpdate(BaseModel):
    """Payload for changing report status from admin panel."""

    new_status: ReportStatus
    comment: Optional[str] = Field(None, max_length=1024)
    assigned_admin_id: Optional[int] = None


class AIAnalysisOut(BaseModel):
    """Serialized AI analysis result for API and admin panel output."""

    is_graffiti: bool
    confidence: float
    graffiti_type: Optional[str]
    surface_type: Optional[str]
    severity: Optional[str]
    estimated_area: Optional[str]
    removal_difficulty: Optional[str]
    recommendation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    """Full report view for admin panel API."""

    id: int
    report_number: str
    status: ReportStatus
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    district: Optional[str]
    description: Optional[str]
    photo_path: str
    created_at: datetime
    updated_at: datetime
    ai_analysis: Optional[AIAnalysisOut] = None

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """Compact report summary for list views."""

    id: int
    report_number: str
    status: ReportStatus
    district: Optional[str]
    created_at: datetime
    has_ai_analysis: bool = False

    class Config:
        from_attributes = True


class ReportFilter(BaseModel):
    """Query filters for admin report listing."""

    status: Optional[ReportStatus] = None
    district: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
