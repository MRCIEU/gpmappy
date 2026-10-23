from __future__ import annotations

import gzip
import io
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from gpmappy.api.associations import associations_api
from gpmappy.api.genes import gene_api, genes_api, specific_genes_api
from gpmappy.api.gwas import (
    delete_gwas_api,
    get_gwas_api,
    get_gwas_summary_stats_api,
    upload_gwas_api,
)
from gpmappy.api.health import health_api, version_api
from gpmappy.api.ld import (
    ld_matrix_by_variant_api,
    ld_matrix_by_variant_id_api,
    ld_proxies_by_variant_api,
    ld_proxies_by_variant_id_api,
)
from gpmappy.api.pleiotropy import gene_pleiotropies_api, variant_pleiotropies_api
from gpmappy.api.region import region_api
from gpmappy.api.search import search_options_api, search_variants_api
from gpmappy.api.traits import (
    specific_traits_api,
    trait_api,
    trait_associations_full_api,
    trait_coloc_pairs_api,
    trait_duplicates_api,
    traits_api,
)
from gpmappy.api.variants import (
    variant_api,
    variant_summary_stats_api,
    variants_api,
    variants_grange_api,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((method, path, kwargs))
        if path.endswith("/summary-stats"):
            return {"url": "https://example.test/summary.tsv.gz"}
        if path == "/v1/info/version":
            return {"version": "0.0.1"}
        if path.endswith("/coloc-pairs"):
            return {"coloc_pair_column_names": ["variant_id", "h4"], "coloc_pair_rows": [[1, 0.9]]}
        if path.endswith("/associations-full"):
            return {
                "associations_full_column_names": ["variant_id", "p"],
                "associations_full_rows": [[1, 0.01]],
            }
        return {"ok": True, "path": path}

    def request_bytes(self, method: str, path: str, **kwargs: Any) -> bytes:
        self.calls.append((method, path, kwargs))
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
            tsv = b"col1\tcol2\n1\t2\n"
            gz_buf = io.BytesIO()
            with gzip.GzipFile(fileobj=gz_buf, mode="wb") as gz_file:
                gz_file.write(tsv)
            zf.writestr("demo_with_lbfs.tsv.gz", gz_buf.getvalue())
        return mem.getvalue()

    def download_to_path(self, url: str, destination: str | Path) -> Path:
        path = Path(destination)
        with gzip.open(path, "wt") as handle:
            handle.write("a\tb\n3\t4\n")
        return path


def test_api_endpoints_cover_request_shapes() -> None:
    transport = FakeTransport()

    assert health_api(transport)["ok"]
    assert version_api(transport) == "0.0.1"
    assert search_options_api(transport)["ok"]
    assert search_variants_api(transport, "rs123", 0.7)["ok"]

    assert traits_api(transport)["ok"]
    assert specific_traits_api(transport, [1, 2])["ok"]
    assert trait_api(transport, 1, include_associations=True)["ok"]
    assert trait_duplicates_api(transport)["ok"]
    assert trait_coloc_pairs_api(transport, 1, 0.9) == [{"variant_id": 1, "h4": 0.9}]
    assert trait_associations_full_api(transport, 1) == [{"variant_id": 1, "p": 0.01}]

    assert genes_api(transport)["ok"]
    assert specific_genes_api(transport, ["ENSG1"], include_trans=False)["ok"]
    assert gene_api(transport, "ENSG1")["ok"]

    assert variants_api(transport, ["rs1", "rs2"], expand=True)["ok"]
    assert variants_grange_api(transport, "1", 100, 200)["ok"]
    assert variant_api(transport, "rs1")["ok"]
    summary = variant_summary_stats_api(transport, "rs1")
    assert "demo" in summary
    assert summary["demo"][0]["col1"] == "1"

    assert region_api(transport, 1)["ok"]

    assert ld_proxies_by_variant_api(transport, ["rs1"])["ok"]
    assert ld_proxies_by_variant_id_api(transport, [1])["ok"]
    assert ld_matrix_by_variant_api(transport, ["rs1"])["ok"]
    assert ld_matrix_by_variant_id_api(transport, [1])["ok"]

    assert associations_api(transport, [1], [2])["ok"]
    assert gene_pleiotropies_api(transport)["ok"]
    assert variant_pleiotropies_api(transport)["ok"]

    assert get_gwas_api(transport, "ieu-a-2")["ok"]
    assert get_gwas_api(transport, "ieu-a-2", include_associations=True)["ok"]
    assert delete_gwas_api(transport, "guid", "a@b.com")["ok"]
    gwas_stats = get_gwas_summary_stats_api(transport, "ieu-a-2")
    assert gwas_stats[0]["a"] == "3"

    with tempfile.NamedTemporaryFile(delete=False) as handle:
        path = handle.name
    try:
        upload = upload_gwas_api(
            transport,
            file=path,
            name="name",
            p_value_threshold=1e-8,
            column_names={"p": "p"},
            email="a@b.com",
            variable_type="continuous",
            is_published=False,
            doi=None,
            should_be_added=False,
            ancestry="EUR",
            sample_size=10,
            reference_build="GRCh38",
            compare_with_upload_guids=["123e4567-e89b-12d3-a456-426614174000"],
        )
        assert upload["ok"]
    finally:
        Path(path).unlink(missing_ok=True)
