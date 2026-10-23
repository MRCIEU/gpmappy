"""Configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from gpmappy.constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS,
    DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS,
    DEFAULT_RATE_LIMIT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEV_BASE_URL,
    PRODUCTION_BASE_URL,
)
from gpmappy.version import package_version


class ApiEnvironment(str, Enum):
    DEV = "dev"
    PRODUCTION = "production"
    CUSTOM = "custom"


@dataclass
class GpmapConfig:
    base_url: str = PRODUCTION_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    rate_limit_max_retries: int = DEFAULT_RATE_LIMIT_MAX_RETRIES
    rate_limit_base_delay: float = DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS
    rate_limit_max_delay: float = DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS
    user_agent: str = field(default_factory=lambda: f"gpmappy/{package_version()}")
    # Check once per API URL that this gpmappy version supports the API's version.
    check_api_version: bool = True

    @staticmethod
    def from_environment(api: str) -> GpmapConfig:
        if api == ApiEnvironment.DEV.value:
            return GpmapConfig(base_url=DEV_BASE_URL)
        if api == ApiEnvironment.PRODUCTION.value:
            return GpmapConfig(base_url=PRODUCTION_BASE_URL)
        raise ValueError(f"Unsupported API environment: {api}")
