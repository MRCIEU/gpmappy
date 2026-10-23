"""Association folding, mirroring gpmapr's tests/testthat/test_merge_associations.R."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gpmappy.client import GpmapClient
from gpmappy.merge import fold_upload_associations, mask_padded_associations, merge_associations

UPLOAD_FIXTURE = (
    Path(__file__).parents[1] / "contract" / "gpmapr" / "fixtures" / "gwas-upload-associations.json"
)


def coloc_groups() -> list[dict[str, Any]]:
    return [
        {"coloc_group_id": 1, "study_id": 10, "variant_id": 100},
        {"coloc_group_id": 1, "study_id": 11, "variant_id": 100},
        {"coloc_group_id": 2, "study_id": 12, "variant_id": 200},
    ]


def rare_results() -> list[dict[str, Any]]:
    return [{"rare_result_group_id": 1, "study_id": 13, "variant_id": 300}]


def test_returns_inputs_unchanged_without_associations() -> None:
    assert merge_associations(coloc_groups(), rare_results(), None) == (
        coloc_groups(),
        rare_results(),
        None,
    )


def test_joins_associations_on_study_and_variant() -> None:
    associations = [
        {"study_id": 10, "variant_id": 100, "beta": 0.1},
        {"study_id": 12, "variant_id": 200, "beta": 0.2},
        {"study_id": 13, "variant_id": 300, "beta": 0.3},
        {"study_id": 10, "variant_id": 100, "beta": 9.9},
    ]
    extractions = [
        {"id": 1, "study_id": 10, "variant_id": 100},
        {"id": 2, "study_id": 14, "variant_id": 400},
    ]
    coloc, rare, studies = merge_associations(
        coloc_groups(), rare_results(), associations, extractions
    )
    assert [row["beta"] for row in coloc] == [0.1, None, 0.2]
    assert [row["beta"] for row in rare] == [0.3]
    assert [row["beta"] for row in studies] == [0.1, None]


def test_does_not_overwrite_columns_the_table_has() -> None:
    coloc, _, _ = merge_associations(
        [{"study_id": 10, "variant_id": 100, "beta": 1.0}],
        None,
        [{"study_id": 10, "variant_id": 100, "beta": 0.1, "se": 0.01}],
    )
    assert coloc == [{"study_id": 10, "variant_id": 100, "beta": 1.0, "se": 0.01}]


def test_functions_fold_the_associations_into_their_tables_and_drop_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gpmappy.client.gene_api",
        lambda *_a, **_k: {
            "coloc_groups": coloc_groups(),
            "study_extractions": [{"id": 1, "study_id": 10, "variant_id": 100}],
            "associations": [{"study_id": 10, "variant_id": 100, "beta": 0.1, "se": 0.01}],
        },
    )
    result = GpmapClient().gene("WNT7B", include_associations=True, as_dataframe=False)
    assert "associations" not in result
    assert [row["beta"] for row in result["coloc_groups"]] == [0.1, None, None]
    assert result["study_extractions"][0]["se"] == 0.01  # noqa: PLR2004


def test_gwas_upload_associations_are_folded_in_by_source() -> None:
    result = fold_upload_associations(json.loads(UPLOAD_FIXTURE.read_text()))
    assert "associations" not in result
    groups = result["coloc_groups"]

    def betas(rows: list[dict[str, Any]], **match: Any) -> list[Any]:
        return [row["beta"] for row in rows if all(row.get(k) == v for k, v in match.items())]

    # Existing rows join on study_id, upload rows on gwas_upload_id; the same id in each must not mix.
    assert betas(groups, source="upload", gwas_upload_id=90) == [0.5, 0.3]
    assert betas(groups, source="upload", gwas_upload_id=144) == [0.45]
    assert betas(groups, source="existing", trait_id=2527) == [0.2]
    extractions = result["study_extractions"]
    assert betas(extractions, source="upload", id=7223) == [0.5]
    assert betas(extractions, source="existing", id=7223) == [None]
    # a placeholder association comes back as missing
    assert betas(groups, source="existing", study_extraction_id=7223) == [None]


def test_placeholder_associations_are_returned_as_missing() -> None:
    associations = [
        {"variant_id": 1, "study_id": 1, "beta": 0, "se": 1, "p": 1, "eaf": 0.3, "imputed": True},
        {
            "variant_id": 2,
            "study_id": 1,
            "beta": 0,
            "se": 0.5,
            "p": 0.9,
            "eaf": 0.3,
            "imputed": True,
        },
        {
            "variant_id": 3,
            "study_id": 1,
            "beta": 0.2,
            "se": 1,
            "p": 1e-3,
            "eaf": 0.3,
            "imputed": False,
        },
        {"variant_id": 4, "study_id": 1, "beta": 0, "se": 1, "p": 1, "eaf": 0.3, "imputed": False},
    ]
    masked = mask_padded_associations(associations)
    assert [row["beta"] for row in masked] == [None, 0, 0.2, 0]
    assert [row["eaf"] for row in masked] == [None, 0.3, 0.3, 0.3]
    assert [row["imputed"] for row in masked] == [True, True, False, False]
    assert mask_padded_associations([{"variant_id": 1, "beta": 0}]) == [
        {"variant_id": 1, "beta": 0}
    ]


@pytest.mark.parametrize("method", ["region", "gene", "trait", "variant"])
def test_works_when_the_api_returns_no_associations(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    payload = {"coloc_groups": coloc_groups(), "rare_results": rare_results()}
    monkeypatch.setattr(f"gpmappy.client.{method}_api", lambda *_a, **_k: dict(payload))
    client = GpmapClient()
    kwargs: dict[str, Any] = {"as_dataframe": False}
    if method != "variant":
        kwargs["include_associations"] = True
    result = getattr(client, method)(1, **kwargs)
    assert result["coloc_groups"] == coloc_groups()
