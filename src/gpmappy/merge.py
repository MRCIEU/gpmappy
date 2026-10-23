"""Merge/transformation helpers (mirroring gpmapr's R/common.R)."""

from __future__ import annotations

from typing import Any

# Association columns joined onto coloc groups, rare results and study extractions.
ASSOCIATION_VALUE_COLUMNS = ("beta", "se", "p", "eaf", "imputed")
# Study extraction columns copied onto each side of a coloc pair, as <column>_a and <column>_b.
COLOC_PAIR_DETAIL_COLUMNS = ("trait_name", "data_type", "tissue", "gene")
ASSOCIATION_TABLES = ("coloc_groups", "rare_results", "study_extractions")

Records = list[dict[str, Any]]


def _records(value: Any) -> Records:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _column_names(records: Records) -> list[str]:
    return list(dict.fromkeys(key for record in records for key in record))


def _is(value: Any, target: float) -> bool:
    """``value == target`` for numbers only (so False is not 0), like R's ``%in%``."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == target


def mask_padded_associations(associations: Records) -> Records:
    """Treat placeholder associations as missing.

    The GPMap pipeline stores ``beta = 0, se = 1, p = 1`` (with ``imputed = True``) for
    variants a study did not report, with ``eaf`` from the LD reference panel. These rows
    are kept, with ``beta``, ``se``, ``p`` and ``eaf`` set to None.
    """
    columns = _column_names(associations)
    if not all(column in columns for column in ("beta", "se")):
        return associations
    masked: Records = []
    for row in associations:
        padded = _is(row.get("beta"), 0) and _is(row.get("se"), 1)
        if "p" in columns:
            padded = padded and _is(row.get("p"), 1)
        if "imputed" in columns:
            padded = padded and row.get("imputed") is True
        masked.append(
            {**row, **{column: None for column in ("beta", "se", "p", "eaf") if column in row}}
            if padded
            else row
        )
    return masked


def join_associations(
    table: Any,
    associations: Any,
    table_key: str = "study_id",
    association_key: str = "study_id",
) -> Any:
    """Join each row's association at its variant onto ``table``.

    Rows match on (``table_key``, variant_id) = (``association_key``, variant_id); the
    first association for a key wins and unmatched rows get None. ``table`` is returned
    unchanged when either is empty or lacks the join columns, and columns the table
    already has are not overwritten.
    """
    rows, assoc_rows = _records(table), _records(associations)
    if not rows or not assoc_rows:
        return table
    table_columns, assoc_columns = _column_names(rows), _column_names(assoc_rows)
    if not all(column in table_columns for column in (table_key, "variant_id")) or not all(
        column in assoc_columns for column in (association_key, "variant_id")
    ):
        return table

    value_columns = [
        column
        for column in ASSOCIATION_VALUE_COLUMNS
        if column in assoc_columns and column not in table_columns
    ]
    index: dict[tuple[Any, Any], dict[str, Any]] = {}
    for association in mask_padded_associations(assoc_rows):
        if association.get(association_key) is not None:
            index.setdefault(
                (association[association_key], association.get("variant_id")), association
            )

    joined: Records = []
    for row in rows:
        match = index.get((row.get(table_key), row.get("variant_id")), {})
        joined.append({**row, **{column: match.get(column) for column in value_columns}})
    return joined


def merge_associations(
    coloc_groups: Any,
    rare_results: Any,
    associations: Any,
    study_extractions: Any = None,
) -> tuple[Any, Any, Any]:
    """Coloc groups, rare results and study extractions, each with the association of its study at its variant."""
    return (
        join_associations(coloc_groups, associations),
        join_associations(rare_results, associations),
        join_associations(study_extractions, associations),
    )


def fold_associations(result: dict[str, Any]) -> dict[str, Any]:
    """Join ``result["associations"]`` onto its tables, then drop it."""
    merged = merge_associations(
        result.get("coloc_groups"),
        result.get("rare_results"),
        result.get("associations"),
        result.get("study_extractions"),
    )
    for name, table in zip(ASSOCIATION_TABLES, merged):
        if table is not None:
            result[name] = table
    result.pop("associations", None)
    return result


def fold_upload_associations(result: dict[str, Any]) -> dict[str, Any]:
    """Join a GWAS upload's associations onto its coloc groups and study extractions, then drop them.

    Rows are keyed by ``source``: existing studies by ``study_id``, the uploads' own
    studies by ``gwas_upload_id``.
    """
    associations = _records(result.get("associations"))
    if associations:
        for name in ("coloc_groups", "study_extractions"):
            result[name] = join_upload_associations(result.get(name), associations)
    result.pop("associations", None)
    return result


def join_upload_associations(table: Any, associations: Records) -> Any:
    """Join GWAS upload associations onto a table with a ``source`` column, keeping its row order."""
    rows = _records(table)
    if not rows or "source" not in _column_names(rows):
        return table
    existing = [row for row in associations if row.get("source") == "existing"]
    upload = [row for row in associations if row.get("source") == "upload"]
    joined: Records = []
    for row in rows:
        if row.get("source") == "upload":
            joined.extend(join_associations([row], upload, "gwas_upload_id", "gwas_upload_id"))
        else:
            joined.extend(join_associations([row], existing))
    return _fill_columns(joined)


def _fill_columns(rows: Records) -> Records:
    """Give every row the same columns, as binding data frame rows does."""
    columns = _column_names(rows)
    return [{column: row.get(column) for column in columns} for row in rows]


def _row_source(row: dict[str, Any]) -> Any:
    return row.get("source", "existing")


def add_coloc_pair_details(result: dict[str, Any]) -> dict[str, Any]:
    """Add the trait name, data type, tissue and gene of both sides of each coloc pair.

    A side is identified by ``study_extraction_<side>_id`` together with ``source_<side>``
    (GWAS upload results, where upload and existing study extractions have separate ids),
    or by the id alone (every other result, where all study extractions are existing ones).
    The new ``<column>_a`` / ``<column>_b`` columns follow the id columns, and are None where
    a study extraction isn't in the result.
    """
    pairs = _records(result.get("coloc_pairs"))
    if not pairs:
        return result
    extractions = {
        (_row_source(row), row.get("id")): row for row in _records(result.get("study_extractions"))
    }

    detailed: Records = []
    for pair in pairs:
        details: dict[str, Any] = {}
        for side in ("a", "b"):
            id_column = f"study_extraction_{side}_id"
            if id_column not in pair:
                continue
            source = pair.get(f"source_{side}", "existing")
            extraction = extractions.get((source, pair[id_column]), {})
            for column in COLOC_PAIR_DETAIL_COLUMNS:
                details[f"{column}_{side}"] = extraction.get(column)
        detailed.append(_insert_after_ids(pair, details))
    result["coloc_pairs"] = detailed
    return result


def _insert_after_ids(pair: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    id_columns = {"study_extraction_a_id", "study_extraction_b_id", "source_a", "source_b"}
    last_id = max((i for i, key in enumerate(pair) if key in id_columns), default=None)
    if last_id is None:
        return {**pair, **details}
    items = list(pair.items())
    return dict([*items[: last_id + 1], *details.items(), *items[last_id + 1 :]])
