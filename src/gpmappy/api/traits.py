"""Trait endpoints."""

from __future__ import annotations

from typing import Any

import httpx

from gpmappy.transport import HttpTransport


def traits_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/traits")


def specific_traits_api(
    transport: HttpTransport,
    trait_ids: list[str | int],
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("ids", str(v)) for v in trait_ids]
    params.extend(
        [
            ("include_associations", str(include_associations).lower()),
            ("include_coloc_pairs", str(include_coloc_pairs).lower()),
            ("h4_threshold", str(h4_threshold)),
        ]
    )
    return transport.request_json("GET", "/v1/traits", params=httpx.QueryParams(params))


def trait_api(
    transport: HttpTransport,
    trait_id: str | int,
    include_associations: bool = False,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        f"/v1/traits/{trait_id}",
        params={"include_associations": str(include_associations).lower()},
    )


def trait_coloc_pairs_api(
    transport: HttpTransport,
    trait_id: str | int,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        f"/v1/traits/{trait_id}/coloc-pairs",
        params={"h4_threshold": h4_threshold},
    )
