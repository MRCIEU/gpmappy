"""Configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gpmappy.constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEV_BASE_URL,
    PRODUCTION_BASE_URL,
)


class ApiEnvironment(str, Enum):
    DEV = "dev"
    PRODUCTION = "production"
    CUSTOM = "custom"


@dataclass(slots=True)
class GpmapConfig:
    base_url: str = PRODUCTION_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    user_agent: str = "gpmappy/0.1.0"

    @staticmethod
    def from_environment(api: str) -> "GpmapConfig":
        if api == ApiEnvironment.DEV.value:
            return GpmapConfig(base_url=DEV_BASE_URL)
        if api == ApiEnvironment.PRODUCTION.value:
            return GpmapConfig(base_url=PRODUCTION_BASE_URL)
        raise ValueError(f"Unsupported API environment: {api}")
