"""Package constants."""

from __future__ import annotations

DEFAULT_TIMEOUT_SECONDS = 360.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_RATE_LIMIT_MAX_RETRIES = 5
DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS = 1.0
DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS = 32.0

PRODUCTION_BASE_URL = "https://gpmap.opengwas.io/api"
DEV_BASE_URL = "http://localhost:8000"

# GPMap API version -> the gpmappy versions that support it (as gpmapr's api_to_package_version).
API_TO_PACKAGE_VERSION = {
    "1.0.1": ("0.1.0", "0.1.1"),
    "1.1.0": ("1.0.0",),
}
API_VERSION_TIMEOUT_SECONDS = 10.0

MAX_IDS_EXPAND = 10
MAX_IDS_NON_EXPAND = 50
