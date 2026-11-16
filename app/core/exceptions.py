"""Custom domain exceptions for the AntiGraffiti AI platform."""


class AntiGraffitiException(Exception):
    """Base exception for all domain-specific errors."""

    def __init__(self, message: str = "An unexpected error occurred in AntiGraffiti AI.") -> None:
        self.message = message
        super().__init__(self.message)


class UnauthorizedWebhookError(AntiGraffitiException):
    """Raised when Telegram Webhook secret token is invalid or missing."""

    def __init__(self, message: str = "Invalid Telegram Webhook secret token.") -> None:
        super().__init__(message)


class DuplicateUpdateError(AntiGraffitiException):
    """Raised when Telegram sends an already processed update_id."""

    def __init__(self, update_id: int) -> None:
        super().__init__(f"Update ID {update_id} has already been processed.")
        self.update_id = update_id


class InvalidImageError(AntiGraffitiException):
    """Raised when an uploaded photo is corrupted, exceeds size, or fails MIME check."""

    def __init__(self, message: str = "The provided file is not a valid or safe image.") -> None:
        super().__init__(message)


class AIVisionError(AntiGraffitiException):
    """Raised when OpenAI Vision API request fails or outputs unparseable response."""

    def __init__(self, message: str = "Failed to perform AI graffiti analysis.") -> None:
        super().__init__(message)


class ReportNotFoundError(AntiGraffitiException):
    """Raised when a requested graffiti report does not exist."""

    def __init__(self, report_id_or_number: str) -> None:
        super().__init__(f"Report '{report_id_or_number}' not found.")
        self.identifier = report_id_or_number


class AdminAuthError(AntiGraffitiException):
    """Raised on invalid admin credentials or expired session."""

    def __init__(self, message: str = "Authentication failed or session expired.") -> None:
        super().__init__(message)


class ForbiddenRoleError(AntiGraffitiException):
    """Raised when an admin attempts an action above their role permissions."""

    def __init__(self, required_role: str) -> None:
        super().__init__(f"Access denied. Requires role: {required_role}")
        self.required_role = required_role
