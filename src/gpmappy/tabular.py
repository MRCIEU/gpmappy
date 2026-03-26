"""Optional dataframe helpers."""

from __future__ import annotations

from typing import Any

from gpmappy.exceptions import OptionalDependencyError

try:  # pragma: no cover - exercised indirectly in environments without pandas
    import pandas as _pd
except Exception:  # pragma: no cover - import failures vary by platform
    _pd = None


TableLike = Any


def pandas_available() -> bool:
    return _pd is not None


def to_dataframe(records: list[dict[str, Any]]) -> Any:
    if _pd is None:
        raise OptionalDependencyError(
            "Pandas is required for dataframe output. Install with `pip install 'gpmappy[dataframe]'`."
        )
    return _pd.DataFrame(records)


def records_to_table(
    records: list[dict[str, Any]] | None,
    as_dataframe: bool | None = None,
) -> TableLike:
    rowset = records or []
    if as_dataframe is False:
        return rowset
    if as_dataframe is True:
        return to_dataframe(rowset)
    if pandas_available():
        return to_dataframe(rowset)
    return rowset


def maybe_table(value: Any, as_dataframe: bool | None = None) -> Any:
    if isinstance(value, list) and (not value or isinstance(value[0], dict)):
        return records_to_table(value, as_dataframe=as_dataframe)
    return value
