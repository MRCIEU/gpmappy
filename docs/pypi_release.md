# PyPI Release Guide

This project is configured for Trusted Publisher uploads from GitHub Actions.

## One-time setup

1. Create a PyPI project named `gpmappy` (and optionally TestPyPI project).
2. In PyPI project settings, add a Trusted Publisher:
   - Owner: `MRCIEU`
   - Repository: `gpmappy`
   - Workflow: `.github/workflows/release.yml`
   - Environment: `pypi`
3. (Optional) Repeat on TestPyPI with environment `testpypi`.
4. In GitHub repository settings, create environments:
   - `pypi`
   - `testpypi`

## Pre-release checklist

1. Update `pyproject.toml` metadata:
   - `project.version`
   - `project.urls.*` (confirm links still point to `MRCIEU/gpmappy`)
2. Update `CHANGELOG.md`.
3. Run local checks:

```bash
pip install -e ".[dev]"
ruff check .
black --check .
mypy src
pytest
python -m build
twine check dist/*
```

## Publish flow

- TestPyPI (manual):
  - Run workflow `Publish`
  - Choose input `repository=testpypi`
- PyPI (automatic): merge a version bump into `main`
  - When `pyproject.toml` has a version with no `v<version>` tag yet, the workflow tags the
    merge commit, creates the GitHub release (notes from that version's `CHANGELOG.md`
    section), then builds and publishes to PyPI
  - Pushes to `main` that don't change the version publish nothing
  - So only merge a version bump when you mean to release it
- PyPI (manual): run manual dispatch with `repository=pypi` (no tag or GitHub release)

## Install test

```bash
pip install gpmappy
pip install "gpmappy[dataframe]"
```
