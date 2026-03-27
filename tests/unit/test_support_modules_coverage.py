from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from gpmappy import tabular
from gpmappy.cache import TTLCache
from gpmappy.exceptions import ApiError, NetworkError, OptionalDependencyError, TimeoutError
from gpmappy.merge import merge_associations
from gpmappy.tabular import maybe_table, records_to_table
from gpmappy.transport import HttpTransport
from gpmappy.utils import build_multi_params

EXPECTED_RARE_STUDY_ID = 2
MERGED_BETA = 0.3


class _Response:
    def __init__(self, status_code: int, text: str = "ok", payload: Any = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload
        self.content = text.encode()

    def json(self) -> Any:
        if self._payload == "invalid_json":
            raise json.JSONDecodeError("x", "y", 1)
        return self._payload


def test_transport_success_and_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpTransport("https://example.test", 1, 1, 0, "ua")

    def fake_request(*args: Any, **kwargs: Any) -> _Response:
        return _Response(200, text="abc", payload={"value": 1})

    monkeypatch.setattr(transport._client, "request", fake_request)

    assert transport.request_json("GET", "/ok") == {"value": 1}
    assert transport.request_bytes("GET", "/bytes") == b"abc"

    out_path = tmp_path / "out.txt"
    saved = transport.download_to_path("https://example.test/file", out_path)
    assert saved.read_bytes() == b"abc"


def test_transport_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpTransport("https://example.test", 1, 0, 0, "ua")

    def fake_request_404(*args: Any, **kwargs: Any) -> _Response:
        return _Response(404, text="missing", payload={"detail": "missing"})

    monkeypatch.setattr(transport._client, "request", fake_request_404)
    with pytest.raises(ApiError):
        transport.request_json("GET", "/missing")

    def fake_request_invalid(*args: Any, **kwargs: Any) -> _Response:
        return _Response(200, text="ok", payload="invalid_json")

    monkeypatch.setattr(transport._client, "request", fake_request_invalid)
    with pytest.raises(ApiError):
        transport.request_json("GET", "/badjson")

    def fake_request_list(*args: Any, **kwargs: Any) -> _Response:
        return _Response(200, text="ok", payload=[1, 2])

    monkeypatch.setattr(transport._client, "request", fake_request_list)
    with pytest.raises(ApiError):
        transport.request_json("GET", "/list")


def test_transport_retry_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpTransport("https://example.test", 1, 0, 0, "ua")

    def raise_timeout(*args: Any, **kwargs: Any) -> _Response:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(transport._client, "request", raise_timeout)
    with pytest.raises(TimeoutError):
        transport.request_bytes("GET", "/timeout")

    def raise_http_error(*args: Any, **kwargs: Any) -> _Response:
        raise httpx.HTTPError("net")

    monkeypatch.setattr(transport._client, "request", raise_http_error)
    with pytest.raises(NetworkError):
        transport.request_bytes("GET", "/network")


def test_cache_tabular_merge_and_utils_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    cache: TTLCache[str] = TTLCache(ttl_seconds=1)
    cache.set("a", "b")
    assert cache.get("a") == "b"

    # force expiry path
    monkeypatch.setattr("gpmappy.cache.time.time", lambda: 3_000_000_000)
    assert cache.get("a") is None

    monkeypatch.setattr(tabular, "_pd", None)
    with pytest.raises(OptionalDependencyError):
        records_to_table([{"x": 1}], as_dataframe=True)

    assert maybe_table([{"x": 1}], as_dataframe=False) == [{"x": 1}]
    assert maybe_table({"x": 1}, as_dataframe=False) == {"x": 1}

    coloc, rare = merge_associations(
        [{"study_id": 1, "snp_id": 1}], [{"study_id": 2, "snp_id": 2}], []
    )
    assert coloc[0]["study_id"] == 1
    assert rare[0]["study_id"] == EXPECTED_RARE_STUDY_ID

    merged_coloc, merged_rare = merge_associations(
        [{"study_id": 1, "snp_id": 1}],
        [{"study_id": 1, "snp_id": 1}],
        [{"study_id": 1, "snp_id": 1, "beta": MERGED_BETA}],
    )
    assert merged_coloc[0]["beta"] == MERGED_BETA
    assert merged_rare[0]["beta"] == MERGED_BETA

    assert build_multi_params("ids", [1, "a"]) == "ids=1&ids=a"
