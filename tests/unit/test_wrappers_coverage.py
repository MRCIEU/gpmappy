from __future__ import annotations

from typing import Any

import gpmappy.wrappers as w

MIN_EXPECTED_WRAPPER_CALLS = 20


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, method_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((method_name, args, kwargs))
        return {"method": method_name, "args": list(args), "kwargs": kwargs}

    def select_api(self, api: str = "production") -> None:
        self.calls.append(("select_api", (api,), {}))

    def health_api(self) -> dict[str, Any]:
        return self._record("health_api")

    def version_api(self) -> str:
        self.calls.append(("version_api", (), {}))
        return "v-test"

    def search_gpmap(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("search_gpmap", *args, **kwargs)

    def all_traits(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("all_traits", *args, **kwargs)

    def trait(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("trait", *args, **kwargs)

    def traits(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("traits", *args, **kwargs)

    def all_genes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("all_genes", *args, **kwargs)

    def gene(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("gene", *args, **kwargs)

    def genes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("genes", *args, **kwargs)

    def variant(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("variant", *args, **kwargs)

    def variants(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("variants", *args, **kwargs)

    def region(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("region", *args, **kwargs)

    def ld_matrix(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("ld_matrix", *args, **kwargs)

    def ld_proxies(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("ld_proxies", *args, **kwargs)

    def associations(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("associations", *args, **kwargs)

    def get_all_gene_pleiotropies(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("get_all_gene_pleiotropies", *args, **kwargs)

    def get_all_snp_pleiotropies(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("get_all_snp_pleiotropies", *args, **kwargs)

    def get_all_variant_pleiotropies(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("get_all_variant_pleiotropies", *args, **kwargs)

    def trait_duplicates(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("trait_duplicates", *args, **kwargs)

    def delete_gwas(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("delete_gwas", *args, **kwargs)

    def get_gwas(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("get_gwas", *args, **kwargs)

    def upload_gwas(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("upload_gwas", *args, **kwargs)


def test_wrappers_delegate_to_default_client() -> None:
    original = w.get_default_client()
    dummy = DummyClient()
    w.set_default_client(dummy)
    try:
        w.select_api("staging")
        assert w.health_api()["method"] == "health_api"
        assert w.version_api() == "v-test"

        assert w.search_gpmap("BRCA1", 0.7, as_dataframe=True)["method"] == "search_gpmap"
        assert w.all_traits(as_dataframe=False)["method"] == "all_traits"
        assert w.trait(1, True, True, True, 0.9, None)["method"] == "trait"
        assert w.trait_duplicates(False)["method"] == "trait_duplicates"
        assert w.traits([1, 2], False, False, 0.8, True)["method"] == "traits"

        assert w.all_genes()["method"] == "all_genes"
        assert w.gene("ENSG000001", True, False, True, 0.7, False)["method"] == "gene"
        assert w.genes(["ENSG1", "ENSG2"], False, False, False, 0.8, True)["method"] == "genes"

        assert w.variant("rs123", True, 0.8, True, False)["method"] == "variant"
        assert w.variants(["rs123", "rs124"], True, True, True, 0.8, None)["method"] == "variants"
        assert w.region("1:100-200", True, False, 0.8, True)["method"] == "region"

        assert w.ld_matrix([1, 2])["method"] == "ld_matrix"
        assert w.ld_proxies(["rs1", "rs2"])["method"] == "ld_proxies"

        assert w.associations([1, 2], [10, 11], None)["method"] == "associations"
        assert w.get_all_gene_pleiotropies(True)["method"] == "get_all_gene_pleiotropies"
        assert w.get_all_snp_pleiotropies(False)["method"] == "get_all_snp_pleiotropies"
        assert w.get_all_variant_pleiotropies(False)["method"] == "get_all_variant_pleiotropies"
        assert w.get_gwas("ieu-a-2", True, True, None)["method"] == "get_gwas"
        assert w.delete_gwas("guid", "a@b.com")["method"] == "delete_gwas"

        upload = w.upload_gwas(
            file="x.tsv",
            name="test",
            p_value_threshold=1e-8,
            column_names={"p": "p"},
            email="a@b.com",
            category="continuous",
            is_published=False,
            doi=None,
            should_be_added=False,
            ancestry="EUR",
            sample_size=123,
            reference_build="GRCh38",
            compare_with_upload_guids=None,
            chr_col="chr",
        )
        assert upload["method"] == "upload_gwas"

        method_names = [entry[0] for entry in dummy.calls]
        assert "select_api" in method_names
        assert "upload_gwas" in method_names
        assert "search_gpmap" in method_names
        assert len(method_names) >= MIN_EXPECTED_WRAPPER_CALLS
    finally:
        w.set_default_client(original)
