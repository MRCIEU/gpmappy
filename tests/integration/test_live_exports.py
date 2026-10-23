"""Live checks of every export, mirroring gpmapr's tests/testthat/test_exported_functions.R.

Run with ``pytest --run-live`` (or GPMAPPY_RUN_LIVE=1); they are skipped otherwise. They
use the API at $GPMAP_URL (default: production), e.g. GPMAP_URL=http://localhost:8000.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

from gpmappy import (
    GpmapClient,
    all_genes,
    all_traits,
    associations,
    delete_gwas,
    gene,
    genes,
    get_all_gene_pleiotropies,
    get_all_variant_pleiotropies,
    get_default_client,
    gpmap_available,
    health_api,
    ld_matrix,
    ld_proxies,
    search_gpmap,
    set_default_client,
    trait,
    trait_duplicates,
    traits,
    variant,
    variants,
)
from gpmappy.config import GpmapConfig
from gpmappy.constants import PRODUCTION_BASE_URL
from gpmappy.exceptions import ApiError

pytestmark = [pytest.mark.integration, pytest.mark.live]

TRAIT_ID = 5020
VARIANT_ID = 5553693


@pytest.fixture(scope="module", autouse=True)
def live_client() -> Iterator[None]:
    original = get_default_client()
    set_default_client(
        GpmapClient(GpmapConfig(base_url=os.environ.get("GPMAP_URL", PRODUCTION_BASE_URL)))
    )
    yield
    set_default_client(original)


def _column(rows: list[dict[str, Any]], name: str) -> list[Any]:
    return [row.get(name) for row in rows]


def test_health_api() -> None:
    assert health_api()["status"] in {"healthy", "unhealthy"}


def test_gpmap_available() -> None:
    assert gpmap_available()


def test_all_traits_and_trait_have_pipeline_id_and_variable_type() -> None:
    assert {"pipeline_id", "variable_type"} <= set(all_traits(as_dataframe=False)[0])
    result = trait(TRAIT_ID, as_dataframe=False)
    assert isinstance(result["trait"]["pipeline_id"], str)
    assert result["trait"]["source_url"].startswith("https://opengwas.io/datasets/")


def test_associations_are_folded_into_the_tables() -> None:
    result = trait(TRAIT_ID, include_associations=True, as_dataframe=False)
    assert "associations" not in result
    assert {"beta", "se"} <= set(result["coloc_groups"][0])
    assert {"beta", "se"} <= set(result["study_extractions"][0])


def test_ld_results_have_r_squared() -> None:
    pairs = ld_matrix([VARIANT_ID, 5553688])["lds"]
    assert pairs
    assert all(pair["rsq"] == round(pair["r"] ** 2, 2) for pair in pairs)
    assert ld_matrix([VARIANT_ID, 80717])["lds"] == []
    assert {"r", "rsq"} <= set(ld_proxies([VARIANT_ID])["lds"][0])


def test_search_gpmap() -> None:
    result = search_gpmap("haemoglobin", as_dataframe=False)
    assert result
    expected = {
        "call",
        "name",
        "type",
        "type_id",
        "num_coloc_groups",
        "num_coloc_studies",
        "num_rare_results",
        "num_study_extractions",
    }
    assert expected <= set(result[0])


def test_search_gpmap_orders_by_coloc_groups_and_rare_results() -> None:
    result = search_gpmap("haemoglobin", as_dataframe=False)
    importance = [
        (row.get("num_coloc_groups") or 0) + (row.get("num_rare_results") or 0) for row in result
    ]
    assert importance == sorted(importance, reverse=True)


def test_trait() -> None:
    result = trait(TRAIT_ID, as_dataframe=False)
    assert result["trait"]["id"] == TRAIT_ID
    assert result["coloc_groups"]


def test_trait_full_associations() -> None:
    result = trait(TRAIT_ID, include_full_associations=True, as_dataframe=False)
    full = result["full_associations"]
    assert full
    assert {"variant_id", "study_id", "beta", "se", "p", "eaf", "imputed"} <= set(full[0])


def test_variant() -> None:
    result = variant(VARIANT_ID, as_dataframe=False)
    assert result["variant"]["id"] == VARIANT_ID
    assert result["coloc_groups"]


def test_gene() -> None:
    result = gene("WNT7B", as_dataframe=False)
    assert result["gene"]["gene"] == "WNT7B"
    assert result["coloc_groups"]


def test_associations() -> None:
    variant_ids, study_ids = [80750], [5020, 4870]
    result = associations(variant_ids, study_ids, as_dataframe=False)
    assert all(row["variant_id"] in variant_ids for row in result)
    assert all(row["study_id"] in study_ids for row in result)


def test_pleiotropies() -> None:
    assert get_all_gene_pleiotropies(as_dataframe=False)
    assert get_all_variant_pleiotropies(as_dataframe=False)


def test_all_genes_and_traits() -> None:
    assert all_genes(as_dataframe=False)
    assert all_traits(as_dataframe=False)


def test_traits() -> None:
    trait_ids = [4405, 4872]
    result = traits(trait_ids, include_associations=True, as_dataframe=False)
    assert set(_column(result["traits"], "id")) <= set(trait_ids)
    assert result["coloc_groups"]
    assert result["study_extractions"]


def test_genes() -> None:
    gene_ids = ["WNT7B", "WNT7A"]
    result = genes(gene_ids, include_associations=True, as_dataframe=False)
    assert set(_column(result["genes"], "gene")) <= set(gene_ids)
    assert result["coloc_groups"]
    assert result["study_extractions"]


def test_variants() -> None:
    variant_ids = [VARIANT_ID, 5553694]
    result = variants(variant_ids, expand=True, include_associations=True, as_dataframe=False)
    assert set(_column(result["variants"], "id")) <= set(variant_ids)
    assert result["coloc_groups"]
    assert result["study_extractions"]


def test_trait_duplicates() -> None:
    result = trait_duplicates(as_dataframe=False)
    assert result
    # Older API versions name each duplicate's parent; newer ones list duplicate groups.
    parent_shape = {"trait_id", "trait_name", "parent_trait_id", "parent_trait_name"}
    group_shape = {"trait_id", "trait_name", "duplicate_group", "is_representative"}
    assert parent_shape <= set(result[0]) or group_shape <= set(result[0])


def test_delete_gwas_surfaces_api_errors() -> None:
    with pytest.raises(ApiError, match="not found"):
        delete_gwas("00000000-0000-0000-0000-000000000000", "user@example.com")
