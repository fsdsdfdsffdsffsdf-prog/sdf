"""Enumeration types for AntiGraffiti AI database models."""

import enum


class ReportStatus(str, enum.Enum):
    """Lifecycle statuses of a graffiti report."""

    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    AI_REVIEW_REQUIRED = "AI_REVIEW_REQUIRED"


class AdminRole(str, enum.Enum):
    """Administrative access roles with hierarchical permissions."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"
    OPERATOR = "OPERATOR"


class GraffitiSeverity(str, enum.Enum):
    """Estimated scale and severity of graffiti vandalism."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationStatus(str, enum.Enum):
    """Delivery status of a push notification."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
