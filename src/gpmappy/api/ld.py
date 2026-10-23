"""LD endpoints."""

from __future__ import annotations

from typing import Any

import httpx

from gpmappy.transport import HttpTransport


def ld_proxies_by_variant_api(
    transport: HttpTransport, variants: list[str | int]
) -> dict[str, Any]:
    params = httpx.QueryParams([("variants", str(v)) for v in variants])
    return transport.request_json("GET", "/v1/ld/proxies", params=params)


def ld_proxies_by_variant_id_api(
    transport: HttpTransport, variant_ids: list[int]
) -> dict[str, Any]:
    params = httpx.QueryParams([("variant_ids", str(v)) for v in variant_ids])
    return transport.request_json("GET", "/v1/ld/proxies", params=params)


def ld_matrix_by_variant_api(transport: HttpTransport, variants: list[str | int]) -> dict[str, Any]:
    params = httpx.QueryParams([("variants", str(v)) for v in variants])
    return transport.request_json("GET", "/v1/ld/matrix", params=params)


def ld_matrix_by_variant_id_api(transport: HttpTransport, variant_ids: list[int]) -> dict[str, Any]:
    params = httpx.QueryParams([("variant_ids", str(v)) for v in variant_ids])
    return transport.request_json("GET", "/v1/ld/matrix", params=params)
