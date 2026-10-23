"""Association endpoints."""

from __future__ import annotations

from typing import Any

import httpx

from gpmappy.transport import HttpTransport


def associations_api(
    transport: HttpTransport,
    variant_ids: list[int],
    study_ids: list[int],
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("variant_ids", str(v)) for v in variant_ids]
    params.extend(("study_ids", str(v)) for v in study_ids)
    return transport.request_json("GET", "/v1/associations", params=httpx.QueryParams(params))
