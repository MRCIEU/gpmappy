"""Pleiotropy endpoints."""

from __future__ import annotations

from typing import Any

from gpmappy.transport import HttpTransport


def gene_pleiotropies_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/pleiotropy/genes")


def snp_pleiotropies_api(transport: HttpTransport) -> dict[str, Any]:
    return transport.request_json("GET", "/v1/pleiotropy/snps")
