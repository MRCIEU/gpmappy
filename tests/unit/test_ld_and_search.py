"""r-squared in LD results and variant searches, mirroring gpmapr's test_ld.R and test_search_gpmap.R."""

from __future__ import annotations

from typing import Any

import pytest

from gpmappy.client import GpmapClient


def test_ld_proxies_and_matrix_add_the_r_squared(monkeypatch: pytest.MonkeyPatch) -> None:
    lds = {"lds": [{"lead_variant_id": 1, "proxy_variant_id": 2, "r": 0.9411}]}
    monkeypatch.setattr("gpmappy.client.ld_proxies_by_variant_id_api", lambda *_a: dict(lds))
    monkeypatch.setattr("gpmappy.client.ld_matrix_by_variant_api", lambda *_a: dict(lds))
    client = GpmapClient()
    assert client.ld_proxies([1])["lds"][0]["rsq"] == 0.89  # noqa: PLR2004
    assert client.ld_matrix(["rs1"])["lds"][0]["rsq"] == 0.89  # noqa: PLR2004


def test_ld_matrix_returns_an_empty_table_when_no_pairs_are_stored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("gpmappy.client.ld_matrix_by_variant_id_api", lambda *_a: {"lds": None})
    assert GpmapClient().ld_matrix([5553693, 80717]) == {"lds": []}


def test_variant_search_reports_each_proxys_own_counts_and_r_squared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def variant(vid: int, groups: int, r: list[float]) -> dict[str, Any]:
        return {
            "id": vid,
            "display_snp": f"rs{vid}",
            "num_colocs": groups,
            "coloc_groups": [{}] * groups,
            "rare_results": [],
            "ld_proxies": [{"r": value} for value in r],
        }

    monkeypatch.setattr(
        "gpmappy.client.search_variants_api",
        lambda *_a: {
            "original_variants": [variant(1, 1, [])],
            "proxy_variants": [variant(2, 2, [0.5, -0.95]), variant(3, 5, [])],
        },
    )
    rows = GpmapClient().search_gpmap("rs1", as_dataframe=False)
    assert [row["type_id"] for row in rows] == [1, 3, 2]
    assert [row["rsq"] for row in rows] == [None, None, 0.9]
    assert [row["num_coloc_studies"] for row in rows] == [1, 5, 2]
