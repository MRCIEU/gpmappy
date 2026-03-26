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
- Tabular outputs are returned as pandas DataFrames.
