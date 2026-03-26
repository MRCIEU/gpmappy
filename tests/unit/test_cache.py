from gpmappy.cache import TTLCache


def test_ttl_cache_roundtrip() -> None:
    cache: TTLCache[str] = TTLCache(ttl_seconds=100)
    cache.set("k", "v")
    assert cache.get("k") == "v"
