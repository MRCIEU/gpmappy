"""Client implementation."""

from __future__ import annotations

from gpmappy.config import ApiEnvironment, GpmapConfig
from gpmappy.constants import DEV_BASE_URL, PRODUCTION_BASE_URL
from gpmappy.transport import HttpTransport


class GpmapClient:
    def __init__(self, config: GpmapConfig | None = None) -> None:
        self._config = config or GpmapConfig()
        self._transport = HttpTransport(
            base_url=self._config.base_url,
            timeout_seconds=self._config.timeout_seconds,
            max_retries=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            user_agent=self._config.user_agent,
        )

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def close(self) -> None:
        self._transport.close()

    def select_api(self, api: str = "production") -> None:
        if api == ApiEnvironment.PRODUCTION.value:
            self.set_base_url(PRODUCTION_BASE_URL)
            return
        if api == ApiEnvironment.DEV.value:
            self.set_base_url(DEV_BASE_URL)
            return
        raise ValueError("Invalid API environment")

    def set_base_url(self, url: str) -> None:
        self._transport.close()
        self._config.base_url = url.rstrip("/")
        self._transport = HttpTransport(
            base_url=self._config.base_url,
            timeout_seconds=self._config.timeout_seconds,
            max_retries=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            user_agent=self._config.user_agent,
        )

    def health_api(self) -> dict[str, object]:
        return self._transport.request_json("GET", "/health")

    def version_api(self) -> str:
        payload = self._transport.request_json("GET", "/v1/info/version")
        version = payload.get("version")
        return str(version)
