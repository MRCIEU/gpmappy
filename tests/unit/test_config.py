from gpmappy.config import GpmapConfig


def test_config_from_environment_dev() -> None:
    config = GpmapConfig.from_environment("dev")
    assert config.base_url.startswith("http://localhost")


def test_config_from_environment_production() -> None:
    config = GpmapConfig.from_environment("production")
    assert config.base_url.startswith("https://")
