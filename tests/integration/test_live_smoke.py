import pytest

from gpmappy.client import GpmapClient


@pytest.mark.integration
@pytest.mark.live
def test_live_health_smoke() -> None:
    client = GpmapClient()
    result = client.health_api()
    assert "status" in result
