"""Custom exception types."""

from __future__ import annotations


class GpmappyError(Exception):
    """Base error class for gpmappy."""


class ValidationError(GpmappyError):
    """Raised when inputs do not pass local validation."""


class ApiError(GpmappyError):
    """Raised when the remote API returns a non-success status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class TimeoutError(GpmappyError):
    """Raised when a request times out."""


class NetworkError(GpmappyError):
    """Raised for transport/network failures."""


class OptionalDependencyError(GpmappyError):
    """Raised when an optional dependency is required but not installed."""
