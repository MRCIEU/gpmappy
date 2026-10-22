# Changelog

## 0.2.0

Brings gpmappy in line with gpmapr 0.0.2.0.

- Add `trait_duplicates()` (`/v1/traits/duplicates`) and `delete_gwas()` (`DELETE /v1/gwas/{guid}`).
- Add `trait(include_full_associations=True)` (`/v1/traits/{id}/associations-full`).
- `trait()` coloc pairs are returned as a table; `traits()` de-duplicates them.
- `trait()` and `get_gwas()` accept `include_associations` for GWAS uploads, merging them
  into coloc groups by `study_id` or `existing_study_id`.
- `upload_gwas()` takes `*_col` arguments, checks them against the file header and accepts
  `compare_with_upload_guids`. `column_names` is deprecated.
- `search_gpmap()` orders results by coloc groups plus rare results and keeps the searched
  variant first. Trait names no longer get a `(None)` suffix, and proxy rows drop `rsq`.
- Requests that get `429 Too Many Requests` are retried with exponential backoff, honouring
  `Retry-After`, and raise `RateLimitError` after 5 retries.
- **Breaking:** follow the API's `snp_id` -> `variant_id` rename: `variant(variant_id)`,
  `associations(variant_ids, study_ids)`, `get_all_variant_pleiotropies()` (the old
  pleiotropy name is a deprecated alias), and association merging on `variant_id`.
- **Breaking:** `trait()` and `get_gwas()` positional arguments follow gpmapr's order.
- `traits()` and `genes()` return the API payload without dropping empty sections, as gpmapr does.
- Live tests only run with `pytest --run-live` or `GPMAPPY_RUN_LIVE=1`.
- The parity contract now replays scenarios against gpmapr-generated golden output.

## 0.1.0

- Initial implementation with parity-oriented API surface.
