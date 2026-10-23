from __future__ import annotations

import os

import pytest

from gpmappy.client import GpmapClient
from gpmappy.config import GpmapConfig
from gpmappy.constants import PRODUCTION_BASE_URL
from gpmappy.exceptions import ApiVersionError, GpmappyError


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


@pytest.fixture(scope="session")
def live_api_url() -> str:
    """The API the live tests call: $GPMAP_URL, or production.

    The live tests are skipped unless it can be reached and its version is checked as one this
    gpmappy supports (e.g. production before an API release this gpmappy needs is deployed).
    ensure_api_compatible() returns False, rather than raising, when it can't fetch the API's
    version, so that users' requests aren't blocked by it; the live tests need it to pass.
    """
    url = os.environ.get("GPMAP_URL", PRODUCTION_BASE_URL)
    with GpmapClient(GpmapConfig(base_url=url)) as client:
        try:
            client.health_api()
        except GpmappyError as error:
            pytest.skip(f"GPMap API at {url} is not reachable: {error}")
        try:
            supported = client._transport.ensure_api_compatible()
        except ApiVersionError as error:
            pytest.skip(str(error))
    if not supported:
        pytest.skip(
            f"Couldn't fetch the version of the GPMap API at {url} to check gpmappy supports it"
        )
    return url
