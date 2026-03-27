from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gpmappy.client import GpmapClient
from gpmappy.exceptions import ValidationError


@pytest.fixture
def patched_client(monkeypatch: pytest.MonkeyPatch) -> GpmapClient:
    monkeypatch.setattr("gpmappy.client.health_api", lambda _: {"status": "ok"})
    monkeypatch.setattr("gpmappy.client.version_api", lambda _: "1.0.0")

    monkeypatch.setattr("gpmappy.client.traits_api", lambda _: {"traits": [{"id": 1}]})
    monkeypatch.setattr("gpmappy.client.genes_api", lambda _: {"genes": [{"id": "ENSG1"}]})
    monkeypatch.setattr(
        "gpmappy.client.associations_api",
        lambda *_args, **_kwargs: {"associations": [{"snp_id": 1}]},
    )
    monkeypatch.setattr(
        "gpmappy.client.gene_pleiotropies_api", lambda _: {"genes": [{"gene": "A"}]}
    )
    monkeypatch.setattr("gpmappy.client.snp_pleiotropies_api", lambda _: {"snps": [{"snp": "rs1"}]})

    monkeypatch.setattr(
        "gpmappy.client.trait_api",
        lambda *_args, **_kwargs: {
            "trait": {"trait": "ieu-a-2"},
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.1}],
        },
    )
    monkeypatch.setattr(
        "gpmappy.client.trait_coloc_pairs_api", lambda *_args, **_kwargs: [{"pair": 1}]
    )
    monkeypatch.setattr(
        "gpmappy.client.specific_traits_api",
        lambda *_args, **_kwargs: {
            "traits": [{"id": 1}],
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "study_extractions": [{"id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
        },
    )
    monkeypatch.setattr(
        "gpmappy.client.get_gwas_api",
        lambda *_args, **_kwargs: {
            "trait": {"id": 99, "trait": "uploaded"},
            "coloc_groups": [{"study_id": 2, "snp_id": 2}],
            "study_extractions": [{"id": 2}],
            "rare_results": [{"study_id": 2, "snp_id": 2}],
        },
    )

    monkeypatch.setattr(
        "gpmappy.client.gene_api",
        lambda *_args, **_kwargs: {
            "gene": {"id": "ENSG1"},
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.2}],
            "tissues": ["x"],
        },
    )
    monkeypatch.setattr(
        "gpmappy.client.specific_genes_api",
        lambda *_args, **_kwargs: {
            "genes": [{"id": "ENSG1"}],
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.2}],
        },
    )

    monkeypatch.setattr(
        "gpmappy.client.region_api",
        lambda *_args, **_kwargs: {
            "region": {"id": 1},
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.2}],
            "tissues": ["x"],
        },
    )

    monkeypatch.setattr(
        "gpmappy.client.variant_api",
        lambda *_args, **_kwargs: {
            "variant": {"id": 1},
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.2}],
        },
    )
    monkeypatch.setattr(
        "gpmappy.client.variant_summary_stats_api",
        lambda *_args, **_kwargs: {"stats": [{"a": "1"}]},
    )
    monkeypatch.setattr(
        "gpmappy.client.variants_api",
        lambda *_args, **_kwargs: {
            "variants": [{"id": 1}],
            "coloc_groups": [{"study_id": 1, "snp_id": 1}],
            "rare_results": [{"study_id": 1, "snp_id": 1}],
            "associations": [{"study_id": 1, "snp_id": 1, "beta": 0.2}],
        },
    )

    monkeypatch.setattr(
        "gpmappy.client.ld_matrix_by_snp_id_api", lambda *_args, **_kwargs: {"kind": "snp"}
    )
    monkeypatch.setattr(
        "gpmappy.client.ld_matrix_by_variant_api", lambda *_args, **_kwargs: {"kind": "variant"}
    )
    monkeypatch.setattr(
        "gpmappy.client.ld_proxies_by_snp_id_api", lambda *_args, **_kwargs: {"kind": "snp"}
    )
    monkeypatch.setattr(
        "gpmappy.client.ld_proxies_by_variant_api", lambda *_args, **_kwargs: {"kind": "variant"}
    )

    monkeypatch.setattr(
        "gpmappy.client.get_gwas_summary_stats_api", lambda *_args, **_kwargs: [{"a": "1"}]
    )
    monkeypatch.setattr(
        "gpmappy.client.upload_gwas_api", lambda *_args, **_kwargs: {"uploaded": True}
    )

    monkeypatch.setattr(
        "gpmappy.client.search_variants_api",
        lambda *_args, **_kwargs: {
            "original_variants": [
                {
                    "display_snp": "rs1",
                    "id": 1,
                    "num_colocs": 1,
                    "coloc_groups": [{}],
                    "rare_results": [{}],
                }
            ],
            "proxy_variants": [
                {
                    "display_snp": "rs2",
                    "id": 2,
                    "num_colocs": 1,
                    "coloc_groups": [{}],
                    "rare_results": [{}],
                    "ld_proxies": [{"r": 0.5}],
                }
            ],
        },
    )
    monkeypatch.setattr(
        "gpmappy.client.search_options_api",
        lambda *_args, **_kwargs: {
            "search_terms": [
                {"type": "gene", "type_id": "ENSG1", "name": "BRCA1", "alt_name": "GeneA"},
                {"type": "trait", "type_id": 1, "name": "haemoglobin", "alt_name": "hb"},
            ]
        },
    )

    return GpmapClient()


