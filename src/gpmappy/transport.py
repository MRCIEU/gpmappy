"""HTTP transport abstraction."""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Any

import httpx
from httpx._types import QueryParamTypes

from gpmappy.constants import (
    API_TO_PACKAGE_VERSION,
    API_VERSION_TIMEOUT_SECONDS,
    DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS,
    DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS,
    DEFAULT_RATE_LIMIT_MAX_RETRIES,
)
from gpmappy.exceptions import (
    ApiError,
    ApiVersionError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from gpmappy.version import package_version

HTTP_BAD_REQUEST = 400
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500
# Paths that work whatever the API version, so they skip the version check.
VERSION_CHECK_EXEMPT_PATHS = frozenset({"/health", "/v1/info/version"})


def api_error(status_code: int, text: str, reason: str = "") -> ApiError:
    """The error for an HTTP error response, explained by the API's ``detail`` when it sends one."""
    detail = _response_detail(text)
    if detail is None:
        category = "Client error" if status_code < HTTP_SERVER_ERROR else "Server error"
        detail = f"{category}: ({status_code}) {reason}".rstrip()
    return ApiError(status_code, f"GPMap API request failed (HTTP {status_code}): {detail}", detail)


def _response_detail(text: str) -> str | None:
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get("detail") is None:
        return None
    # Validation errors are lists of objects; flatten them like R's unlist().
    return "; ".join(str(value) for value in _flatten(payload["detail"]))


def _flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [item for nested in value.values() for item in _flatten(nested)]
    if isinstance(value, list):
        return [item for nested in value for item in _flatten(nested)]
    return [value]


def retry_delay_seconds(
    attempt: int,
    retry_after: str | None,
    base_delay: float = DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS,
    max_delay: float = DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS,
) -> float:
    """Seconds to wait before retrying a rate-limited (429) request.

    Honours a numeric ``Retry-After`` header when the API sends one, otherwise
    backs off exponentially with full jitter, capped at ``max_delay``.
    """
    if retry_after is not None:
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = math.nan
        if math.isfinite(seconds):
            return max(seconds, 0.0)
    capped_delay = min(max_delay, base_delay * 2**attempt)
    return random.uniform(0, capped_delay)


class HttpTransport:
    def __init__(  # noqa: PLR0913
        self,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        backoff_factor: float,
        user_agent: str,
        *,
        rate_limit_max_retries: int = DEFAULT_RATE_LIMIT_MAX_RETRIES,
        rate_limit_base_delay: float = DEFAULT_RATE_LIMIT_BASE_DELAY_SECONDS,
        rate_limit_max_delay: float = DEFAULT_RATE_LIMIT_MAX_DELAY_SECONDS,
        check_api_version: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limit_max_retries = rate_limit_max_retries
        self.rate_limit_base_delay = rate_limit_base_delay
        self.rate_limit_max_delay = rate_limit_max_delay
        self.check_api_version = check_api_version
        self._api_compatible = False
        self._client = httpx.Client(
            timeout=self.timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def ensure_api_compatible(self) -> bool:
        """Check that this gpmappy version supports the API's version, once per transport.

        Returns False, without caching, when the version can't be fetched (the request
        itself then reports the problem); raises ApiVersionError when it isn't supported.
        """
        if self._api_compatible:
            return True
        api_version = self._fetch_api_version()
        if api_version is None:
            return False
        version = package_version()
        if version not in API_TO_PACKAGE_VERSION.get(api_version, ()):
            raise ApiVersionError(
                f"gpmappy {version} does not support version {api_version} of the GPMap API at "
                f"{self.base_url}. Please update gpmappy with `pip install --upgrade gpmappy`."
            )
        self._api_compatible = True
        return True

    def _fetch_api_version(self) -> str | None:
        try:
            response = self._client.request(
                "GET", f"{self.base_url}/v1/info/version", timeout=API_VERSION_TIMEOUT_SECONDS
            )
            payload = response.json() if response.status_code < HTTP_BAD_REQUEST else None
        except (httpx.HTTPError, ValueError):
            return None
        version = payload.get("version") if isinstance(payload, dict) else None
        return str(version) if version else None

    def request_json(  # noqa: PLR0913
        self,
        method: str,
        path: str,
        *,
        params: QueryParamTypes | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(
            method, path, params=params, data=data, files=files, json_body=json_body
        )
        if not response.content:
            return {}
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(response.status_code, "Invalid JSON response") from exc
        if isinstance(payload, dict):
            return payload
        raise ApiError(response.status_code, "Expected JSON object response")

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: QueryParamTypes | None = None,
    ) -> bytes:
        response = self._request(method, path, params=params)
        return response.content

    def download_to_path(
        self,
        url: str,
        destination: str | Path,
    ) -> Path:
        path = Path(destination)
        response = self._request("GET", url, absolute=True)
        path.write_bytes(response.content)
        return path

    def _request(  # noqa: PLR0913
        self,
        method: str,
        path: str,
        *,
        params: QueryParamTypes | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> httpx.Response:
        url = path if absolute else f"{self.base_url}{path}"
        if self.check_api_version and not absolute and path not in VERSION_CHECK_EXEMPT_PATHS:
            self.ensure_api_compatible()
        attempt = 0
        rate_limit_attempt = 0
        while True:
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    files=files,
                    json=json_body,
                )
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise TimeoutError(
                        f"Could not reach the GPMap API at {self.base_url}: request timed out"
                    ) from exc
                time.sleep(self.backoff_factor * (2**attempt))
                attempt += 1
                continue
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise NetworkError(
                        f"Could not reach the GPMap API at {self.base_url}: {exc}"
                    ) from exc
                time.sleep(self.backoff_factor * (2**attempt))
                attempt += 1
                continue

            # Rate limiting has its own retry budget so it never eats into the
            # retries reserved for network failures and server errors.
            if response.status_code == HTTP_TOO_MANY_REQUESTS:
                if rate_limit_attempt >= self.rate_limit_max_retries:
                    raise RateLimitError(self.rate_limit_max_retries)
                time.sleep(
                    retry_delay_seconds(
                        rate_limit_attempt,
                        response.headers.get("retry-after"),
                        self.rate_limit_base_delay,
                        self.rate_limit_max_delay,
                    )
                )
                rate_limit_attempt += 1
                continue

            if response.status_code >= HTTP_BAD_REQUEST:
                if attempt >= self.max_retries or response.status_code < HTTP_SERVER_ERROR:
                    raise api_error(
                        response.status_code, response.text, getattr(response, "reason_phrase", "")
                    )
                time.sleep(self.backoff_factor * (2**attempt))
                attempt += 1
                continue
            return response
