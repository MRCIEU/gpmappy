"""GWAS endpoints."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, cast

import pandas as pd

from gpmappy.transport import HttpTransport


def get_gwas_api(
    transport: HttpTransport,
    gwas_id: str,
) -> dict[str, Any]:
    return transport.request_json("GET", f"/v1/gwas/{gwas_id}")


def get_gwas_summary_stats_api(
    transport: HttpTransport,
    gwas_id: str,
) -> pd.DataFrame:
    summary_stats_url_payload = transport.request_json("GET", f"/v1/gwas/{gwas_id}/summary-stats")
    summary_stats_url = str(summary_stats_url_payload.get("url", summary_stats_url_payload))

    with tempfile.TemporaryDirectory(prefix="gpmappy_gwas_") as tmpdir:
        file_path = Path(tmpdir) / f"gwas_summary_stats_{gwas_id}.tsv.gz"
        transport.download_to_path(summary_stats_url, file_path)
        return cast(pd.DataFrame, pd.read_csv(file_path, sep="\t"))  # type: ignore[arg-type]


def upload_gwas_api(
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
    }
    with open(file, "rb") as fobj:
        files = {
            "file": (Path(file).name, fobj),
            "request": (None, json.dumps(request_payload)),
        }
        return transport.request_json("POST", "/v1/gwas", files=files)
