# gpmappy Architecture

## Design goals

- Preserve functional parity with `gpmapr` exported functions.
- Provide a clean Python API centered around a reusable client object.
- Keep network behavior reliable with timeouts, retries, and typed errors.
- Return pandas DataFrames for tabular payloads while keeping nested payloads as dicts.

## Layers

1. Public layer: `gpmappy.wrappers` and `GpmapClient` methods.
2. Service layer: resource methods in `GpmapClient` that apply validation and transforms.
3. API layer: `gpmappy.api.*` functions that map directly to HTTP endpoints.
4. Transport layer: `HttpTransport` wrapper around `httpx.Client`.
5. Utilities: merge and cleanup helpers, GUID logic, and search cache.

## Error model

- `ValidationError`: local argument validation issues.
- `ApiError`: non-2xx API response with payload details when available.
- `NetworkError`: request transport failures.
- `TimeoutError`: timeout-specific transport failures.

## Data return policy

- Endpoint responses remain dict-like unless explicitly tabular.
- Known tabular entities are converted to `pandas.DataFrame` where possible.
- Empty/missing optional objects are dropped via cleanup helpers.

## Compatibility notes

- `trait()` and `traits()` preserve GUID branch behavior.
- Association merge behavior mirrors R implementation.
- `variants()` keeps expand/non-expand limits.
- `upload_gwas()` keeps strict validations from `gpmapr`.
