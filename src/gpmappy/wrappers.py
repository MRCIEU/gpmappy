"""Module-level convenience wrappers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from gpmappy.client import GpmapClient

_default_client = GpmapClient()


def get_default_client() -> GpmapClient:
    return _default_client


def set_default_client(client: GpmapClient) -> None:
    global _default_client
    _default_client = client


def select_api(api: str = "production") -> None:
    _default_client.select_api(api)


def health_api() -> dict[str, object]:
    return _default_client.health_api()


def version_api() -> str:
    return _default_client.version_api()


def search_gpmap(search_text: str, rsquared_threshold: float = 0.8) -> pd.DataFrame:
    return _default_client.search_gpmap(search_text, rsquared_threshold)


def all_traits() -> pd.DataFrame:
    return _default_client.all_traits()


def trait(
    trait_id: str | int,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.trait(trait_id, include_associations, include_coloc_pairs, h4_threshold)


def traits(
    trait_ids: list[str | int],
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.traits(trait_ids, include_associations, include_coloc_pairs, h4_threshold)


def all_genes() -> pd.DataFrame:
    return _default_client.all_genes()


def gene(
    gene_id: str,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    include_trans: bool = True,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.gene(
        gene_id,
        include_associations=include_associations,
        include_coloc_pairs=include_coloc_pairs,
        include_trans=include_trans,
        h4_threshold=h4_threshold,
    )


def genes(
    gene_ids: list[str],
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    include_trans: bool = True,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.genes(
        gene_ids,
        include_associations=include_associations,
        include_coloc_pairs=include_coloc_pairs,
        include_trans=include_trans,
        h4_threshold=h4_threshold,
    )


def variant(
    snp_id: str | int,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
    include_summary_stats: bool = False,
) -> dict[str, Any]:
    return _default_client.variant(
        snp_id,
        include_coloc_pairs=include_coloc_pairs,
        h4_threshold=h4_threshold,
        include_summary_stats=include_summary_stats,
    )


def variants(
    variants: list[str | int],
    expand: bool = False,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.variants(
        variants,
        expand=expand,
        include_associations=include_associations,
        include_coloc_pairs=include_coloc_pairs,
        h4_threshold=h4_threshold,
    )


def region(
    region_id: str | int,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return _default_client.region(region_id, include_associations, include_coloc_pairs, h4_threshold)


def ld_matrix(variant_ids: list[str | int]) -> dict[str, Any]:
    return _default_client.ld_matrix(variant_ids)


def ld_proxies(variant_ids: list[str | int]) -> dict[str, Any]:
    return _default_client.ld_proxies(variant_ids)


def associations(snp_ids: list[int], study_ids: list[int]) -> pd.DataFrame:
    return _default_client.associations(snp_ids, study_ids)


def get_all_gene_pleiotropies() -> pd.DataFrame:
    return _default_client.get_all_gene_pleiotropies()


def get_all_snp_pleiotropies() -> pd.DataFrame:
    return _default_client.get_all_snp_pleiotropies()


def get_gwas(gwas_id: str, include_summary_stats: bool = False) -> dict[str, Any]:
    return _default_client.get_gwas(gwas_id, include_summary_stats=include_summary_stats)


def upload_gwas(
    file: str,
    name: str,
    p_value_threshold: float = 5e-8,
    column_names: dict[str, str] | None = None,
    email: str | None = None,
    category: str = "continuous",
    is_published: bool = False,
    doi: str | None = None,
    should_be_added: bool = False,
    ancestry: str = "EUR",
    sample_size: int | float | None = None,
    reference_build: str = "GRCh38",
) -> dict[str, Any]:
    return _default_client.upload_gwas(
        file=file,
        name=name,
        p_value_threshold=p_value_threshold,
        column_names=column_names,
        email=email,
        category=category,
        is_published=is_published,
        doi=doi,
        should_be_added=should_be_added,
        ancestry=ancestry,
        sample_size=sample_size,
        reference_build=reference_build,
    )
