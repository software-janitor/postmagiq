"""Standard exception classes for the API.

All custom exceptions inherit from QuillexirException and include:
- message: Human-readable error message
- error_code: Machine-readable error code (e.g., "NOT_FOUND")
- details: Optional dictionary with additional context
"""

from typing import Any, Optional


class QuillexirException(Exception):
    """Base exception for all Quillexir API errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code for client handling
        details: Optional dictionary with additional error context
        status_code: HTTP status code (set by subclasses)
    """

    status_code: int = 500
    default_error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or self.default_error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "code": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(QuillexirException):
    """Resource not found (HTTP 404).

    Use when the requested resource does not exist.
    """

    status_code = 404
    default_error_code = "NOT_FOUND"

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class ValidationError(QuillexirException):
    """Request validation failed (HTTP 400).

    Use when request data fails validation rules.
    """

    status_code = 400
    default_error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class AuthenticationError(QuillexirException):
    """Authentication failed (HTTP 401).

    Use when credentials are missing, invalid, or expired.
    """

    status_code = 401
    default_error_code = "AUTHENTICATION_FAILED"

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class AuthorizationError(QuillexirException):
    """Authorization failed (HTTP 403).

    Use when the user is authenticated but lacks permission.
    """

    status_code = 403
    default_error_code = "FORBIDDEN"

    def __init__(
        self,
        message: str = "Permission denied",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class RateLimitError(QuillexirException):
    """Rate limit exceeded (HTTP 429).

    Use when the user has exceeded their request quota.
    """

    status_code = 429
    default_error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class ConflictError(QuillexirException):
    """Resource conflict (HTTP 409).

    Use when the request conflicts with current state
    (e.g., duplicate resource, version mismatch).
    """

    status_code = 409
    default_error_code = "CONFLICT"

    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)
