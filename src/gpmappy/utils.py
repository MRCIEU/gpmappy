"""General utility helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from gpmappy.merge import add_coloc_pair_details

GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
INLINE_STUDY_CHUNKS = 2


def is_guid(value: str | int) -> bool:
    return bool(GUID_PATTERN.match(str(value)))


def cleanup_api_object(api_object: dict[str, Any]) -> dict[str, Any]:
    """Drop empty elements and describe both sides of any coloc pairs."""
    cleaned = {k: v for k, v in api_object.items() if v not in (None, [], {})}
    return add_coloc_pair_details(cleaned)


def create_source_url(study_name: str) -> str:
    chunks = study_name.split("-")
    token = (
        study_name
        if len(chunks) <= INLINE_STUDY_CHUNKS
        else "-".join([*chunks[:INLINE_STUDY_CHUNKS], "_".join(chunks[INLINE_STUDY_CHUNKS:])])
    )
    return f"https://opengwas.io/datasets/{token}"


def build_multi_params(name: str, values: Iterable[str | int]) -> str:
    payload = [(name, str(v)) for v in values]
    return urlencode(payload)


def rows_to_records(columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Turn the API's compact ``*_column_names`` + ``*_rows`` payloads into records."""
    return [dict(zip(columns, row)) for row in rows]


def columns_to_records(
    columns: Sequence[str], data: Mapping[str, Sequence[Any]]
) -> list[dict[str, Any]]:
    """Turn the API's columnar ``*_column_names`` + ``*_columns`` payloads into records."""
    if not columns:
        return []
    return rows_to_records(columns, zip(*(data[column] for column in columns)))


def tabular_payload_to_records(payload: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    """Read a ``format=columnar`` payload (``<prefix>_columns``, one list per column) into records.

    The row format (``<prefix>_rows``, one list per row), which an API without ``format``
    support returns, is still read.
    """
    columns = payload.get(f"{prefix}_column_names") or []
    data = payload.get(f"{prefix}_columns")
    if data is not None:
        return columns_to_records(columns, data)
    return rows_to_records(columns, payload.get(f"{prefix}_rows") or [])
