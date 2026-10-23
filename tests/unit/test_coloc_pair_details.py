"""Coloc pair details, mirroring gpmapr's tests/testthat/test_coloc_pair_details.R."""

from __future__ import annotations

from typing import Any

import pytest

from gpmappy.client import GpmapClient
from gpmappy.merge import add_coloc_pair_details

EXISTING_EXTRACTIONS = [
    {"id": 10, "trait_name": "LDL cholesterol", "data_type": "Phenotype", "tissue": None},
    {
        "id": 20,
        "trait_name": "PCSK9 Liver eQTL",
        "data_type": "Gene Expression",
        "tissue": "Liver",
        "gene": "PCSK9",
    },
]


def test_both_sides_get_their_study_extraction_details_after_the_id_columns() -> None:
    result = add_coloc_pair_details(
        {
            "coloc_pairs": [
                {
                    "variant_id": 1,
                    "study_extraction_a_id": 10,
                    "study_extraction_b_id": 20,
                    "h4": 0.9,
                }
            ],
            "study_extractions": EXISTING_EXTRACTIONS,
        }
    )
    pair = result["coloc_pairs"][0]
    assert list(pair) == [
        "variant_id",
        "study_extraction_a_id",
        "study_extraction_b_id",
        "trait_name_a",
        "data_type_a",
        "tissue_a",
        "gene_a",
        "trait_name_b",
        "data_type_b",
        "tissue_b",
        "gene_b",
        "h4",
    ]
    assert pair["trait_name_a"] == "LDL cholesterol"
    assert pair["trait_name_b"] == "PCSK9 Liver eQTL"
    assert pair["tissue_b"] == "Liver"
    assert "source_a" not in pair


def test_a_study_extraction_missing_from_the_response_gives_missing_details() -> None:
    pairs = add_coloc_pair_details(
        {
            "coloc_pairs": [
                {"study_extraction_a_id": 10, "study_extraction_b_id": 20},
                {"study_extraction_a_id": 99, "study_extraction_b_id": 20},
            ],
            "study_extractions": EXISTING_EXTRACTIONS,
        }
    )["coloc_pairs"]
    assert [pair["trait_name_a"] for pair in pairs] == ["LDL cholesterol", None]
    assert [pair["trait_name_b"] for pair in pairs] == ["PCSK9 Liver eQTL"] * 2


def test_upload_pairs_are_matched_by_source_and_id() -> None:
    # Upload and existing study extractions have separate ids: 7223 is both here.
    pairs = add_coloc_pair_details(
        {
            "coloc_pairs": [
                {
                    "study_extraction_a_id": 7223,
                    "source_a": "upload",
                    "study_extraction_b_id": 10,
                    "source_b": "existing",
                    "h4": 0.9,
                },
                {
                    "study_extraction_a_id": 7223,
                    "source_a": "upload",
                    "study_extraction_b_id": 7223,
                    "source_b": "existing",
                    "h4": 0.95,
                },
                {
                    "study_extraction_a_id": 10,
                    "source_a": "existing",
                    "study_extraction_b_id": 7223,
                    "source_b": "upload",
                    "h4": 0.85,
                },
            ],
            "study_extractions": [
                {"id": 10, "source": "existing", "trait_name": "LDL cholesterol"},
                {"id": 7223, "source": "existing", "trait_name": "Granulocyte percentage"},
                {"id": 7223, "source": "upload", "gwas_upload_id": 90, "trait_name": "My GWAS"},
            ],
        }
    )["coloc_pairs"]
    assert [p["trait_name_a"] for p in pairs] == ["My GWAS", "My GWAS", "LDL cholesterol"]
    assert [p["trait_name_b"] for p in pairs] == [
        "LDL cholesterol",
        "Granulocyte percentage",
        "My GWAS",
    ]
    keys = list(pairs[0])
    assert keys.index("trait_name_a") == keys.index("source_b") + 1


def test_results_without_coloc_pairs_are_unchanged() -> None:
    result: dict[str, Any] = {"coloc_groups": [{"id": 1}], "coloc_pairs": []}
    assert add_coloc_pair_details(dict(result)) == result
    assert add_coloc_pair_details({"trait": {"id": 1}}) == {"trait": {"id": 1}}


def test_trait_coloc_pairs_are_left_without_details(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gpmappy.client.trait_api",
        lambda *_a, **_k: {"trait": {"id": 1}, "study_extractions": EXISTING_EXTRACTIONS},
    )
    monkeypatch.setattr(
        "gpmappy.client.trait_coloc_pairs_api",
        lambda *_a, **_k: [{"study_extraction_a_id": 10, "study_extraction_b_id": 20}],
    )
    result = GpmapClient().trait(1, include_coloc_pairs=True, as_dataframe=False)
    assert list(result["coloc_pairs"][0]) == ["study_extraction_a_id", "study_extraction_b_id"]
