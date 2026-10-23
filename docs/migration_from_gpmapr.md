# Migration from gpmapr

`gpmappy` keeps function parity while using Python conventions.

## Mapping examples

- `gpmapr::all_traits()` -> `gpmappy.all_traits()`
- `gpmapr::trait(trait_id)` -> `gpmappy.trait(trait_id)`
- `gpmapr::variants(variants, expand=TRUE)` -> `gpmappy.variants(variants, expand=True)`
- `gpmapr::upload_gwas(...)` -> `gpmappy.upload_gwas(...)`

## Key differences

- Snake_case naming is preserved where already present.
- Module wrappers and `GpmapClient` class are both supported.
- Tabular outputs auto-convert to pandas DataFrames when pandas is installed.
- Set `as_dataframe=False` on supported methods for a pure list-of-dict output.
- `select_api()` and `version_api()` are public in gpmappy. Like gpmapr, gpmappy checks the
  API version on the first request rather than on import.
- `compare_upload()` takes the dict returned by `get_gwas(..., include_associations=True)`
  (DataFrame or list tables both work).

## Upgrading from gpmappy 0.1

gpmappy 1.0 follows gpmapr 1.0.0 and requires API 1.1.0. It renamed SNP identifiers to
variant identifiers:

- `variant(snp_id=...)` -> `variant(variant_id=...)`
- `associations(snp_ids=..., study_ids=...)` -> `associations(variant_ids=..., study_ids=...)`
- `get_all_snp_pleiotropies()` -> `get_all_variant_pleiotropies()` (the old name still works
  but raises a `FutureWarning`)
- Associations are merged into coloc groups and rare results on `variant_id`.

Positional arguments now follow gpmapr's order:

- `trait(trait_id, include_associations, include_full_associations, include_coloc_pairs, ...)`
- `get_gwas(gwas_id, include_associations, include_summary_stats, ...)`

`upload_gwas()` requires the `*_col` arguments (or the deprecated `column_names`) and takes
`variable_type` (the deprecated `category` still works).

Output changes with API 1.1.0:

- No `associations` element: with `include_associations=True` the effects are columns of
  `coloc_groups`, `rare_results` and `study_extractions`.
- Placeholder associations (beta 0, se 1, p 1) are returned as missing values.
- Traits have `pipeline_id` instead of `trait`, and `variable_type` instead of `category`.
- GWAS upload rows have `source` and `gwas_upload_id`: identify a study extraction by
  `source` together with its id. The upload's own rows are those with
  `source == "upload"` and `gwas_upload_id == result["trait"]["id"]`.
- Coloc pairs carry `trait_name_a`, `trait_name_b`, etc.
- The API returns coloc groups and rare results in no particular order, so don't rely on
  their row order.
