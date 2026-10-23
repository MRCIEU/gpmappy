"""Line up a GWAS upload with another trait (port of gpmapr's R/compare_upload.R)."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from gpmappy.exceptions import ValidationError
from gpmappy.tabular import TableLike, records_to_table
from gpmappy.utils import is_guid

Records = list[dict[str, Any]]


def compare_upload(
    upload: dict[str, Any], trait_id: Any, as_dataframe: bool | None = None
) -> dict[str, TableLike]:
    """Line up a GWAS upload with a trait (or another upload it was compared with).

    ``upload`` is a result of ``get_gwas()`` or ``trait()`` with a GUID, fetched with
    ``include_associations=True``. ``trait_id`` is a trait id, or the GUID of an upload
    named in the upload's ``compare_with_upload_guids``.

    Returns ``coloc_groups``: one row per coloc group with both the upload and the trait,
    giving the lead (smallest p-value) effect of each, on the same alleles; and
    ``coloc_pairs``: the coloc pairs between one of the upload's study extractions and one
    of the trait's, upload first. Both are empty when they don't colocalise.
    """
    groups = _as_records(upload.get("coloc_groups")) if isinstance(upload, dict) else []
    trait = upload.get("trait") if isinstance(upload, dict) else None
    if not isinstance(trait, dict) or trait.get("id") is None or "source" not in _columns(groups):
        raise ValidationError(
            "upload must be a GWAS upload result from get_gwas() or trait() with a GUID"
        )
    if "beta" not in _columns(groups):
        raise ValidationError(
            "upload has no associations: fetch it with include_associations = TRUE, "
            "e.g. get_gwas(guid, include_associations = TRUE)"
        )
    if isinstance(trait_id, (list, tuple)):
        trait_id = trait_id[0] if len(trait_id) == 1 else None
    if trait_id is None:
        raise ValidationError("trait_id must be a single trait id or GWAS upload GUID")

    upload_id = trait["id"]
    extractions = _as_records(upload.get("study_extractions"))

    def is_upload_row(row: dict[str, Any], upload_ids: Iterable[Any]) -> bool:
        return _source(row) == "upload" and row.get("gwas_upload_id") in set(upload_ids)

    if is_guid(trait_id):
        compared_ids = {
            row.get("gwas_upload_id")
            for row in [*groups, *extractions]
            if _source(row) == "upload" and row.get("study") == trait_id
        }
        if not compared_ids:
            raise ValidationError(
                f"trait_id {trait_id} is not a GWAS upload this upload was compared with"
            )

        def is_trait_row(row: dict[str, Any]) -> bool:
            return is_upload_row(row, compared_ids)

    else:

        def is_trait_row(row: dict[str, Any]) -> bool:
            return _source(row) == "existing" and _equal(row.get("trait_id"), trait_id)

    upload_leads = _lead_per_coloc_group([row for row in groups if is_upload_row(row, [upload_id])])
    trait_leads = {
        row["coloc_group_id"]: row
        for row in _lead_per_coloc_group(list(filter(is_trait_row, groups)))
    }
    compared_groups = [
        {
            "coloc_group_id": lead.get("coloc_group_id"),
            "ld_block_id": lead.get("ld_block_id"),
            "ld_block": lead.get("ld_block"),
            "variant_id": lead.get("variant_id"),
            "display_snp": lead.get("display_snp"),
            "h4_connectedness": lead.get("h4_connectedness"),
            "upload_study_extraction_id": lead.get("study_extraction_id"),
            "upload_beta": lead.get("beta"),
            "upload_se": lead.get("se"),
            "upload_p": lead.get("p"),
            "trait_name": trait_leads[lead["coloc_group_id"]].get("trait_name"),
            "trait_study_extraction_id": trait_leads[lead["coloc_group_id"]].get(
                "study_extraction_id"
            ),
            "trait_beta": trait_leads[lead["coloc_group_id"]].get("beta"),
            "trait_se": trait_leads[lead["coloc_group_id"]].get("se"),
            "trait_p": trait_leads[lead["coloc_group_id"]].get("p"),
        }
        for lead in upload_leads
        if lead.get("coloc_group_id") in trait_leads
    ]

    compared_pairs = _compare_pairs(
        _as_records(upload.get("coloc_pairs")),
        extractions,
        own=[row for row in extractions if is_upload_row(row, [upload_id])],
        other=list(filter(is_trait_row, extractions)),
        shared_ld_blocks={row["ld_block_id"] for row in compared_groups},
    )
    return {
        "coloc_groups": records_to_table(compared_groups, as_dataframe=as_dataframe),
        "coloc_pairs": records_to_table(compared_pairs, as_dataframe=as_dataframe),
    }


def _lead_per_coloc_group(rows: Records) -> Records:
    """The row of each coloc group with the smallest p-value (min_p when p is missing), among rows with an effect."""
    with_effect = [row for row in rows if _present(row.get("beta")) and _present(row.get("se"))]

    def order(row: dict[str, Any]) -> tuple[Any, bool, float]:
        p: Any = row.get("p") if _present(row.get("p")) else row.get("min_p")
        return (row.get("coloc_group_id"), not _present(p), float(p) if _present(p) else 0.0)

    leads: dict[Any, dict[str, Any]] = {}
    for row in sorted(with_effect, key=order):
        leads.setdefault(row.get("coloc_group_id"), row)
    return list(leads.values())


def _compare_pairs(
    pairs: Records,
    extractions: Records,
    own: Records,
    other: Records,
    shared_ld_blocks: set[Any],
) -> Records:
    """The coloc pairs between the upload's study extractions and the trait's, with the upload first."""
    if not pairs or not extractions:
        return []
    by_key = {_key(row): row for row in reversed(extractions)}
    own_keys = {_key(row) for row in own}
    other_keys = {_key(row) for row in other}
    compared: Records = []
    for pair in pairs:
        key_a = (pair.get("source_a"), pair.get("study_extraction_a_id"))
        key_b = (pair.get("source_b"), pair.get("study_extraction_b_id"))
        if key_a in own_keys and key_b in other_keys:
            upload_key, trait_key = key_a, key_b
        elif key_b in own_keys and key_a in other_keys:
            upload_key, trait_key = key_b, key_a
        else:
            continue
        upload_row, trait_row = by_key[upload_key], by_key[trait_key]
        compared.append(
            {
                "ld_block_id": pair.get("ld_block_id"),
                "upload_study_extraction_id": upload_row.get("id"),
                "upload_display_snp": upload_row.get("display_snp"),
                "trait_name": trait_row.get("trait_name"),
                "trait_study_extraction_id": trait_row.get("id"),
                "trait_display_snp": trait_row.get("display_snp"),
                "h3": pair.get("h3"),
                "h4": pair.get("h4"),
                "in_shared_coloc_group": pair.get("ld_block_id") in shared_ld_blocks,
            }
        )
    return compared


def _key(row: dict[str, Any]) -> tuple[Any, Any]:
    return (_source(row), row.get("id"))


def _source(row: dict[str, Any]) -> Any:
    return row.get("source", "existing")


def _present(value: Any) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def _equal(value: Any, target: Any) -> bool:
    if not _present(value):
        return False
    try:
        return float(value) == float(target)
    except (TypeError, ValueError):
        return bool(value == target)


def _columns(rows: Records) -> set[str]:
    return {key for row in rows for key in row}


def _as_records(table: Any) -> Records:
    """Records from a list of dicts, a DataFrame, or a list of DataFrames (missing values as None)."""
    if hasattr(table, "to_dict") and hasattr(table, "columns"):
        return [
            {key: None if not _present(value) else value for key, value in row.items()}
            for row in table.to_dict(orient="records")
        ]
    if isinstance(table, list):
        if table and all(hasattr(item, "to_dict") for item in table):
            return [row for item in table for row in _as_records(item)]
        return [row for row in table if isinstance(row, dict)]
    return []
