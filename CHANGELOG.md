# Changelog

## 1.0.0

Brings gpmappy in line with gpmapr 1.0.0. **Requires version 1.1.0 of the GPMap API.**

### API 1.1.0 / gpmapr 1.0.0

- The API version is checked on the first request to an API (not on import). If this
  gpmappy doesn't support it, requests raise `ApiVersionError` with upgrade instructions.
  `/health` and `/v1/info/version` are not checked; `GpmapConfig(check_api_version=False)`
  turns the check off.
- New `gpmap_available()`: whether the API can be reached and is a supported version.
- New `compare_upload(upload, trait_id)`: lines up a GWAS upload with a trait (or a compared
  upload) in the coloc groups they share, and lists the coloc pairs between them.
- **Breaking:** `$associations` is no longer returned. With `include_associations=True`,
  each study's association at its variant (`beta`, `se`, `p`, `eaf`, `imputed`) is added to
  `coloc_groups`, `rare_results` **and** `study_extractions`; `get_gwas()` and `traits()` with
  GUIDs now add them too.
- Placeholder associations (beta 0, se 1, p 1, imputed) for variants a study did not report
  come back with `beta`, `se`, `p` and `eaf` missing, including from `associations()` and
  `trait(include_full_associations=True)`.
- **Breaking:** GWAS upload results have a `source` ("upload"/"existing") and
  `gwas_upload_id` on every row; associations join on them, and coloc pairs use
  `study_extraction_*_id` with `source_*`.
- Coloc pairs from `gene()`, `genes()`, `variant()`, `region()` and `get_gwas()` gain
  `trait_name_a/_b`, `data_type_*`, `tissue_*` and `gene_*`.
- **Breaking:** the API's `trait` is now `pipeline_id` (and `source_url` is built from it) and
  `category` is now `variable_type`. `upload_gwas()` takes `variable_type`; `category` still
  works with a `FutureWarning`.
- `traits()` adds `trait_name` (from the upload's `name`) for GUIDs and marks existing rows
  `source="existing"` when mixing trait ids and GUIDs.
- `ld_matrix()` / `ld_proxies()` gain `rsq`, and an empty `lds` list when no pairs are
  stored. Variant searches gain `rsq` for each proxy.
- `genes()` and `traits()` drop empty elements, and `genes()` drops `tissues`, as gpmapr does.
- API errors read `GPMap API request failed (HTTP 404): <detail>` (`ApiError.detail` holds
  the API's explanation); connection failures read `Could not reach the GPMap API at <url>: ...`.

### Since gpmappy 0.1 (gpmapr 0.0.2.0)

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
- Live tests only run with `pytest --run-live` or `GPMAPPY_RUN_LIVE=1`.
- The parity contract replays scenarios against gpmapr-generated golden output, using
  gpmapr's recorded API responses plus hand-built edge cases, and an opt-in live test
  compares both packages against a real API.

## 0.1.0

- Initial implementation with parity-oriented API surface.
