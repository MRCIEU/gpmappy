"""Gene endpoints."""

from __future__ import annotations

from typing import Any

import httpx

from gpmappy.transport import HttpTransport


def genes_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/genes")


def specific_genes_api(
    transport: HttpTransport,
    gene_ids: list[str],
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    include_trans: bool = True,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("ids", v) for v in gene_ids]
    params.extend(
        [
            ("include_associations", str(include_associations).lower()),
            ("include_coloc_pairs", str(include_coloc_pairs).lower()),
            ("include_trans", str(include_trans).lower()),
            ("h4_threshold", str(h4_threshold)),
        ]
    )
    return transport.request_json("GET", "/v1/genes", params=httpx.QueryParams(params))


def gene_api(
    transport: HttpTransport,
    gene_id: str,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    include_trans: bool = True,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        f"/v1/genes/{gene_id}",
        params={
            "include_associations": str(include_associations).lower(),
            "include_coloc_pairs": str(include_coloc_pairs).lower(),
            "include_trans": str(include_trans).lower(),
            "h4_threshold": h4_threshold,
        },
    )
