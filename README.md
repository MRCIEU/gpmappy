# gpmappy

Python client for the OpenGWAS genotype-phenotype map API.

Requires Python 3.9 or newer.

The base install is lightweight and does not require pandas.
Install dataframe support with the optional extra when needed.

## Local development install

Create and activate a virtual environment, then install in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Install with dataframe support only:

```bash
pip install -e ".[dataframe]"
```

Install as a regular local package:

```bash
pip install .
```

Install full tabular support from a release:

```bash
pip install "gpmappy[dataframe]"
```

## Quick check

```bash
pytest              # unit + gpmapr parity contract tests (no network)
pytest --run-live   # also hit the GPMap API ($GPMAP_URL, default production)
GPMAPPY_PARITY_URL=http://localhost:8000 pytest --run-live tests/integration/test_live_parity.py
```

gpmappy 1.0 needs version 1.1.0 of the GPMap API.

The parity contract tests compare gpmappy against golden output recorded from the gpmapr
R package. When gpmapr changes, regenerate them with
`Rscript scripts/parity/generate_gpmapr_contract.R path/to/gpmapr` (see
`docs/api_contract.md`).

## Troubleshooting

If you see NumPy ABI errors (for example `_ARRAY_API not found`) in older environments,
reinstall compatible numeric dependencies:

```bash
pip install --force-reinstall "numpy<2"
pip install --force-reinstall pandas
```

If you use Conda, prefer either all-conda or all-pip installs for numeric packages in a
given environment to avoid ABI conflicts.

## Maintainer: PyPI publication

This repository includes a GitHub Actions publish workflow at
`.github/workflows/release.yml` using Trusted Publisher (OIDC) for TestPyPI and PyPI.

Before first release, configure Trusted Publisher settings and follow
`docs/pypi_release.md`.

## Maintainer: docs publication

Documentation is built with MkDocs and deployed to GitHub Pages via
`.github/workflows/docs.yml`.

In repository settings, ensure Pages is configured to use **GitHub Actions** as
the source.
