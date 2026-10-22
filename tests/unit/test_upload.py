"""GWAS upload validation, mirroring gpmapr's upload_gwas() tests."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

import pytest

from gpmappy.client import GpmapClient
from gpmappy.exceptions import ApiError, ValidationError
from gpmappy.upload import build_gwas_column_names, check_gwas_file_columns

GUID = "123e4567-e89b-12d3-a456-426614174000"
HEADER = "chr\tpos\tea\toa\tp\tbeta\tse"
COLUMNS = {"chr_col": "chr", "bp_col": "pos", "ea_col": "ea", "oa_col": "oa"}


@pytest.fixture
def gwas_file(tmp_path: Path) -> Path:
    path = tmp_path / "gwas.tsv"
    path.write_text(f"{HEADER}\n1\t100\tA\tG\t1e-9\t0.1\t0.01\n")
    return path


@pytest.fixture
def upload(gwas_file: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    sent: dict[str, Any] = {}

    def fake_upload_gwas_api(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        sent.update(kwargs)
        return {"guid": GUID}

    monkeypatch.setattr("gpmappy.client.upload_gwas_api", fake_upload_gwas_api)

    def run(**kwargs: Any) -> dict[str, Any]:
        GpmapClient().upload_gwas(
            str(gwas_file), name="test", email="user@example.com", sample_size=1000, **kwargs
        )
        return sent

    return run


def test_upload_validates_column_arguments(upload: Any) -> None:
    with pytest.raises(ValidationError, match="Missing required column arguments: p_col"):
        upload(**COLUMNS, beta_col="beta", se_col="se")
    with pytest.raises(ValidationError, match="Either beta_col and se_col"):
        upload(**COLUMNS, p_col="p", beta_col="beta")
    with pytest.raises(ValidationError, match="Columns not found in file: pval"):
        upload(**COLUMNS, p_col="pval", beta_col="beta", se_col="se")
    with pytest.raises(ValidationError, match="not both"):
        upload(column_names={"CHR": "chr"}, chr_col="chr")
    with (
        pytest.raises(ValidationError, match="Unknown column_names: POS"),
        pytest.warns(FutureWarning),
    ):
        upload(column_names={"CHR": "chr", "POS": "pos"})
    with (
        pytest.warns(FutureWarning, match="deprecated"),
        pytest.raises(ValidationError, match="Missing required"),
    ):
        upload(column_names={"CHR": "chr", "BP": "pos"})
    with pytest.raises(ValidationError, match="p_col must be a single column name"):
        upload(**COLUMNS, p_col="", beta_col="beta", se_col="se")


def test_upload_sends_api_column_names_and_compare_guids(upload: Any) -> None:
    sent = upload(
        **COLUMNS, p_col="p", beta_col="beta", se_col="se", compare_with_upload_guids=GUID
    )
    assert sent["column_names"] == {
        "CHR": "chr",
        "BP": "pos",
        "EA": "ea",
        "OA": "oa",
        "P": "p",
        "BETA": "beta",
        "SE": "se",
    }
    # a single GUID must still be sent as a list
    assert sent["compare_with_upload_guids"] == [GUID]


def test_upload_rejects_invalid_compare_guids(upload: Any) -> None:
    with pytest.raises(ValidationError, match="vector of GUIDs"):
        upload(**COLUMNS, p_col="p", beta_col="b", se_col="s", compare_with_upload_guids=["x"])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": ""}, "name is required"),
        ({"email": None}, "email is required"),
        ({"category": "binary"}, "category"),
        ({"ancestry": "AFR"}, "ancestry"),
        ({"reference_build": "hg19"}, "reference_build"),
        ({"p_value_threshold": 0.05}, "p_value_threshold"),
        ({"sample_size": 0}, "sample_size"),
    ],
)
def test_upload_validates_metadata(gwas_file: Path, kwargs: dict[str, Any], message: str) -> None:
    arguments: dict[str, Any] = {
        "name": "test",
        "email": "user@example.com",
        "sample_size": 1000,
        **kwargs,
    }
    with pytest.raises(ValidationError, match=message):
        GpmapClient().upload_gwas(str(gwas_file), **arguments)


def test_legacy_column_names_are_mapped_to_api_column_names() -> None:
    with pytest.warns(FutureWarning):
        result = build_gwas_column_names(
            {
                "chr": "chr",
                "BP": "pos",
                "EA": "ea",
                "OA": "oa",
                "P": "p",
                "OR": "or",
                "LB": "lb",
                "UB": "ub",
            },
            {},
        )
    assert list(result) == ["CHR", "BP", "EA", "OA", "P", "OR", "OR_LB", "OR_UB"]
    assert result["OR_LB"] == "lb"


def test_header_check_reads_gzip_and_csv(tmp_path: Path) -> None:
    gz_path = tmp_path / "gwas.tsv.gz"
    with gzip.open(gz_path, "wt") as handle:
        handle.write(f"{HEADER}\n")
    check_gwas_file_columns(str(gz_path), {"CHR": "chr"})
    with pytest.raises(ValidationError, match="Columns not found in file: CHROM"):
        check_gwas_file_columns(str(gz_path), {"CHR": "CHROM"})

    csv_path = tmp_path / "gwas.csv"
    csv_path.write_text('"chr","pos"\n')
    with pytest.raises(ValidationError, match="Columns not found in file: p"):
        check_gwas_file_columns(str(csv_path), {"CHR": "chr", "P": "p"})


def test_header_check_is_skipped_when_the_header_is_unreadable(tmp_path: Path) -> None:
    single_column = tmp_path / "single.txt"
    single_column.write_text("everything\n")
    check_gwas_file_columns(str(single_column), {"CHR": "chr"})
    binary = tmp_path / "binary.gz"
    binary.write_bytes(b"not gzip")
    check_gwas_file_columns(str(binary), {"CHR": "chr"})


def test_delete_gwas_surfaces_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GpmapClient()

    def not_found(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ApiError(404, '{"detail": "Uploaded GWAS with GUID x not found"}')

    monkeypatch.setattr(client._transport, "request_json", not_found)
    with pytest.raises(ApiError, match=f"Failed to delete GWAS upload {GUID}: .* not found"):
        client.delete_gwas(GUID, "user@example.com")

    def plain_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ApiError(409, "upload is still processing")

    monkeypatch.setattr(client._transport, "request_json", plain_error)
    with pytest.raises(ApiError, match="still processing"):
        client.delete_gwas(GUID, "user@example.com")
