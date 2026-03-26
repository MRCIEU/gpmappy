"""Region endpoints."""

from __future__ import annotations

from typing import Any

from gpmappy.transport import HttpTransport


def region_api(
    transport: HttpTransport,
    region_id: str | int,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        f"/v1/regions/{region_id}",
        params={
            "include_associations": str(include_associations).lower(),
            "include_coloc_pairs": str(include_coloc_pairs).lower(),
            "h4_threshold": h4_threshold,
        },
    )
