"""Package constants."""

from __future__ import annotations

DEFAULT_TIMEOUT_SECONDS = 360.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_FACTOR = 0.5

PRODUCTION_BASE_URL = "https://gpmap.opengwas.io/api"
DEV_BASE_URL = "http://localhost:8000"

MAX_IDS_EXPAND = 10
MAX_IDS_NON_EXPAND = 50
