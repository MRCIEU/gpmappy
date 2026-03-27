from __future__ import annotations

from typing import Any

import pytest

from gpmappy import tabular
from gpmappy.client import GpmapClient
from gpmappy.exceptions import OptionalDependencyError


def test_all_genes_returns_list_when_dataframe_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GpmapClient()

    def fake_genes_api(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"genes": [{"id": 1, "gene": "WNT7B"}]}

    monkeypatch.setattr("gpmappy.client.genes_api", fake_genes_api)
    result = client.all_genes(as_dataframe=False)
    assert isinstance(result, list)
    assert result[0]["gene"] == "WNT7B"


def test_all_genes_raises_when_dataframe_requested_without_pandas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GpmapClient()

    def fake_genes_api(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"genes": [{"id": 1, "gene": "WNT7B"}]}

    monkeypatch.setattr("gpmappy.client.genes_api", fake_genes_api)
    monkeypatch.setattr(tabular, "_pd", None)

    with pytest.raises(OptionalDependencyError):
        client.all_genes(as_dataframe=True)


def test_gene_coerces_nested_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GpmapClient()

    def fake_gene_api(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "gene": {"gene": "WNT7B"},
            "coloc_groups": [{"study_id": 1, "snp_id": 2}],
            "study_extractions": [{"id": 10, "study_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 2}],
        }

    monkeypatch.setattr("gpmappy.client.gene_api", fake_gene_api)

    result = client.gene("WNT7B")
    if tabular.pandas_available():
        assert hasattr(result["coloc_groups"], "to_dict")
        assert hasattr(result["study_extractions"], "to_dict")
    else:
        assert isinstance(result["coloc_groups"], list)
        assert isinstance(result["study_extractions"], list)
