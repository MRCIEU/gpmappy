# gpmappy

Python client for the OpenGWAS genotype-phenotype map API.

## Local development install

Create and activate a virtual environment, then install in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Install as a regular local package:

```bash
pip install .
```

## Quick check

```bash
pytest
```
