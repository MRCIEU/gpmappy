"""GWAS endpoints."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from gpmappy.exceptions import ApiError
from gpmappy.parsers import read_tsv_gz_records
from gpmappy.transport import HttpTransport


def get_gwas_api(
    transport: HttpTransport,
    gwas_id: str,
    include_associations: bool = False,
) -> dict[str, Any]:
    params = {"include_associations": "true"} if include_associations else None
    return transport.request_json("GET", f"/v1/gwas/{gwas_id}", params=params)


def get_gwas_summary_stats_api(
    transport: HttpTransport,
    gwas_id: str,
) -> list[dict[str, str]]:
    summary_stats_url_payload = transport.request_json("GET", f"/v1/gwas/{gwas_id}/summary-stats")
    summary_stats_url = str(summary_stats_url_payload.get("url", summary_stats_url_payload))

    with tempfile.TemporaryDirectory(prefix="gpmappy_gwas_") as tmpdir:
        file_path = Path(tmpdir) / f"gwas_summary_stats_{gwas_id}.tsv.gz"
        transport.download_to_path(summary_stats_url, file_path)
        return read_tsv_gz_records(file_path)


def upload_gwas_api(  # noqa: PLR0913
    transport: HttpTransport,
    file: str,
    name: str,
    p_value_threshold: float,
    column_names: dict[str, str],
    email: str,
    category: str,
    is_published: bool,
    doi: str | None,
    should_be_added: bool,
    ancestry: str,
    sample_size: int | float,
    reference_build: str,
    compare_with_upload_guids: list[str] | None = None,
) -> dict[str, Any]:
    request_payload = {
        "reference_build": reference_build,
        "email": email,
        "name": name,
        "category": category,
        "is_published": is_published,
        "doi": doi,
        "should_be_added": should_be_added,
        "ancestry": ancestry,
        "sample_size": sample_size,
        "p_value_threshold": p_value_threshold,
        "column_names": column_names,
        "compare_with_upload_guids": compare_with_upload_guids,
    }
    with open(file, "rb") as fobj:
        files = {
            "file": (Path(file).name, fobj),
            "request": (None, json.dumps(request_payload)),
        }
        return transport.request_json("POST", "/v1/gwas", files=files)


def delete_gwas_api(
    transport: HttpTransport,
    guid: str,
    email: str,
) -> dict[str, Any]:
    try:
        return transport.request_json("DELETE", f"/v1/gwas/{guid}", json_body={"email": email})
    except ApiError as exc:
        raise ApiError(
            exc.status_code, f"Failed to delete GWAS upload {guid}: {_error_detail(exc.message)}"
        ) from exc


def _error_detail(message: str) -> str:
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return message
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return message
