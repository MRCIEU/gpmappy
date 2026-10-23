"""compare_upload(), mirroring gpmapr's tests/testthat/test_compare_upload.R.

Uses gpmapr's hand-written GWAS upload fixture: coloc group 1 has the upload (AD GWAS,
upload 90), allergic rhinitis (trait 2527), a compared upload (144) and type 1 diabetes,
whose p-value is smaller than all of theirs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gpmappy import tabular
from gpmappy.client import GpmapClient
from gpmappy.compare import compare_upload
from gpmappy.exceptions import ValidationError

FIXTURES = Path(__file__).parents[1] / "contract" / "gpmapr" / "fixtures"
GUID = "7a289615-c1b4-91f3-3d97-887f60de9155"
COMPARED_GUID = "11111111-2222-3333-4444-555555555555"


class _UploadTransport:
    def close(self) -> None:
        pass

    def request_json(self, method: str, path: str, *, params: Any = None, **_: Any) -> Any:
        name = "gwas-upload-associations.json" if params else "gwas-upload.json"
        return json.loads((FIXTURES / name).read_text())


def get_upload(include_associations: bool = True, as_dataframe: bool | None = False) -> Any:
    client = GpmapClient()
    client._transport = _UploadTransport()  # type: ignore[assignment]
    return client.get_gwas(
        GUID, include_associations=include_associations, as_dataframe=as_dataframe
    )


def test_lines_up_the_uploads_own_effect_with_the_traits() -> None:
    groups = compare_upload(get_upload(), 2527, as_dataframe=False)["coloc_groups"]
    assert len(groups) == 1
    group = groups[0]
    assert (group["coloc_group_id"], group["variant_id"]) == (1, 100)
    # The upload's own row, not type 1 diabetes, which has the smallest p-value in the group.
    assert group["upload_study_extraction_id"] == 7223  # noqa: PLR2004
    assert group["upload_beta"] == 0.5  # noqa: PLR2004
    assert group["trait_name"] == "Allergic rhinitis"
    assert group["trait_study_extraction_id"] == 32958  # noqa: PLR2004
    assert group["trait_beta"] == 0.2  # noqa: PLR2004


def test_returns_the_coloc_pairs_between_upload_and_trait_upload_first() -> None:
    pairs = compare_upload(get_upload(), 2527, as_dataframe=False)["coloc_pairs"]
    assert [p["upload_study_extraction_id"] for p in pairs] == [7223, 7225]
    assert [p["trait_study_extraction_id"] for p in pairs] == [32958, 40000]
    assert [p["h4"] for p in pairs] == [0.9, 0.95]
    assert [p["in_shared_coloc_group"] for p in pairs] == [True, False]


def test_compares_with_another_upload_by_its_guid() -> None:
    comparison = compare_upload(get_upload(), COMPARED_GUID, as_dataframe=False)
    assert comparison["coloc_groups"][0]["trait_name"] == "Compared GWAS"
    assert comparison["coloc_groups"][0]["trait_beta"] == 0.45  # noqa: PLR2004
    assert [p["trait_study_extraction_id"] for p in comparison["coloc_pairs"]] == [8001]


def test_skips_rows_whose_association_is_a_placeholder() -> None:
    comparison = compare_upload(get_upload(), 21, as_dataframe=False)
    assert comparison["coloc_groups"] == []
    assert [p["trait_study_extraction_id"] for p in comparison["coloc_pairs"]] == [7223]


def test_returns_empty_tables_for_a_trait_the_upload_does_not_colocalise_with() -> None:
    assert compare_upload(get_upload(), 999999, as_dataframe=False) == {
        "coloc_groups": [],
        "coloc_pairs": [],
    }


@pytest.mark.skipif(not tabular.pandas_available(), reason="needs pandas")
def test_accepts_dataframe_results() -> None:
    comparison = compare_upload(get_upload(as_dataframe=True), 2527, as_dataframe=False)
    assert comparison["coloc_groups"][0]["trait_beta"] == 0.2  # noqa: PLR2004
    assert len(comparison["coloc_pairs"]) == 2  # noqa: PLR2004


def test_explains_what_it_needs() -> None:
    with pytest.raises(ValidationError, match="include_associations = TRUE"):
        compare_upload(get_upload(include_associations=False), 2527)
    with pytest.raises(ValidationError, match="GWAS upload result"):
        compare_upload({"trait": {"id": 1}}, 2527)
    with pytest.raises(ValidationError, match="single trait id"):
        compare_upload(get_upload(), [1, 2])
    with pytest.raises(ValidationError, match="not a GWAS upload this upload was compared with"):
        compare_upload(get_upload(), "99999999-2222-3333-4444-555555555555")
