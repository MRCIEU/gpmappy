"""Rate-limit (429) retries, mirroring gpmapr's tests/testthat/test_api_retry.R."""

from __future__ import annotations

from typing import Any

import pytest

from gpmappy.exceptions import ApiError, RateLimitError
from gpmappy.transport import HttpTransport, retry_delay_seconds

RETRY_AFTER_SECONDS = 5
MAX_DELAY = 8
TWO_RETRIES = 2
THREE_CALLS = 3


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.text = "{}"
        self.content = b'{"ok": true}'

    def json(self) -> Any:
        return {"ok": True}


def _transport(
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[int],
    max_retries: int = 0,
    rate_limit_max_retries: int = 5,
) -> tuple[HttpTransport, list[dict[str, Any]], list[float]]:
    transport = HttpTransport(
        "https://example.test",
        1,
        max_retries,
        0,
        "ua",
        rate_limit_max_retries=rate_limit_max_retries,
        rate_limit_base_delay=0.001,
        rate_limit_max_delay=0.002,
    )
    calls: list[dict[str, Any]] = []
    sleeps: list[float] = []

    def fake_request(*args: Any, **kwargs: Any) -> _Response:
        calls.append(kwargs)
        return _Response(statuses[min(len(calls), len(statuses)) - 1])

    monkeypatch.setattr(transport._client, "request", fake_request)
    monkeypatch.setattr("gpmappy.transport.time.sleep", sleeps.append)
    return transport, calls, sleeps


def test_retries_on_429_and_returns_the_eventual_success(monkeypatch: pytest.MonkeyPatch) -> None:
    transport, calls, sleeps = _transport(monkeypatch, [429, 429, 200])
    assert transport.request_json("GET", "/v1/traits") == {"ok": True}
    assert len(calls) == THREE_CALLS
    assert len(sleeps) == TWO_RETRIES


def test_passes_non_429_responses_straight_through(monkeypatch: pytest.MonkeyPatch) -> None:
    transport, calls, sleeps = _transport(monkeypatch, [404])
    with pytest.raises(ApiError) as excinfo:
        transport.request_json("GET", "/v1/traits/0")
    assert not isinstance(excinfo.value, RateLimitError)
    assert len(calls) == 1
    assert sleeps == []


def test_errors_after_exhausting_retries_on_persistent_429s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, calls, _ = _transport(monkeypatch, [429], rate_limit_max_retries=2)
    with pytest.raises(RateLimitError, match="rate limit exceeded after 2 retries"):
        transport.request_json("GET", "/v1/traits")
    assert len(calls) == THREE_CALLS


def test_rate_limit_retries_do_not_use_the_network_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, calls, _ = _transport(monkeypatch, [429, 200], max_retries=0)
    assert transport.request_bytes("GET", "/v1/traits") == b'{"ok": true}'
    assert len(calls) == TWO_RETRIES


def test_honours_retry_after_from_the_response(monkeypatch: pytest.MonkeyPatch) -> None:
    transport, _, sleeps = _transport(monkeypatch, [429, 200])
    responses = iter([_Response(429, {"retry-after": "5"}), _Response(200)])
    monkeypatch.setattr(transport._client, "request", lambda *a, **k: next(responses))
    transport.request_json("GET", "/v1/traits")
    assert sleeps == [RETRY_AFTER_SECONDS]


def test_retry_delay_honours_a_numeric_retry_after_header() -> None:
    assert retry_delay_seconds(0, "5") == RETRY_AFTER_SECONDS
    assert retry_delay_seconds(0, "-3") == 0


def test_retry_delay_falls_back_to_bounded_exponential_backoff() -> None:
    for retry_after in (None, "Wed, 21 Oct 2026 07:28:00 GMT", "nan"):
        delays = [
            retry_delay_seconds(attempt, retry_after, base_delay=1, max_delay=MAX_DELAY)
            for attempt in range(5)
        ]
        assert all(0 <= delay <= MAX_DELAY for delay in delays)


def test_json_body_is_sent_and_empty_responses_decode_to_empty_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, calls, _ = _transport(monkeypatch, [200])
    empty = _Response(200)
    empty.content = b""
    monkeypatch.setattr(
        transport._client, "request", lambda *a, **k: calls.append(k) or empty  # type: ignore[func-returns-value]
    )
    assert transport.request_json("DELETE", "/v1/gwas/x", json_body={"email": "a@b.com"}) == {}
    assert calls[-1]["json"] == {"email": "a@b.com"}
