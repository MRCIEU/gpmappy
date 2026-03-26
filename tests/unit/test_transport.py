import pytest

from gpmappy.exceptions import ApiError
from gpmappy.transport import HttpTransport


def test_transport_handles_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpTransport(
        base_url="https://example.org",
        timeout_seconds=1,
        max_retries=0,
        backoff_factor=0,
        user_agent="test",
    )

    class _Resp:
        status_code = 404
        text = "not found"

        def json(self):  # type: ignore[no-untyped-def]
            return {"detail": "not found"}

    def fake_request(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _Resp()

    monkeypatch.setattr(transport._client, "request", fake_request)
    with pytest.raises(ApiError):
        transport.request_json("GET", "/missing")
