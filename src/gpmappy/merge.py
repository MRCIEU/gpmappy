"""Merge/transformation helpers."""

from __future__ import annotations

import pandas as pd


def _merge_optional(
    left: pd.DataFrame | None,
    associations: pd.DataFrame | None,
) -> pd.DataFrame | None:
    if left is None or left.empty or associations is None or associations.empty:
        return left
    return left.merge(associations, on=["study_id", "snp_id"], how="left")


def merge_associations(
    coloc_groups: pd.DataFrame | None,
    rare_results: pd.DataFrame | None,
    associations: pd.DataFrame | None,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    merged_coloc = _merge_optional(coloc_groups, associations)
    merged_rare = _merge_optional(rare_results, associations)
    return merged_coloc, merged_rare
