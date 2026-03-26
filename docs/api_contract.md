# gpmappy API Contract

## Public entry points

- `GpmapClient`: primary object-oriented interface.
- Module-level wrappers in `gpmappy` for quick scripts and parity with R usage patterns.

## Environment defaults

- Production base URL: `https://gpmap.opengwas.io/api`
- Dev base URL: `http://localhost:8000`
- Default timeout: 360 seconds

## Method conventions

- Validate arguments before issuing any request.
- Keep parameter names aligned with R function names when practical.
- Return DataFrames for table-like sections (`traits`, `genes`, `associations`, etc.).
- Use snake_case for all Python methods and parameters.

## Stability policy

- Backward-compatible changes only within `0.x` minor versions where possible.
- Any intentional divergence from R behavior must be documented in `docs/parity_matrix.md`.

## Testing policy

- Unit tests for validation and data transform logic.
- HTTP-level tests mocked with `respx`.
- Optional live integration tests marked with `@pytest.mark.live`.
