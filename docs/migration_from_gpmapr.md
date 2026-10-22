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
- `select_api()` and `version_api()` are public in gpmappy. gpmappy does not check the
  API version on import.

## Upgrading from gpmappy 0.1

gpmappy 0.2 follows gpmapr 0.0.2.0, which renamed SNP identifiers to variant identifiers:

- `variant(snp_id=...)` -> `variant(variant_id=...)`
- `associations(snp_ids=..., study_ids=...)` -> `associations(variant_ids=..., study_ids=...)`
- `get_all_snp_pleiotropies()` -> `get_all_variant_pleiotropies()` (the old name still works
  but raises a `FutureWarning`)
- Associations are merged into coloc groups and rare results on `variant_id`.

Positional arguments now follow gpmapr's order:

- `trait(trait_id, include_associations, include_full_associations, include_coloc_pairs, ...)`
- `get_gwas(gwas_id, include_associations, include_summary_stats, ...)`

`upload_gwas()` requires the `*_col` arguments (or the deprecated `column_names`).
