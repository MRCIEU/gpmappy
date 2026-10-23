"""The installed gpmappy version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def package_version() -> str:
    try:
        return version("gpmappy")
    except (
        PackageNotFoundError
    ):  # pragma: no cover - only when running from an uninstalled checkout
        return "0+unknown"
