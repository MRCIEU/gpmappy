"""General utility helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlencode

GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_guid(value: str | int) -> bool:
    return bool(GUID_PATTERN.match(str(value)))


def cleanup_api_object(api_object: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in api_object.items() if v is not None and v != [] and v != {}}


def create_source_url(study_name: str) -> str:
    chunks = study_name.split("-")
    if len(chunks) <= 2:
        token = study_name
    else:
        token = "-".join(chunks[:2] + ["_".join(chunks[2:])])
    return f"https://opengwas.io/datasets/{token}"


def build_multi_params(name: str, values: Iterable[str | int]) -> str:
    payload = [(name, str(v)) for v in values]
    return urlencode(payload)
