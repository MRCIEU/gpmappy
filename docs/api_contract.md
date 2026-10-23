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
- Live integration tests marked with `@pytest.mark.live`, skipped unless you pass
  `pytest --run-live` (or set `GPMAPPY_RUN_LIVE=1`).

## Parity contract with gpmapr

`tests/contract/` checks gpmappy against the gpmapr R package:

- `gpmapr/fixtures/`: gpmapr's own recorded API responses (copied from its
  `tests/testthat/fixtures`), served by the URLs in their `index.json`.
- `fixtures/`: gpmappy's hand-built edge cases (matching, duplicate and placeholder
  associations, search ties, coloc pairs endpoints, uploads and deletes) and the routes
  that serve them.
- `scenarios.json`: calls to make, e.g. `trait(trait_id = 5020, include_associations = TRUE)`,
  and the fixture set each uses (`"fixtures": "edge"`, default gpmapr's). An argument
  `{"$call": {...}}` is the result of another call, e.g. `compare_upload(upload = get_gwas(...))`.
- `gpmapr/surface.json`: every gpmapr export with its parameters and defaults, and the API
  versions it supports (gpmappy must support the same ones).
- `gpmapr/golden/<id>.json`: for each scenario, the requests gpmapr made and its
  normalized result, error and warnings.

`test_parity_contract.py` checks that gpmappy exports every gpmapr function with the same
parameters (plus `as_dataframe`), and that each scenario sends the same requests and
returns the same output. Python-only exports are listed with a reason in
`PYTHON_ONLY_EXPORTS`. Known gpmapr bugs gpmappy does not copy are listed per scenario under
`divergences`, and a divergence that stops occurring fails the test.

The golden files come from gpmapr itself:

```bash
Rscript scripts/parity/generate_gpmapr_contract.R [path/to/gpmapr]
```

The script sources gpmapr's R files (no install or network needed), copies gpmapr's
recorded fixtures, and serves every request from the fixtures. When gpmapr is checked out next to this repository (or at
`$GPMAPR_PATH`) and `Rscript` is available, `test_gpmapr_snapshot_is_current` regenerates
the snapshot and fails if gpmapr has changed. Regenerate it, review the diff, and port
the change to gpmappy. Add a scenario (and fixture routes) for any new behaviour.

### Live parity

`tests/integration/test_live_parity.py` runs the calls in
`tests/integration/live_parity_scenarios.json` through both packages against a real API
and compares the results (ignoring row order, which the API doesn't fix):

```bash
GPMAPPY_PARITY_URL=http://localhost:8000 pytest --run-live tests/integration/test_live_parity.py
```
