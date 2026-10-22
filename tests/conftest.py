from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run tests marked 'live' against the production GPMap API",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-live") or os.environ.get("GPMAPPY_RUN_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="live API test: use --run-live or GPMAPPY_RUN_LIVE=1")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
