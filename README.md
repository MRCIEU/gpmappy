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

## Quick check

```bash
pytest
```

## Troubleshooting

If you see NumPy ABI errors (for example `_ARRAY_API not found`) in older environments,
reinstall compatible numeric dependencies:

```bash
pip install --force-reinstall "numpy<2"
pip install --force-reinstall pandas
```
