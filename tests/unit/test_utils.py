from gpmappy.utils import create_source_url, is_guid


def test_is_guid_true() -> None:
    assert is_guid("123e4567-e89b-12d3-a456-426614174000")


def test_is_guid_false() -> None:
    assert not is_guid("WNT7B")


def test_create_source_url() -> None:
    value = create_source_url("ieu-a-2")
    assert value == "https://opengwas.io/datasets/ieu-a-2"
