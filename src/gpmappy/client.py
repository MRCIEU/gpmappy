"""Client implementation."""

from __future__ import annotations

import re
import warnings
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
from gpmappy.api.variants import variant_api, variant_summary_stats_api, variants_api
from gpmappy.cache import TTLCache
from gpmappy.compare import compare_upload
from gpmappy.config import ApiEnvironment, GpmapConfig
from gpmappy.constants import DEV_BASE_URL, MAX_IDS_EXPAND, MAX_IDS_NON_EXPAND, PRODUCTION_BASE_URL
from gpmappy.exceptions import GpmappyError, ValidationError
from gpmappy.merge import (
    fold_associations,
    fold_upload_associations,
    mask_padded_associations,
)
from gpmappy.tabular import TableLike, records_to_table
from gpmappy.transport import HttpTransport
from gpmappy.upload import (
    build_gwas_column_names,
    check_gwas_file_columns,
    validate_upload_arguments,
)
from gpmappy.utils import cleanup_api_object, create_source_url, is_guid

VARIANT_SEARCH_PATTERN = re.compile(r"^(rs|\d+:\d+)")


class GpmapClient:
    def __init__(self, config: GpmapConfig | None = None) -> None:
        self._config = config or GpmapConfig()
        self._transport = HttpTransport(
            base_url=self._config.base_url,
            timeout_seconds=self._config.timeout_seconds,
            max_retries=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            user_agent=self._config.user_agent,
            rate_limit_max_retries=self._config.rate_limit_max_retries,
            rate_limit_base_delay=self._config.rate_limit_base_delay,
            rate_limit_max_delay=self._config.rate_limit_max_delay,
            check_api_version=self._config.check_api_version,
        )
        self._search_cache: TTLCache[list[dict[str, Any]]] = TTLCache(ttl_seconds=600)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> GpmapClient:
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
            rate_limit_max_retries=self._config.rate_limit_max_retries,
            rate_limit_base_delay=self._config.rate_limit_base_delay,
            rate_limit_max_delay=self._config.rate_limit_max_delay,
            check_api_version=self._config.check_api_version,
        )

    def health_api(self) -> dict[str, object]:
        return health_api(self._transport)

    def version_api(self) -> str:
        return version_api(self._transport)

    def gpmap_available(self) -> bool:
        """Whether the API can be reached and is a version this gpmappy supports. Never raises."""
        try:
            health_api(self._transport)
            return self._transport.ensure_api_compatible()
        except GpmappyError:
            return False

    def compare_upload(
        self, upload: dict[str, Any], trait_id: Any, as_dataframe: bool | None = None
    ) -> dict[str, TableLike]:
        """See :func:`gpmappy.compare.compare_upload`."""
        return compare_upload(upload, trait_id, as_dataframe=as_dataframe)

    def all_traits(self, as_dataframe: bool | None = None) -> TableLike:
        payload = traits_api(self._transport)
        return records_to_table(
            _ensure_record_list(payload.get("traits")), as_dataframe=as_dataframe
        )

    def all_genes(self, as_dataframe: bool | None = None) -> TableLike:
        payload = genes_api(self._transport)
        return records_to_table(
            _ensure_record_list(payload.get("genes")), as_dataframe=as_dataframe
        )

    def trait_duplicates(self, as_dataframe: bool | None = None) -> TableLike:
        payload = trait_duplicates_api(self._transport)
        return records_to_table(
            _ensure_record_list(payload.get("duplicates")), as_dataframe=as_dataframe
        )

    def associations(
        self, variant_ids: list[int], study_ids: list[int], as_dataframe: bool | None = None
    ) -> TableLike:
        payload = associations_api(self._transport, variant_ids=variant_ids, study_ids=study_ids)
        return records_to_table(
            mask_padded_associations(_ensure_record_list(payload.get("associations"))),
            as_dataframe=as_dataframe,
        )

    def get_all_gene_pleiotropies(self, as_dataframe: bool | None = None) -> TableLike:
        payload = gene_pleiotropies_api(self._transport)
        return records_to_table(
            _ensure_record_list(payload.get("genes")), as_dataframe=as_dataframe
        )

    def get_all_variant_pleiotropies(self, as_dataframe: bool | None = None) -> TableLike:
        payload = variant_pleiotropies_api(self._transport)
        return records_to_table(_ensure_record_list(payload.get("snps")), as_dataframe=as_dataframe)

    def get_all_snp_pleiotropies(self, as_dataframe: bool | None = None) -> TableLike:
        """Deprecated alias of :meth:`get_all_variant_pleiotropies`."""
        warnings.warn(
            "get_all_snp_pleiotropies() is deprecated, use get_all_variant_pleiotropies()",
            FutureWarning,
            stacklevel=2,
        )
        return self.get_all_variant_pleiotropies(as_dataframe=as_dataframe)

    def trait(  # noqa: PLR0913
        self,
        trait_id: str | int,
        include_associations: bool = False,
        include_full_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        if trait_id is None:
            raise ValidationError("trait_id is required")

        if is_guid(trait_id):
            trait_info = fold_upload_associations(
                get_gwas_api(
                    self._transport, str(trait_id), include_associations=include_associations
                )
            )
        else:
            trait_info = trait_api(
                self._transport, trait_id, include_associations=include_associations
            )
            if include_full_associations:
                trait_info["full_associations"] = mask_padded_associations(
                    trait_associations_full_api(self._transport, trait_id)
                )
            trait_info = fold_associations(trait_info)

        trait_info = cleanup_api_object(trait_info)
        if isinstance(trait_info.get("trait"), dict) and trait_info["trait"].get("pipeline_id"):
            trait_info["trait"]["source_url"] = create_source_url(
                str(trait_info["trait"]["pipeline_id"])
            )

        # Added after the clean up: the coloc pairs endpoint doesn't return the study
        # extractions its pairs refer to, so their details can't be joined on.
        if not is_guid(trait_id) and include_coloc_pairs:
            coloc_pairs = trait_coloc_pairs_api(self._transport, trait_id, h4_threshold)
            if coloc_pairs:
                trait_info["coloc_pairs"] = coloc_pairs
        return _coerce_tabular(trait_info, as_dataframe)

    def traits(
        self,
        trait_ids: list[str | int],
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        _validate_id_list("trait_ids", trait_ids, MAX_IDS_EXPAND)
        clean_ids = list(dict.fromkeys(trait_ids))
        numeric_ids = [v for v in clean_ids if not is_guid(v)]
        guid_ids = [str(v) for v in clean_ids if is_guid(v)]

        result: dict[str, Any]
        if numeric_ids:
            result = fold_associations(
                specific_traits_api(
                    self._transport, numeric_ids, include_associations=include_associations
                )
            )
        else:
            result = {
                "traits": None,
                "coloc_groups": None,
                "study_extractions": None,
                "rare_results": None,
            }

        for guid in guid_ids:
            upload = get_gwas_api(self._transport, guid, include_associations=include_associations)
            _merge_trait_result(result, fold_upload_associations(upload))

        result = cleanup_api_object(result)
        # Added after the clean up, as in trait().
        if include_coloc_pairs and numeric_ids:
            coloc_pairs = _dedupe_records(
                [
                    pair
                    for tid in numeric_ids
                    for pair in trait_coloc_pairs_api(self._transport, tid, h4_threshold)
                ]
            )
            if coloc_pairs:
                result["coloc_pairs"] = coloc_pairs
        return _coerce_tabular(result, as_dataframe)

    def gene(  # noqa: PLR0913
        self,
        gene_id: str,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        include_trans: bool = True,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
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
        result.pop("tissues", None)
        return _coerce_tabular(cleanup_api_object(fold_associations(result)), as_dataframe)

    def genes(  # noqa: PLR0913
        self,
        gene_ids: list[str],
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        include_trans: bool = True,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        _validate_id_list("gene_ids", gene_ids, MAX_IDS_EXPAND)
        result = specific_genes_api(
            self._transport,
            list(dict.fromkeys(gene_ids)),
            include_associations=include_associations,
            include_coloc_pairs=include_coloc_pairs,
            include_trans=include_trans,
            h4_threshold=h4_threshold,
        )
        result.pop("tissues", None)
        return _coerce_tabular(cleanup_api_object(fold_associations(result)), as_dataframe)

    def region(
        self,
        region_id: str | int,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
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
        result.pop("tissues", None)
        return _coerce_tabular(cleanup_api_object(fold_associations(result)), as_dataframe)

    def variant(
        self,
        variant_id: str | int,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        include_summary_stats: bool = False,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        if variant_id is None:
            raise ValidationError("variant_id is required")
        result = variant_api(
            self._transport,
            variant_id,
            include_coloc_pairs=include_coloc_pairs,
            h4_threshold=h4_threshold,
        )
        if include_summary_stats:
            result["summary_stats"] = variant_summary_stats_api(self._transport, variant_id)
        return _coerce_tabular(cleanup_api_object(fold_associations(result)), as_dataframe)

    def variants(  # noqa: PLR0913
        self,
        variants: list[str | int],
        expand: bool = False,
        include_associations: bool = False,
        include_coloc_pairs: bool = False,
        h4_threshold: float = 0.8,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        _validate_id_list("variants", variants)
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
        return _coerce_tabular(cleanup_api_object(fold_associations(result)), as_dataframe)

    def ld_matrix(self, variant_ids: list[str | int] | None = None) -> dict[str, Any]:
        if not variant_ids:
            raise ValidationError("variant_ids is required")
        if all(isinstance(v, int) for v in variant_ids):
            result = ld_matrix_by_variant_id_api(self._transport, [int(v) for v in variant_ids])
        else:
            result = ld_matrix_by_variant_api(self._transport, variant_ids)
        return _with_rsq(result)

    def ld_proxies(self, variant_ids: list[str | int] | None = None) -> dict[str, Any]:
        if not variant_ids:
            raise ValidationError("variant_ids is required")
        if all(isinstance(v, int) for v in variant_ids):
            result = ld_proxies_by_variant_id_api(self._transport, [int(v) for v in variant_ids])
        else:
            result = ld_proxies_by_variant_api(self._transport, variant_ids)
        return _with_rsq(result)

    def get_gwas(
        self,
        gwas_id: str,
        include_associations: bool = False,
        include_summary_stats: bool = False,
        as_dataframe: bool | None = None,
    ) -> dict[str, Any]:
        if not gwas_id:
            raise ValidationError("gwas_id is required")
        result = get_gwas_api(self._transport, gwas_id, include_associations=include_associations)
        if include_summary_stats:
            result["summary_stats"] = get_gwas_summary_stats_api(self._transport, gwas_id)
        return _coerce_tabular(cleanup_api_object(fold_upload_associations(result)), as_dataframe)

    def upload_gwas(  # noqa: PLR0913
        self,
        file: str,
        name: str,
        p_value_threshold: float = 5e-8,
        column_names: dict[str, str] | None = None,
        email: str | None = None,
        variable_type: str = "continuous",
        is_published: bool = False,
        doi: str | None = None,
        should_be_added: bool = False,
        ancestry: str = "EUR",
        sample_size: int | float | None = None,
        reference_build: str = "GRCh38",
        compare_with_upload_guids: str | list[str] | None = None,
        chr_col: str | None = None,
        bp_col: str | None = None,
        ea_col: str | None = None,
        oa_col: str | None = None,
        p_col: str | None = None,
        eaf_col: str | None = None,
        beta_col: str | None = None,
        se_col: str | None = None,
        or_col: str | None = None,
        or_lb_col: str | None = None,
        or_ub_col: str | None = None,
        snp_col: str | None = None,
        rsid_col: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Upload a GWAS. Name its columns with the ``*_col`` arguments, e.g. ``chr_col="chr"``.

        ``chr_col``, ``bp_col``, ``ea_col``, ``oa_col`` and ``p_col`` are required, along
        with either ``beta_col`` and ``se_col`` or ``or_col``, ``or_lb_col`` and
        ``or_ub_col``. ``column_names`` and ``category`` (use ``variable_type``) are deprecated.
        """
        if category is not None:
            warnings.warn(
                "`category` is deprecated, use `variable_type` instead", FutureWarning, stacklevel=2
            )
            variable_type = category
        compare_guids = (
            [compare_with_upload_guids]
            if isinstance(compare_with_upload_guids, str)
            else compare_with_upload_guids
        )
        validate_upload_arguments(
            file=file,
            name=name,
            p_value_threshold=p_value_threshold,
            email=email,
            variable_type=variable_type,
            ancestry=ancestry,
            sample_size=sample_size,
            reference_build=reference_build,
            compare_with_upload_guids=compare_guids,
        )
        api_column_names = build_gwas_column_names(
            column_names,
            {
                "chr_col": chr_col,
                "bp_col": bp_col,
                "ea_col": ea_col,
                "oa_col": oa_col,
                "p_col": p_col,
                "eaf_col": eaf_col,
                "beta_col": beta_col,
                "se_col": se_col,
                "or_col": or_col,
                "or_lb_col": or_lb_col,
                "or_ub_col": or_ub_col,
                "snp_col": snp_col,
                "rsid_col": rsid_col,
            },
        )
        check_gwas_file_columns(file, api_column_names)
        return upload_gwas_api(
            self._transport,
            file=file,
            name=name,
            p_value_threshold=p_value_threshold,
            column_names=api_column_names,
            email=str(email),
            variable_type=variable_type,
            is_published=is_published,
            doi=doi,
            should_be_added=should_be_added,
            ancestry=ancestry,
            sample_size=float(sample_size),  # type: ignore[arg-type]
            reference_build=reference_build,
            compare_with_upload_guids=list(compare_guids) if compare_guids else None,
        )

    def delete_gwas(self, gwas_id: str, email: str) -> dict[str, Any]:
        """Permanently delete a GWAS upload and all of its results and files.

        The email must match the one used for the upload, and uploads that are
        still processing cannot be deleted.
        """
        if not isinstance(gwas_id, str) or not is_guid(gwas_id):
            raise ValidationError("gwas_id must be the GUID of a GWAS upload")
        if not isinstance(email, str) or not email.strip():
            raise ValidationError("email is required")
        return delete_gwas_api(self._transport, gwas_id, email)

    def search_gpmap(
        self,
        search_text: str,
        rsquared_threshold: float = 0.8,
        as_dataframe: bool | None = None,
    ) -> TableLike:
        """Search traits, genes and variants.

        Results are ordered by colocalisation groups plus rare results (most first);
        for variant searches the searched variant always comes first.
        """
        if not search_text:
            raise ValidationError("search_text is required")
        if rsquared_threshold < 0 or rsquared_threshold > 1:
            raise ValidationError("rsquared_threshold must be in [0, 1]")

        query = search_text.lower()
        if VARIANT_SEARCH_PATTERN.match(query):
            payload = search_variants_api(self._transport, query, rsquared_threshold)
            rows = _build_variant_search_rows(payload)
        else:
            rows = self._search_terms(query)
        return records_to_table(_order_search_results(rows), as_dataframe=as_dataframe)

    def _search_terms(self, query: str) -> list[dict[str, Any]]:
        search_options = self._search_cache.get("search_options")
        if search_options is None:
            payload = search_options_api(self._transport)
            search_options = _ensure_record_list(payload.get("search_terms"))
            self._search_cache.set("search_options", search_options)

        matched_rows = []
        for row in search_options:
            name = str(row.get("name") or "")
            alt_name = str(row.get("alt_name") or "")
            if query not in name.lower() and query not in alt_name.lower():
                continue

            matched_row = dict(row)
            if alt_name:
                matched_row["name"] = f"{name} ({alt_name})"
            matched_row["call"] = _search_call(matched_row.get("type"), matched_row.get("type_id"))
            for column in ("name_lower", "alt_name_lower", "alt_name"):
                matched_row.pop(column, None)
            matched_rows.append(matched_row)
        return _dedupe_records(matched_rows)


def _build_variant_search_rows(payload: dict[str, object]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_type, key in (
        ("original_variant", "original_variants"),
        ("proxy_variant", "proxy_variants"),
    ):
        for item in _ensure_record_list(payload.get(key)):
            # r-squared with the searched variant: the strongest of a proxy's LD pairs
            ld_proxies = _ensure_record_list(item.get("ld_proxies"))
            rsq = (
                _rsq([pair.get("r") for pair in ld_proxies])
                if row_type == "proxy_variant"
                else None
            )
            rows.append(
                {
                    "type": row_type,
                    "name": item.get("display_snp"),
                    "type_id": item.get("id"),
                    "rsq": rsq,
                    "num_coloc_groups": item.get("num_colocs"),
                    "num_coloc_studies": _safe_list_len(item.get("coloc_groups")),
                    "num_rare_results": _safe_list_len(item.get("rare_results")),
                    "num_study_extractions": None,
                    "call": f"variant({item.get('id')})",
                }
            )
    return _dedupe_records(rows)


def _search_call(row_type: object, type_id: object) -> str | None:
    if row_type in {"original_variant", "proxy_variant"}:
        return f"variant({type_id})"
    if row_type == "trait":
        return f"trait({type_id})"
    if row_type == "gene":
        return f"gene('{type_id}')"
    return None


def _order_search_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Most important results first, keeping an exact variant match above its proxies."""

    def importance(row: dict[str, Any]) -> float:
        return float(row.get("num_coloc_groups") or 0) + float(row.get("num_rare_results") or 0)

    return sorted(rows, key=lambda row: (row.get("type") != "original_variant", -importance(row)))


def _validate_id_list(name: str, ids: list[Any], max_ids: int | None = None) -> None:
    if not ids:
        raise ValidationError(f"{name} is required")
    if any(v is None for v in ids):
        raise ValidationError(f"{name} must not contain missing values")
    if max_ids is not None and len(ids) > max_ids:
        raise ValidationError(f"{name} must contain at most {max_ids} IDs")


def _merge_trait_result(result: dict[str, Any], upload: dict[str, Any]) -> None:
    """Add a GWAS upload result to a traits() result."""
    if isinstance(upload.get("trait"), dict):
        # One row per upload, from its single-value fields, named like the other traits.
        row = {
            key: value
            for key, value in upload["trait"].items()
            if not isinstance(value, (dict, list))
        }
        if "name" in row:
            row["trait_name"] = row["name"]
        result["traits"] = [*_ensure_record_list(result.get("traits")), row]
    for key in ("coloc_groups", "study_extractions", "rare_results"):
        rows = _ensure_record_list(upload.get(key))
        if not rows:
            continue
        existing = _ensure_record_list(result.get(key))
        if existing and not any("source" in row for row in existing):
            existing = [{**row, "source": "existing"} for row in existing]
        result[key] = [*existing, *rows]


def _with_rsq(result: dict[str, Any]) -> dict[str, Any]:
    """LD pairs with their r-squared, rounded as in search_gpmap(); no pairs give an empty list."""
    result["lds"] = [
        {**pair, "rsq": _rsq([pair.get("r")])} for pair in _ensure_record_list(result.get("lds"))
    ]
    return result


def _rsq(r_values: list[Any]) -> float | None:
    squares = [float(r) ** 2 for r in r_values if isinstance(r, (int, float))]
    return round(max(squares), 2) if squares else None


def _safe_list_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _ensure_record_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _coerce_tabular(data: dict[str, Any], as_dataframe: bool | None) -> dict[str, Any]:
    coerced: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list) and _is_record_list(value):
            coerced[key] = records_to_table(value, as_dataframe=as_dataframe)
        elif isinstance(value, dict):
            coerced[key] = _coerce_nested_dict(value, as_dataframe)
        else:
            coerced[key] = value
    return coerced


def _coerce_nested_dict(value: dict[str, Any], as_dataframe: bool | None) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, list) and _is_record_list(item):
            nested[key] = records_to_table(item, as_dataframe=as_dataframe)
        else:
            nested[key] = item
    return nested


def _is_record_list(value: list[Any]) -> bool:
    if not value:
        return True
    return all(isinstance(item, dict) for item in value)


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for row in records:
        key = tuple(sorted((k, repr(v)) for k, v in row.items()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
