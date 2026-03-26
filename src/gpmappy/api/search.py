"""Search endpoints."""

from __future__ import annotations

from gpmappy.transport import HttpTransport


def search_options_api(transport: HttpTransport) -> dict[str, object]:
    return transport.request_json("GET", "/v1/search/options")


def search_variants_api(
    transport: HttpTransport,
    query: str,
    rsquared_threshold: float = 0.8,
) -> dict[str, object]:
    return transport.request_json(
        "GET",
        f"/v1/search/variant/{query}",
        params={"rsquared_threshold": rsquared_threshold},
    )
