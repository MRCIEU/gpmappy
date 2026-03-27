# API Reference

Core client:

- `GpmapClient.health_api()`
- `GpmapClient.version_api()`
- `GpmapClient.search_gpmap()`
- `GpmapClient.all_traits()`, `GpmapClient.trait()`, `GpmapClient.traits()`
- `GpmapClient.all_genes()`, `GpmapClient.gene()`, `GpmapClient.genes()`
- `GpmapClient.variant()`, `GpmapClient.variants()`
- `GpmapClient.region()`
- `GpmapClient.ld_matrix()`, `GpmapClient.ld_proxies()`
- `GpmapClient.associations()`
- `GpmapClient.get_all_gene_pleiotropies()`, `GpmapClient.get_all_snp_pleiotropies()`
- `GpmapClient.get_gwas()`, `GpmapClient.upload_gwas()`

Module wrappers mirror the same names.

## Tabular output behavior

- Methods with tabular output accept `as_dataframe: bool | None = None`.
- `None` (default): returns pandas DataFrames when pandas is installed, otherwise list-of-dict tables.
- `True`: force DataFrame output (raises a clear error if pandas is missing).
- `False`: always return list-of-dict tables.
