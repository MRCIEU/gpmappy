"""Health and version endpoints."""

from __future__ import annotations

from gpmappy.transport import HttpTransport


def health_api(transport: HttpTransport) -> dict[str, object]:
    return transport.request_json("GET", "/health")


def version_api(transport: HttpTransport) -> str:
    payload = transport.request_json("GET", "/v1/info/version")
    return str(payload.get("version", ""))
