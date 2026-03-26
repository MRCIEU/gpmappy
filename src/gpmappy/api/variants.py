"""Variant endpoints."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any, cast

import httpx
import pandas as pd

from gpmappy.transport import HttpTransport


def variants_api(
    transport: HttpTransport,
    variants: list[str | int],
    expand: bool = False,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("variants", str(v)) for v in variants]
    params.extend(
        [
            ("expand", str(expand).lower()),
            ("include_associations", str(include_associations).lower()),
            ("include_coloc_pairs", str(include_coloc_pairs).lower()),
            ("h4_threshold", str(h4_threshold)),
        ]
    )
    return transport.request_json("GET", "/v1/variants", params=httpx.QueryParams(params))


def variants_grange_api(
    transport: HttpTransport,
    chr_value: str,
    start: int,
    stop: int,
    include_associations: bool = False,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        "/v1/variants",
        params={
            "grange": f"{chr_value}:{start}-{stop}",
            "expand": "false",
            "include_associations": str(include_associations).lower(),
            "include_coloc_pairs": str(include_coloc_pairs).lower(),
            "h4_threshold": h4_threshold,
        },
    )


def variant_api(
    transport: HttpTransport,
    snp_id: str | int,
    include_coloc_pairs: bool = False,
    h4_threshold: float = 0.8,
) -> dict[str, Any]:
    return transport.request_json(
        "GET",
        f"/v1/variants/{snp_id}",
        params={
            "include_coloc_pairs": str(include_coloc_pairs).lower(),
            "h4_threshold": h4_threshold,
        },
    )


def variant_summary_stats_api(
    transport: HttpTransport,
    snp_id: str | int,
) -> dict[str, pd.DataFrame]:
    payload = transport.request_bytes("GET", f"/v1/variants/{snp_id}/summary-stats")
    with tempfile.TemporaryDirectory(prefix="gpmappy_variant_") as tmpdir:
        zip_path = Path(tmpdir) / f"summary_stats_{snp_id}.zip"
        zip_path.write_bytes(payload)
        dataframes: dict[str, pd.DataFrame] = {}
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)
        for gz_path in Path(tmpdir).glob("*.tsv.gz"):
            key = gz_path.name.replace(".tsv.gz", "").replace("_with_lbfs", "")
            df = cast(pd.DataFrame, pd.read_csv(gz_path, sep="\t"))  # type: ignore[arg-type]
            dataframes[key] = df
        return dataframes
