"""Client implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from gpmappy.api.associations import associations_api
from gpmappy.api.genes import gene_api, genes_api, specific_genes_api
from gpmappy.api.gwas import get_gwas_api, get_gwas_summary_stats_api, upload_gwas_api
from gpmappy.api.health import health_api, version_api
from gpmappy.api.ld import (
    ld_matrix_by_snp_id_api,
    ld_matrix_by_variant_api,
    ld_proxies_by_snp_id_api,
    ld_proxies_by_variant_api,
)
from gpmappy.api.pleiotropy import gene_pleiotropies_api, snp_pleiotropies_api
from gpmappy.api.region import region_api
from gpmappy.api.search import search_options_api, search_variants_api
from gpmappy.api.traits import specific_traits_api, trait_api, trait_coloc_pairs_api, traits_api
from gpmappy.api.variants import variant_api, variant_summary_stats_api, variants_api
from gpmappy.cache import TTLCache
from gpmappy.config import ApiEnvironment, GpmapConfig
from gpmappy.constants import DEV_BASE_URL, MAX_IDS_EXPAND, MAX_IDS_NON_EXPAND, PRODUCTION_BASE_URL
from gpmappy.exceptions import ValidationError
from gpmappy.merge import merge_associations
from gpmappy.transport import HttpTransport
from gpmappy.utils import cleanup_api_object, create_source_url, is_guid


class GpmapClient:
    def __init__(self, config: GpmapConfig | None = None) -> None:
        self._config = config or GpmapConfig()
        self._transport = HttpTransport(
            base_url=self._config.base_url,
            timeout_seconds=self._config.timeout_seconds,
            max_retries=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            user_agent=self._config.user_agent,
        )
        self._search_cache: TTLCache[pd.DataFrame] = TTLCache(ttl_seconds=600)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "GpmapClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def select_api(self, api: str = "production") -> None:
        if api == ApiEnvironment.PRODUCTION.value:
            self.set_base_url(PRODUCTION_BASE_URL)
            return
        if api == ApiEnvironment.DEV.value:
            self.set_base_url(DEV_BASE_URL)
            return
        raise ValidationError("Invalid API environment")

    def set_base_url(self, url: str) -> None:
        self._transport.close()
        self._config.base_url = url.rstrip("/")
        self._transport = HttpTransport(
            base_url=self._config.base_url,
            timeout_seconds=self._config.timeout_seconds,
            max_retries=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            user_agent=self._config.user_agent,
        )

    def health_api(self) -> dict[str, object]:
        return health_api(self._transport)

    def version_api(self) -> str:
        return version_api(self._transport)

    def all_traits(self) -> pd.DataFrame:
        payload = traits_api(self._transport)
        return pd.DataFrame(payload.get("traits", []))

    def all_genes(self) -> pd.DataFrame:
        payload = genes_api(self._transport)
        return pd.DataFrame(payload.get("genes", []))

    def associations(self, snp_ids: list[int], study_ids: list[int]) -> pd.DataFrame:
        payload = associations_api(self._transport, snp_ids=snp_ids, study_ids=study_ids)
        return pd.DataFrame(payload.get("associations", []))

    def get_all_gene_pleiotropies(self) -> pd.DataFrame:
        payload = gene_pleiotropies_api(self._transport)
        return pd.DataFrame(payload.get("genes", []))

    def get_all_snp_pleiotropies(self) -> pd.DataFrame:
        payload = snp_pleiotropies_api(self._transport)
        return pd.DataFrame(payload.get("snps", []))

    def trait(
        self,
        trait_id: str | int,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if trait_id is None:
            raise ValidationError("trait_id is required")

        if is_guid(trait_id):
            trait_info = get_gwas_api(self._transport, str(trait_id))
            coloc_trait_id = trait_info.get("trait", {}).get("id", trait_id)
        else:
            trait_info = trait_api(self._transport, trait_id, include_associations=include_associations)
            coloc_trait_id = trait_id

        if include_coloc_pairs and not is_guid(coloc_trait_id):
            trait_info["coloc_pairs"] = trait_coloc_pairs_api(self._transport, coloc_trait_id, h4_threshold)

        if include_associations and "associations" in trait_info:
            assoc_df = pd.DataFrame(trait_info.get("associations", []))
            coloc_df = pd.DataFrame(trait_info.get("coloc_groups", []))
            rare_df = pd.DataFrame(trait_info.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            trait_info["coloc_groups"] = _df_to_records(merged_coloc)
            trait_info["rare_results"] = _df_to_records(merged_rare)

        if isinstance(trait_info.get("trait"), dict) and trait_info["trait"].get("trait"):
            trait_info["trait"]["source_url"] = create_source_url(str(trait_info["trait"]["trait"]))

        return cleanup_api_object(trait_info)

    def traits(
        self,
        trait_ids: list[str | int],
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if not trait_ids:
            raise ValidationError("trait_ids is required")
        if len(trait_ids) > MAX_IDS_EXPAND:
            raise ValidationError("trait_ids must contain at most 10 IDs")
        clean_ids = list(dict.fromkeys(trait_ids))

        numeric_ids = [v for v in clean_ids if not is_guid(v)]
        guid_ids = [str(v) for v in clean_ids if is_guid(v)]

        result: dict[str, Any] = {
            "traits": [],
            "coloc_groups": [],
            "study_extractions": [],
            "rare_results": [],
        }

        if numeric_ids:
            payload = specific_traits_api(
                self._transport,
                numeric_ids,
                include_associations=include_associations,
                include_coloc_pairs=False,
                h4_threshold=h4_threshold,
            )
            result.update(payload)

            if include_coloc_pairs:
                coloc_pairs = [trait_coloc_pairs_api(self._transport, tid, h4_threshold) for tid in numeric_ids]
                result["coloc_pairs"] = coloc_pairs

        for guid in guid_ids:
            upload_result = get_gwas_api(self._transport, guid)
            result["traits"].append(upload_result.get("trait", {}))
            for key in ("coloc_groups", "study_extractions", "rare_results"):
                result[key].extend(upload_result.get(key, []))

        return cleanup_api_object(result)

    def gene(
        self,
        gene_id: str,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        include_trans: bool = True,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if not gene_id:
            raise ValidationError("gene_id is required")
        result = gene_api(
            self._transport,
            gene_id,
            include_associations=include_associations,
            include_coloc_pairs=include_coloc_pairs,
            include_trans=include_trans,
            h4_threshold=h4_threshold,
        )
        if include_associations and "associations" in result:
            assoc_df = pd.DataFrame(result.get("associations", []))
            coloc_df = pd.DataFrame(result.get("coloc_groups", []))
            rare_df = pd.DataFrame(result.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            result["coloc_groups"] = _df_to_records(merged_coloc)
            result["rare_results"] = _df_to_records(merged_rare)
        result.pop("tissues", None)
        return cleanup_api_object(result)

    def genes(
        self,
        gene_ids: list[str],
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        include_trans: bool = True,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if not gene_ids:
            raise ValidationError("gene_ids is required")
        if len(gene_ids) > MAX_IDS_EXPAND:
            raise ValidationError("gene_ids must contain at most 10 IDs")
        result = specific_genes_api(
            self._transport,
            list(dict.fromkeys(gene_ids)),
            include_associations=include_associations,
            include_coloc_pairs=include_coloc_pairs,
            include_trans=include_trans,
            h4_threshold=h4_threshold,
        )
        if include_associations and "associations" in result:
            assoc_df = pd.DataFrame(result.get("associations", []))
            coloc_df = pd.DataFrame(result.get("coloc_groups", []))
            rare_df = pd.DataFrame(result.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            result["coloc_groups"] = _df_to_records(merged_coloc)
            result["rare_results"] = _df_to_records(merged_rare)
        return cleanup_api_object(result)

    def region(
        self,
        region_id: str | int,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if region_id is None:
            raise ValidationError("region_id is required")
        result = region_api(
            self._transport,
            region_id,
            include_associations=include_associations,
            include_coloc_pairs=include_coloc_pairs,
            h4_threshold=h4_threshold,
        )
        if include_associations and "associations" in result:
            assoc_df = pd.DataFrame(result.get("associations", []))
            coloc_df = pd.DataFrame(result.get("coloc_groups", []))
            rare_df = pd.DataFrame(result.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            result["coloc_groups"] = _df_to_records(merged_coloc)
            result["rare_results"] = _df_to_records(merged_rare)
        result.pop("tissues", None)
        return cleanup_api_object(result)

    def variant(
        self,
        snp_id: str | int,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        include_summary_stats: bool = False,
    ) -> dict[str, Any]:
        if snp_id is None:
            raise ValidationError("snp_id is required")
        result = variant_api(
            self._transport,
            snp_id,
            include_coloc_pairs=include_coloc_pairs,
            h4_threshold=h4_threshold,
        )
        if include_summary_stats:
            result["summary_stats"] = variant_summary_stats_api(self._transport, snp_id)
        if "associations" in result:
            assoc_df = pd.DataFrame(result.get("associations", []))
            coloc_df = pd.DataFrame(result.get("coloc_groups", []))
            rare_df = pd.DataFrame(result.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            result["coloc_groups"] = _df_to_records(merged_coloc)
            result["rare_results"] = _df_to_records(merged_rare)
        return cleanup_api_object(result)

    def variants(
        self,
        variants: list[str | int],
        expand: bool = False,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
    ) -> dict[str, Any]:
        if not variants:
            raise ValidationError("variants is required")
        if expand and len(variants) > MAX_IDS_EXPAND:
            raise ValidationError("variants must contain at most 10 IDs when expand=True")
        if (not expand) and len(variants) > MAX_IDS_NON_EXPAND:
            raise ValidationError("variants must contain at most 50 IDs when expand=False")
        result = variants_api(
            self._transport,
            list(dict.fromkeys(variants)),
            expand=expand,
            include_associations=include_associations,
            include_coloc_pairs=include_coloc_pairs,
            h4_threshold=h4_threshold,
        )
        if expand and include_associations and "associations" in result:
            assoc_df = pd.DataFrame(result.get("associations", []))
            coloc_df = pd.DataFrame(result.get("coloc_groups", []))
            rare_df = pd.DataFrame(result.get("rare_results", []))
            merged_coloc, merged_rare = merge_associations(coloc_df, rare_df, assoc_df)
            result["coloc_groups"] = _df_to_records(merged_coloc)
            result["rare_results"] = _df_to_records(merged_rare)
        return cleanup_api_object(result)

    def ld_matrix(self, variant_ids: list[str | int]) -> dict[str, Any]:
        if not variant_ids:
            raise ValidationError("variant_ids is required")
        if all(isinstance(v, int) for v in variant_ids):
            return ld_matrix_by_snp_id_api(self._transport, [int(v) for v in variant_ids])
        return ld_matrix_by_variant_api(self._transport, variant_ids)

    def ld_proxies(self, variant_ids: list[str | int]) -> dict[str, Any]:
        if not variant_ids:
            raise ValidationError("variant_ids is required")
        if all(isinstance(v, int) for v in variant_ids):
            return ld_proxies_by_snp_id_api(self._transport, [int(v) for v in variant_ids])
        return ld_proxies_by_variant_api(self._transport, variant_ids)

    def get_gwas(self, gwas_id: str, include_summary_stats: bool = False) -> dict[str, Any]:
        if not gwas_id:
            raise ValidationError("gwas_id is required")
        result = get_gwas_api(self._transport, gwas_id)
        if include_summary_stats:
            result["summary_stats"] = get_gwas_summary_stats_api(self._transport, gwas_id)
        return cleanup_api_object(result)

    def upload_gwas(
        self,
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
        _validate_upload(
            file=file,
            name=name,
            p_value_threshold=p_value_threshold,
            email=email,
            category=category,
            ancestry=ancestry,
            sample_size=sample_size,
            reference_build=reference_build,
        )
        return upload_gwas_api(
            self._transport,
            file=file,
            name=name,
            p_value_threshold=p_value_threshold,
            column_names=column_names or {},
            email=str(email),
            category=category,
            is_published=is_published,
            doi=doi,
            should_be_added=should_be_added,
            ancestry=ancestry,
            sample_size=float(sample_size),
            reference_build=reference_build,
        )

    def search_gpmap(self, search_text: str, rsquared_threshold: float = 0.8) -> pd.DataFrame:
        if not search_text:
            raise ValidationError("search_text is required")
        if rsquared_threshold < 0 or rsquared_threshold > 1:
            raise ValidationError("rsquared_threshold must be in [0, 1]")

        search_text_norm = search_text.lower()
        if search_text_norm.startswith("rs") or ":" in search_text_norm:
            payload = search_variants_api(self._transport, search_text_norm, rsquared_threshold)
            results = []
            for item in payload.get("original_variants", []):
                results.append(
                    {
                        "type": "original_variant",
                        "name": item.get("display_snp"),
                        "type_id": item.get("id"),
                        "num_coloc_groups": item.get("num_colocs"),
                        "num_coloc_studies": _safe_list_len(item.get("coloc_groups")),
                        "num_rare_results": _safe_list_len(item.get("rare_results")),
                        "num_study_extractions": None,
                    }
                )
            for item in payload.get("proxy_variants", []):
                rsq = None
                ld_entries = item.get("ld_proxies") or []
                if ld_entries and isinstance(ld_entries, list):
                    rsq = round(float(ld_entries[0].get("r", 0)) ** 2, 2)
                results.append(
                    {
                        "type": "proxy_variant",
                        "name": item.get("display_snp"),
                        "type_id": item.get("id"),
                        "num_coloc_groups": item.get("num_colocs"),
                        "num_coloc_studies": _safe_list_len(item.get("coloc_groups")),
                        "num_rare_results": _safe_list_len(item.get("rare_results")),
                        "num_study_extractions": None,
                        "rsq": rsq,
                    }
                )
            df = pd.DataFrame(results)
        else:
            cache_key = "search_options"
            options_df = self._search_cache.get(cache_key)
            if options_df is None:
                payload = search_options_api(self._transport)
                options_df = pd.DataFrame(payload.get("search_terms", []))
                options_df["name_lower"] = options_df.get("name", "").astype(str).str.lower()
                options_df["alt_name_lower"] = options_df.get("alt_name", "").astype(str).str.lower()
                self._search_cache.set(cache_key, options_df)

            mask = options_df["name_lower"].str.contains(search_text_norm, regex=False) | options_df[
                "alt_name_lower"
            ].str.contains(search_text_norm, regex=False)
            df = options_df[mask].copy()
            df["name"] = df.apply(
                lambda r: r["name"]
                if not r.get("alt_name")
                else f"{r['name']} ({r['alt_name']})",
                axis=1,
            )

        if df.empty:
            return df

        def _call_value(row: pd.Series) -> str:
            row_type = row.get("type")
            if row_type in {"original_variant", "proxy_variant"}:
                return f"variant({row.get('type_id')})"
            if row_type == "trait":
                return f"trait({row.get('type_id')})"
            if row_type == "gene":
                return f"gene('{row.get('type_id')}')"
            return ""

        df["call"] = df.apply(_call_value, axis=1)
        drop_cols = [c for c in ["name_lower", "alt_name", "alt_name_lower", "rsq"] if c in df.columns]
        return df.drop(columns=drop_cols).drop_duplicates()


def _safe_list_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _df_to_records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def _validate_upload(
    *,
    file: str,
    name: str,
    p_value_threshold: float,
    email: str | None,
    category: str,
    ancestry: str,
    sample_size: int | float | None,
    reference_build: str,
) -> None:
    path = Path(file)
    if not path.exists() or path.stat().st_size > 1024**3:
        raise ValidationError("file must be a valid file and less than 1GB")
    if not name:
        raise ValidationError("name is required")
    if not email:
        raise ValidationError("email is required")
    if category not in {"continuous", "categorical"}:
        raise ValidationError("category must be continuous or categorical")
    if ancestry not in {"EUR"}:
        raise ValidationError("ancestry must be EUR")
    if reference_build not in {"GRCh37", "GRCh38"}:
        raise ValidationError("reference_build must be GRCh37 or GRCh38")
    if p_value_threshold <= 0 or p_value_threshold > 1e-5:
        raise ValidationError("p_value_threshold must be in (0, 1e-5]")
    if sample_size is None or float(sample_size) <= 0:
        raise ValidationError("sample_size must be a positive number")
