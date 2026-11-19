"""Pydantic v2 schema for structured OpenAI Vision API response validation."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AIGraffitiAnalysisResult(BaseModel):
    """
    Strongly-typed schema for the AI graffiti analysis response.
    Validated against the raw JSON returned by OpenAI Vision API.
    All fields are optional except is_graffiti and confidence.
    """

    is_graffiti: bool = Field(
        ...,
        description="Whether graffiti is present in the submitted photo",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score from 0.0 to 1.0",
    )
    graffiti_type: Optional[str] = Field(
        None,
        max_length=128,
        description="e.g. spray_paint, marker, sticker, stencil",
    )
    surface_type: Optional[str] = Field(
        None,
        max_length=128,
        description="e.g. concrete, brick, metal, wood, glass",
    )
    severity: Optional[str] = Field(
        None,
        max_length=64,
        description="LOW / MEDIUM / HIGH / CRITICAL",
    )
    estimated_area: Optional[str] = Field(
        None,
        max_length=128,
        description="Human-readable area estimate e.g. '1-3 square meters'",
    )
    removal_difficulty: Optional[str] = Field(
        None,
        max_length=64,
        description="easy / moderate / hard / professional_required",
    )
    description: Optional[str] = Field(
        None,
        max_length=1024,
        description="Human-readable description of what the AI observed",
    )
    recommendation: Optional[str] = Field(
        None,
        max_length=1024,
        description="Recommended action for the city maintenance service",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.upper().strip()
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        return normalized if normalized in allowed else "MEDIUM"

    class Config:
        extra = "ignore"  # Silently drop unknown fields from AI response
