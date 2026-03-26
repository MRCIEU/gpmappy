import tempfile
from pathlib import Path

import pytest

from gpmappy.client import GpmapClient
from gpmappy.exceptions import ValidationError


def test_variants_limit_with_expand() -> None:
    client = GpmapClient()
    with pytest.raises(ValidationError):
        client.variants(list(range(11)), expand=True)


def test_variants_limit_without_expand() -> None:
    client = GpmapClient()
    with pytest.raises(ValidationError):
        client.variants(list(range(51)), expand=False)


def test_upload_validation_requires_existing_file() -> None:
    client = GpmapClient()
    with pytest.raises(ValidationError):
        client.upload_gwas(
            file="/tmp/does-not-exist.tsv",
            name="name",
            email="email@example.com",
            sample_size=1000,
        )


def test_upload_validation_accepts_valid_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GpmapClient()

    def fake_upload_gwas_api(*args, **kwargs):  # type: ignore[no-untyped-def]
        return {"status": "ok"}

    monkeypatch.setattr("gpmappy.client.upload_gwas_api", fake_upload_gwas_api)

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        path = Path(temp_file.name)

    try:
        result = client.upload_gwas(
            file=str(path),
            name="Test",
            email="email@example.com",
            sample_size=1000,
        )
        assert result["status"] == "ok"
    finally:
        path.unlink(missing_ok=True)
