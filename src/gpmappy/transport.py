"""HTTP transport abstraction."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from httpx._types import QueryParamTypes

from gpmappy.exceptions import ApiError, NetworkError, TimeoutError


class HttpTransport:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        backoff_factor: float,
        user_agent: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client = httpx.Client(
            timeout=self.timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: QueryParamTypes | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(method, path, params=params, data=data, files=files)
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

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: QueryParamTypes | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> httpx.Response:
        url = path if absolute else f"{self.base_url}{path}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    files=files,
                )
            except httpx.TimeoutException as exc:
                if attempt == self.max_retries:
                    raise TimeoutError("Request timed out") from exc
                time.sleep(self.backoff_factor * (2**attempt))
                continue
            except httpx.HTTPError as exc:
                if attempt == self.max_retries:
                    raise NetworkError(str(exc)) from exc
                time.sleep(self.backoff_factor * (2**attempt))
                continue

            if response.status_code >= 400:
                if attempt == self.max_retries or response.status_code < 500:
                    message = response.text
                    raise ApiError(response.status_code, message)
                time.sleep(self.backoff_factor * (2**attempt))
                continue
            return response

        raise NetworkError("Request failed after retries")
