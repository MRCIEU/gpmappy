from gpmappy.wrappers import get_default_client, health_api, set_default_client


class _DummyClient:
    def health_api(self):  # type: ignore[no-untyped-def]
        return {"status": "healthy"}


def test_set_default_client_roundtrip() -> None:
    original = get_default_client()
    dummy = _DummyClient()
    try:
        set_default_client(dummy)  # type: ignore[arg-type]
        assert health_api()["status"] == "healthy"
    finally:
        set_default_client(original)
