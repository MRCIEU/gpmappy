# Installation

## Local editable install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Standard local install

```bash
pip install .
```

## Install with DataFrame support

```bash
pip install "gpmappy[dataframe]"
```

Without the `dataframe` extra, methods return list-of-dict tables by default.
