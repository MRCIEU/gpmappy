"""The API version gate and error messages, mirroring gpmapr's test_version_gate.R."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import pytest

from gpmappy.client import GpmapClient
from gpmappy.config import GpmapConfig
from gpmappy.exceptions import ApiError, ApiVersionError, NetworkError, TimeoutError
from gpmappy.transport import HttpTransport, api_error


class _Response:
    def __init__(self, status_code: int, payload: Any, reason_phrase: str = "") -> None:
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.content = self.text.encode()
        self.reason_phrase = reason_phrase
        self.headers: dict[str, str] = {}
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def gated_transport(
    monkeypatch: pytest.MonkeyPatch, api_version: str | None, package: str = "1.0.0"
) -> tuple[HttpTransport, list[str]]:
    transport = HttpTransport("https://example.test", 1, 0, 0, "ua", check_api_version=True)
    paths: list[str] = []

    def fake_request(method: str, url: str, **_: Any) -> _Response:
        path = url.replace("https://example.test", "")
        paths.append(path)
        if path == "/v1/info/version":
            if api_version is None:
                raise httpx.ConnectError("unreachable")
            return _Response(200, {"version": api_version})
        return _Response(200, {"status": "healthy"})

    monkeypatch.setattr(transport._client, "request", fake_request)
    monkeypatch.setattr("gpmappy.transport.package_version", lambda: package)
    return transport, paths


def test_a_supported_api_version_passes_and_is_checked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, paths = gated_transport(monkeypatch, "1.1.0")
    transport.request_json("GET", "/v1/traits")
    transport.request_json("GET", "/v1/genes")
    assert paths == ["/v1/info/version", "/v1/traits", "/v1/genes"]


@pytest.mark.parametrize(
    ("api_version", "package"), [("1.0.1", "1.0.0"), ("1.1.0", "0.1.1"), ("99.0.0", "1.0.0")]
)
def test_an_unsupported_api_version_stops_with_upgrade_instructions(
    monkeypatch: pytest.MonkeyPatch, api_version: str, package: str
) -> None:
    transport, paths = gated_transport(monkeypatch, api_version, package)
    with pytest.raises(
        ApiVersionError,
        match=f"gpmappy {package} does not support version {api_version}.*pip install --upgrade",
    ):
        transport.request_json("GET", "/v1/traits")
    assert paths == ["/v1/info/version"]


def test_an_unreachable_version_endpoint_does_not_block_and_is_not_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, paths = gated_transport(monkeypatch, None)
    transport.request_json("GET", "/v1/traits")
    transport.request_json("GET", "/v1/traits")
    assert paths == ["/v1/info/version", "/v1/traits"] * 2


def test_the_version_and_health_endpoints_skip_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    transport, paths = gated_transport(monkeypatch, "99.0.0")
    transport.request_json("GET", "/health")
    assert paths == ["/health"]


def test_gpmap_available_is_false_for_an_unsupported_api(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GpmapClient()
    transport, _ = gated_transport(monkeypatch, "1.1.0")
    client._transport = transport
    assert client.gpmap_available()

    client._transport, _ = gated_transport(monkeypatch, "1.0.1")
    assert not client.gpmap_available()

    unreachable = GpmapClient(
        GpmapConfig(base_url="http://127.0.0.1:9", max_retries=0, timeout_seconds=0.5)
    )
    assert not unreachable.gpmap_available()


def test_the_client_checks_the_version_unless_disabled() -> None:
    assert GpmapClient()._transport.check_api_version
    assert not GpmapClient(GpmapConfig(check_api_version=False))._transport.check_api_version


def test_http_errors_give_an_informative_message() -> None:
    error = api_error(404, '{"detail": "Trait 999999999 not found"}')
    assert str(error) == "GPMap API request failed (HTTP 404): Trait 999999999 not found"
    assert error.detail == "Trait 999999999 not found"
    validation = api_error(
        422, json.dumps({"detail": [{"loc": ["query", "ids"], "msg": "Field required"}]})
    )
    assert str(validation) == "GPMap API request failed (HTTP 422): query; ids; Field required"
    assert str(api_error(500, "<html>", "Internal Server Error")) == (
        "GPMap API request failed (HTTP 500): Server error: (500) Internal Server Error"
    )
    assert isinstance(error, ApiError)


def test_connection_failures_name_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpTransport("https://example.test", 1, 0, 0, "ua")

    def refuse(*_a: Any, **_k: Any) -> Any:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(transport._client, "request", refuse)
    with pytest.raises(
        NetworkError,
        match=re.escape(
            "Could not reach the GPMap API at https://example.test: connection refused"
        ),
    ):
        transport.request_json("GET", "/v1/traits")

    def time_out(*_a: Any, **_k: Any) -> Any:
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(transport._client, "request", time_out)
    with pytest.raises(
        TimeoutError, match=re.escape("Could not reach the GPMap API at https://example.test")
    ):
        transport.request_json("GET", "/v1/traits")
