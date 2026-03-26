"""Merge/transformation helpers."""

from __future__ import annotations

from typing import Any


def _merge_optional(
    left: list[dict[str, Any]] | None,
    associations: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    rows = left or []
    assoc_rows = associations or []
    if not rows or not assoc_rows:
        return rows

    association_index: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in assoc_rows:
        key = (row.get("study_id"), row.get("snp_id"))
        association_index[key] = row

    merged_rows: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("study_id"), row.get("snp_id"))
        assoc = association_index.get(key)
        if assoc is None:
            merged_rows.append(dict(row))
            continue
        enriched = dict(row)
        for assoc_key, assoc_value in assoc.items():
            enriched.setdefault(assoc_key, assoc_value)
        merged_rows.append(enriched)
    return merged_rows


def merge_associations(
    coloc_groups: list[dict[str, Any]] | None,
    rare_results: list[dict[str, Any]] | None,
    associations: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    merged_coloc = _merge_optional(coloc_groups, associations)
    merged_rare = _merge_optional(rare_results, associations)
    return merged_coloc, merged_rare
