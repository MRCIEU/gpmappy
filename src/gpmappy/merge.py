"""Merge/transformation helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

ASSOCIATION_JOIN_KEYS = ("study_id", "variant_id")
UPLOAD_ASSOCIATION_COLUMNS = ("beta", "se", "p", "eaf", "imputed")


def _column_names(records: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(key for record in records for key in record))


def _left_join(
    rows: list[dict[str, Any]],
    associations: list[dict[str, Any]],
    keys: Sequence[str],
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    """Left-join association ``columns`` onto ``rows`` by ``keys``.

    Like dplyr's ``distinct()`` + ``left_join()``: the first association for a key
    wins, and rows without a match still gain the columns, set to None.
    """
    index: dict[tuple[Any, ...], dict[str, Any]] = {}
    for association in associations:
        index.setdefault(tuple(association.get(key) for key in keys), association)

    merged_rows: list[dict[str, Any]] = []
    for row in rows:
        match = index.get(tuple(row.get(key) for key in keys), {})
        enriched = dict(row)
        for column in columns:
            enriched.setdefault(column, match.get(column))
        merged_rows.append(enriched)
    return merged_rows


def merge_associations(
    coloc_groups: list[dict[str, Any]] | None,
    rare_results: list[dict[str, Any]] | None,
    associations: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Add association statistics (beta, se, p, ...) to coloc groups and rare results."""
    coloc_rows = list(coloc_groups or [])
    rare_rows = list(rare_results or [])
    assoc_rows = associations or []
    available = _column_names(assoc_rows)
    if not all(key in available for key in ASSOCIATION_JOIN_KEYS):
        return coloc_rows, rare_rows

    columns = [column for column in available if column not in ASSOCIATION_JOIN_KEYS]
    return (
        _left_join(coloc_rows, assoc_rows, ASSOCIATION_JOIN_KEYS, columns),
        _left_join(rare_rows, assoc_rows, ASSOCIATION_JOIN_KEYS, columns),
    )


def merge_gwas_upload_associations(
    coloc_groups: list[dict[str, Any]] | None,
    associations: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Add association statistics to the coloc groups of a GWAS upload.

    Rows with a ``study_id`` join on (study_id, variant_id); rows that only have an
    ``existing_study_id`` join on (existing_study_id, variant_id). The result lists
    study rows, then existing-study rows, then any remaining rows, as gpmapr does.
    """
    rows = list(coloc_groups or [])
    if not associations or not rows:
        return rows

    available = _column_names(associations)
    columns = [column for column in UPLOAD_ASSOCIATION_COLUMNS if column in available]
    study_rows = [row for row in rows if row.get("study_id") is not None]
    existing_rows = [
        row
        for row in rows
        if row.get("study_id") is None and row.get("existing_study_id") is not None
    ]
    other_rows = [
        row for row in rows if row.get("study_id") is None and row.get("existing_study_id") is None
    ]

    merged_rows: list[dict[str, Any]] = []
    for part, key in ((study_rows, "study_id"), (existing_rows, "existing_study_id")):
        if key in available:
            merged_rows.extend(_left_join(part, associations, (key, "variant_id"), columns))
        else:
            merged_rows.extend(part)
    merged_rows.extend(other_rows)
    return merged_rows
