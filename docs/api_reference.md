# API Reference

Core client:

- `GpmapClient.health_api()`, `GpmapClient.gpmap_available()`
- `GpmapClient.version_api()`
- `GpmapClient.search_gpmap()`
- `GpmapClient.all_traits()`, `GpmapClient.trait()`, `GpmapClient.traits()`,
  `GpmapClient.trait_duplicates()`
- `GpmapClient.all_genes()`, `GpmapClient.gene()`, `GpmapClient.genes()`
- `GpmapClient.variant()`, `GpmapClient.variants()`
- `GpmapClient.region()`
- `GpmapClient.ld_matrix()`, `GpmapClient.ld_proxies()`
- `GpmapClient.associations()`
- `GpmapClient.get_all_gene_pleiotropies()`, `GpmapClient.get_all_variant_pleiotropies()`
- `GpmapClient.get_gwas()`, `GpmapClient.upload_gwas()`, `GpmapClient.delete_gwas()`,
  `GpmapClient.compare_upload()`

Module wrappers mirror the same names.

## Tabular output behavior

- Methods with tabular output accept `as_dataframe: bool | None = None`.
- `None` (default): returns pandas DataFrames when pandas is installed, otherwise list-of-dict tables.
- `True`: force DataFrame output (raises a clear error if pandas is missing).
- `False`: always return list-of-dict tables.

## Uploading a GWAS

Name the columns of your file with the `*_col` arguments. `chr_col`, `bp_col`, `ea_col`,
`oa_col` and `p_col` are required, plus either `beta_col` and `se_col` or `or_col`,
`or_lb_col` and `or_ub_col`. The columns are checked against the file header before
uploading.

```python
from gpmappy import upload_gwas

upload = upload_gwas(
    "my_gwas.tsv.gz",
    name="My GWAS",
    email="me@example.com",
    sample_size=10_000,
    chr_col="chr", bp_col="pos", ea_col="ea", oa_col="oa", p_col="p",
    beta_col="beta", se_col="se",
    compare_with_upload_guids=["<guid of an earlier upload>"],
)
result = get_gwas(upload["guid"], include_associations=True)  # once processing has finished
comparison = compare_upload(result, 2527)  # effects of the upload and trait 2527 side by side
```

Upload results combine the upload's rows with the existing studies they colocalise with.
Every row of `study_extractions` and `coloc_groups` has a `source` ("upload" or
"existing") and a `gwas_upload_id`; upload and existing study extractions have separate
ids, so identify one by `source` and its id together.

The `column_names` mapping (e.g. `{"CHR": "chr"}`) still works but raises a
`FutureWarning`. Delete an upload with `delete_gwas(guid, email)` using the same email.

## API versions and errors

gpmappy 1.0 supports version 1.1.0 of the GPMap API. The first request to an API checks
its version; if it isn't supported, requests raise `gpmappy.exceptions.ApiVersionError`
(set `GpmapConfig(check_api_version=False)` to skip the check). `gpmap_available()` says
whether the API can be reached and is supported, without raising.

HTTP errors raise `ApiError` with a message like
`GPMap API request failed (HTTP 404): Trait 999999999 not found` (the API's explanation is
in `.detail`, the status in `.status_code`).

## Rate limiting

When the API answers `429 Too Many Requests`, requests are retried up to 5 times,
honouring a `Retry-After` header or otherwise backing off exponentially with jitter
(1 s base, 32 s cap). If the API is still rate limiting after that, a
`gpmappy.exceptions.RateLimitError` is raised. Tune this with `GpmapConfig`
(`rate_limit_max_retries`, `rate_limit_base_delay`, `rate_limit_max_delay`).
