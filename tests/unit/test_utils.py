from gpmappy.utils import create_source_url, is_guid, tabular_payload_to_records


def test_is_guid_true() -> None:
    assert is_guid("123e4567-e89b-12d3-a456-426614174000")


def test_is_guid_false() -> None:
    assert not is_guid("WNT7B")


def test_create_source_url() -> None:
    value = create_source_url("ieu-a-2")
    assert value == "https://opengwas.io/datasets/ieu-a-2"


def test_tabular_payload_columnar_and_rows_give_the_same_records() -> None:
    columnar = {
        "coloc_pair_column_names": ["variant_id", "h4", "in_coloc_group"],
        "coloc_pair_columns": {
            "in_coloc_group": [True, False],
            "variant_id": [1, 2],
            "h4": [0.9, None],
        },
    }
    rows = {
        "coloc_pair_column_names": ["variant_id", "h4", "in_coloc_group"],
        "coloc_pair_rows": [[1, 0.9, True], [2, None, False]],
    }
    expected = [
        {"variant_id": 1, "h4": 0.9, "in_coloc_group": True},
        {"variant_id": 2, "h4": None, "in_coloc_group": False},
    ]
    assert tabular_payload_to_records(columnar, "coloc_pair") == expected
    assert tabular_payload_to_records(rows, "coloc_pair") == expected


def test_tabular_payload_empty() -> None:
    assert (
        tabular_payload_to_records(
            {"associations_full_column_names": [], "associations_full_columns": {}},
            "associations_full",
        )
        == []
    )
    assert (
        tabular_payload_to_records(
            {"associations_full_column_names": [], "associations_full_rows": []},
            "associations_full",
        )
        == []
    )
    assert tabular_payload_to_records({}, "associations_full") == []