def test_client_happy_paths(patched_client: GpmapClient) -> None:
    client = patched_client
    assert client.health_api()["status"] == "ok"
    assert client.version_api() == "1.0.0"

    assert isinstance(client.all_traits(as_dataframe=False), list)
    assert isinstance(client.all_genes(as_dataframe=False), list)
    assert isinstance(client.associations([1], [2], as_dataframe=False), list)
    assert isinstance(client.get_all_gene_pleiotropies(as_dataframe=False), list)
    assert isinstance(client.get_all_snp_pleiotropies(as_dataframe=False), list)

    t = client.trait(1, include_associations=True, include_coloc_pairs=True, as_dataframe=False)
    assert "coloc_pairs" in t
    assert "source_url" in t["trait"]
    t_guid = client.trait("123e4567-e89b-12d3-a456-426614174000", as_dataframe=False)
    assert t_guid["trait"]["trait"] == "uploaded"

    tr = client.traits(
        [1, "123e4567-e89b-12d3-a456-426614174000"], include_coloc_pairs=True, as_dataframe=False
    )
    assert "traits" in tr

    assert "gene" in client.gene("ENSG1", include_associations=True, as_dataframe=False)
    assert "genes" in client.genes(["ENSG1"], include_associations=True, as_dataframe=False)
    assert "region" in client.region(1, include_associations=True, as_dataframe=False)
    assert "variant" in client.variant("rs1", include_summary_stats=True, as_dataframe=False)
    assert "variants" in client.variants(
        ["rs1"], expand=True, include_associations=True, as_dataframe=False
    )

    assert client.ld_matrix([1])["kind"] == "snp"
    assert client.ld_matrix(["rs1"])["kind"] == "variant"
    assert client.ld_proxies([1])["kind"] == "snp"
    assert client.ld_proxies(["rs1"])["kind"] == "variant"

    assert "summary_stats" in client.get_gwas(
        "ieu-a-2", include_summary_stats=True, as_dataframe=False
    )

    with tempfile.NamedTemporaryFile(delete=False) as handle:
        path = Path(handle.name)
    try:
        uploaded = client.upload_gwas(
            file=str(path),
            name="ok",
            email="a@b.com",
            sample_size=10,
        )
        assert uploaded["uploaded"]
    finally:
        path.unlink(missing_ok=True)

    assert isinstance(client.search_gpmap("rs1", as_dataframe=False), list)
    assert isinstance(client.search_gpmap("haemoglobin", as_dataframe=False), list)


def test_client_validation_paths(patched_client: GpmapClient) -> None:
    client = patched_client

    with pytest.raises(ValidationError):
        client.select_api("bad")
    with pytest.raises(ValidationError):
        client.trait(None)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        client.traits([])
    with pytest.raises(ValidationError):
        client.genes([])
    with pytest.raises(ValidationError):
        client.region(None)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        client.variant(None)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        client.variants([])
    with pytest.raises(ValidationError):
        client.ld_matrix([])
    with pytest.raises(ValidationError):
        client.ld_proxies([])
    with pytest.raises(ValidationError):
        client.get_gwas("")
    with pytest.raises(ValidationError):
        client.search_gpmap("")
    with pytest.raises(ValidationError):
        client.search_gpmap("abc", rsquared_threshold=2)
