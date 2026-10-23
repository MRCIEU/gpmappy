"""Trait endpoints."""

from __future__ import annotations

from typing import Any

import httpx

from gpmappy.transport import HttpTransport
from gpmappy.utils import rows_to_records


def traits_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/traits")


def trait_duplicates_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/traits/duplicates")


def specific_traits_api(
    transport: HttpTransport,
    trait_ids: list[str | int],
    include_associations: bool = False,
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("ids", str(v)) for v in trait_ids]
    params.append(("include_associations", str(include_associations).lower()))
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
) -> list[dict[str, Any]]:
    payload = transport.request_json(
        "GET",
        f"/v1/traits/{trait_id}/coloc-pairs",
        params={"h4_threshold": h4_threshold},
    )
    return rows_to_records(
        payload.get("coloc_pair_column_names") or [], payload.get("coloc_pair_rows") or []
    )


def trait_associations_full_api(
    transport: HttpTransport,
    trait_id: str | int,
) -> list[dict[str, Any]]:
    payload = transport.request_json("GET", f"/v1/traits/{trait_id}/associations-full")
    return rows_to_records(
        payload.get("associations_full_column_names") or [],
        payload.get("associations_full_rows") or [],
    )
