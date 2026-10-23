"""Custom exception types."""

from __future__ import annotations


class GpmappyError(Exception):
    """Base error class for gpmappy."""


class ValidationError(GpmappyError):
    """Raised when inputs do not pass local validation."""


class ApiError(GpmappyError):
    """Raised when the remote API returns a non-success status code.

    ``detail`` is the API's explanation (its ``detail`` field) when it sent one.
    """

    def __init__(self, status_code: int, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.detail = message if detail is None else detail


class RateLimitError(ApiError):
    """Raised when the API keeps responding 429 (Too Many Requests) after all retries."""

    def __init__(self, retries: int) -> None:
        super().__init__(
            429,
            f"GPMap API rate limit exceeded after {retries} retries. "
            "Please wait a moment and try again.",
        )
        self.retries = retries


class ApiVersionError(GpmappyError):
    """Raised when this gpmappy version does not support the API's version."""


class TimeoutError(GpmappyError):
    """Raised when a request times out."""


class NetworkError(GpmappyError):
    """Raised for transport/network failures."""


class OptionalDependencyError(GpmappyError):
    """Raised when an optional dependency is required but not installed."""
