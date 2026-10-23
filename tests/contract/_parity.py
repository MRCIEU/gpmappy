"""Helpers for replaying gpmapr parity scenarios against gpmappy.

The normalization here mirrors ``normalize()`` in scripts/parity/normalize.R so R
and Python results can be compared structurally: objects, tables (records) and
lists, with missing values dropped.

Scenarios are served from one of two fixture sets, as by the R generator:
"gpmapr" (gpmapr's recorded responses, vendored in gpmapr/fixtures/) and "edge"
(gpmappy's hand-built edge cases in fixtures/).
"""

from __future__ import annotations

import fnmatch
import json
import math
from pathlib import Path
from typing import Any

import httpx

from gpmappy.transport import api_error

CONTRACT_DIR = Path(__file__).parent
FIXTURES_DIR = CONTRACT_DIR / "fixtures"
GPMAPR_DIR = CONTRACT_DIR / "gpmapr"
SCENARIOS: list[dict[str, Any]] = json.loads((CONTRACT_DIR / "scenarios.json").read_text())[
    "scenarios"
]
GPMAPR_FIXTURES_DIR = GPMAPR_DIR / "fixtures"


def load_golden(scenario_id: str) -> dict[str, Any]:
    return json.loads((GPMAPR_DIR / "golden" / f"{scenario_id}.json").read_text())


def load_surface() -> dict[str, Any]:
    return json.loads((GPMAPR_DIR / "surface.json").read_text())


def resolve_fixture_paths(value: Any) -> Any:
    return value.replace("{fixtures}", str(FIXTURES_DIR)) if isinstance(value, str) else value


# ---------------------------------------------------------------------------
# Fixture-backed transport
# ---------------------------------------------------------------------------
def _normalize_query_value(value: str) -> str:
    if value.lower() in {"true", "false"}:
        return value.lower()
    try:
        number = float(value)
    except ValueError:
        return value
    return f"{number:.15g}" if math.isfinite(number) else value


def _normalize_query(params: Any) -> dict[str, Any]:
    if params is None:
        return {}
    grouped: dict[str, list[str]] = {}
    for key, value in httpx.QueryParams(params).multi_items():
        grouped.setdefault(key, []).append(_normalize_query_value(value))
    return {
        key: values[0] if len(values) == 1 else values for key, values in sorted(grouped.items())
    }


def _route_query(query: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value[0] if isinstance(value, list) and len(value) == 1 else value
        for key, value in sorted(query.items())
    }


def _load_routes() -> dict[str, list[dict[str, Any]]]:
    edge = [
        {
            "method": route["method"],
            "path": route["path"],
            "query": _route_query(route.get("query") or {}),
            "status": int(route.get("status", 200)),
            "file": FIXTURES_DIR / "responses" / route["response"],
        }
        for route in json.loads((FIXTURES_DIR / "routes.json").read_text())
    ]
    recorded = []
    for url, file in json.loads((GPMAPR_FIXTURES_DIR / "index.json").read_text()).items():
        path, _, query = url.partition("?")
        recorded.append(
            {
                "method": "GET",
                "path": path,
                "query": _normalize_query(httpx.QueryParams(query)),
                "status": 200,
                "file": GPMAPR_FIXTURES_DIR / file,
            }
        )
    return {"edge": edge, "gpmapr": recorded}


ROUTES = _load_routes()


class FixtureTransport:
    """Stands in for HttpTransport, serving a fixture set and recording requests."""

    def __init__(self, fixture_set: str = "gpmapr") -> None:
        self.routes = ROUTES[fixture_set]
        self.requests: list[dict[str, Any]] = []

    def close(self) -> None:
        pass

    def ensure_api_compatible(self) -> bool:
        # The version check is unit-tested; every request here is a fixture.
        return True

    def request_json(  # noqa: PLR0913
        self,
        method: str,
        path: str,
        *,
        params: Any = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "method": method,
            "path": path,
            "query": _normalize_query(params),
        }
        if json_body is not None:
            request["body"] = json_body
        if files is not None:
            request["body"] = {
                "file": Path(files["file"][0]).name,
                "request": json.loads(files["request"][1]),
            }
        self.requests.append(request)

        for route in self.routes:
            if (
                route["method"] == method
                and route["path"] == path
                and route["query"] == request["query"]
            ):
                text = route["file"].read_text()
                if route["status"] >= httpx.codes.BAD_REQUEST:
                    raise api_error(route["status"], text)
                payload: dict[str, Any] = json.loads(text)
                return payload
        raise AssertionError(f"No fixture route for {method} {path} {request['query']}")

    def request_bytes(self, method: str, path: str, **_: Any) -> bytes:
        raise AssertionError(f"Binary endpoints are not part of the contract: {method} {path}")

    def download_to_path(self, url: str, destination: str | Path) -> Path:
        raise AssertionError(f"Downloads are not part of the contract: {url}")


# ---------------------------------------------------------------------------
# Normalization (mirror of the R generator)
# ---------------------------------------------------------------------------
def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for row in rows for key in row})
    return {"kind": "table", "columns": columns, "rows": rows}


def _fields(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: normalize(value) for key, value in record.items()}
    return {key: value for key, value in normalized.items() if not _is_missing(value)}


def normalize(value: Any) -> Any:  # noqa: PLR0911
    if hasattr(value, "to_dict") and hasattr(value, "columns"):
        value = value.to_dict(orient="records")
    if _is_missing(value):
        return None
    if isinstance(value, dict):
        fields = _fields(value)
        return {"kind": "object", "fields": fields} if fields else None
    if isinstance(value, (list, tuple)):
        if not value:
            return {"kind": "list", "items": []}
        if all(isinstance(item, dict) for item in value):
            return _table([_fields(item) for item in value])
        if len(value) == 1 and not isinstance(value[0], (dict, list, tuple)):
            return normalize(value[0])
        return {"kind": "list", "items": [normalize(item) for item in value]}
    return value


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def _number(value: Any) -> float | None:
    if isinstance(value, (bool, int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def values_equal(expected: Any, actual: Any) -> bool:
    """Scalar equality that tolerates R's representations.

    R coerces mixed columns to character ("5020") and booleans in numeric
    matrices to 0/1, so those compare equal to Python's 5020 and False.
    """
    if isinstance(expected, str) and isinstance(actual, str):
        return expected == actual
    if isinstance(expected, bool) and isinstance(actual, bool):
        return expected is actual
    expected_number, actual_number = _number(expected), _number(actual)
    if expected_number is not None and actual_number is not None:
        return math.isclose(expected_number, actual_number, rel_tol=1e-9, abs_tol=1e-12)
    return bool(expected == actual)


def compare(expected: Any, actual: Any, path: str) -> list[str]:
    """Return human-readable differences, each prefixed with its result path."""
    if isinstance(expected, dict) and "kind" in expected:
        if not isinstance(actual, dict) or actual.get("kind") != expected["kind"]:
            return [
                f"{path}: gpmapr returned a {expected['kind']}, gpmappy returned {_describe(actual)}"
            ]
        if expected["kind"] == "object":
            return _compare_fields(expected["fields"], actual["fields"], path)
        if expected["kind"] == "table":
            return _compare_table(expected, actual, path)
        return _compare_items(expected["items"], actual["items"], path)
    if not values_equal(expected, actual):
        return [f"{path}: gpmapr={expected!r} gpmappy={actual!r}"]
    return []


def _describe(value: Any) -> str:
    if isinstance(value, dict) and "kind" in value:
        return f"a {value['kind']}"
    return repr(value)


def _compare_fields(expected: dict[str, Any], actual: dict[str, Any], path: str) -> list[str]:
    diffs = [f"{path}/{key}: missing from gpmappy" for key in expected if key not in actual]
    diffs += [f"{path}/{key}: only in gpmappy" for key in actual if key not in expected]
    for key, expected_value in expected.items():
        if key in actual:
            diffs += compare(expected_value, actual[key], f"{path}/{key}")
    return diffs


def _compare_table(expected: dict[str, Any], actual: dict[str, Any], path: str) -> list[str]:
    diffs: list[str] = []
    missing = sorted(set(expected["columns"]) - set(actual["columns"]))
    extra = sorted(set(actual["columns"]) - set(expected["columns"]))
    if missing or extra:
        diffs.append(f"{path}/columns: missing from gpmappy={missing} only in gpmappy={extra}")
    if len(expected["rows"]) != len(actual["rows"]):
        diffs.append(
            f"{path}/rows: gpmapr has {len(expected['rows'])}, gpmappy has {len(actual['rows'])}"
        )
        return diffs
    for index, (expected_row, actual_row) in enumerate(zip(expected["rows"], actual["rows"])):
        for key in sorted(set(expected_row) | set(actual_row)):
            row_path = f"{path}/rows/{index}/{key}"
            if key not in actual_row:
                diffs.append(f"{row_path}: missing from gpmappy (gpmapr={expected_row[key]!r})")
            elif key not in expected_row:
                diffs.append(f"{row_path}: only in gpmappy (gpmappy={actual_row[key]!r})")
            else:
                diffs += compare(expected_row[key], actual_row[key], row_path)
    return diffs


def _compare_items(expected: list[Any], actual: list[Any], path: str) -> list[str]:
    if len(expected) != len(actual):
        return [f"{path}: gpmapr has {len(expected)} items, gpmappy has {len(actual)}"]
    diffs: list[str] = []
    for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
        diffs += compare(expected_item, actual_item, f"{path}/{index}")
    return diffs


def apply_divergences(
    diffs: list[str], divergences: list[dict[str, str]]
) -> tuple[list[str], list[str]]:
    """Split differences into unexpected ones and declared divergences that never matched."""
    patterns = [divergence["path"] for divergence in divergences]
    used: set[str] = set()
    unexpected: list[str] = []
    for diff in diffs:
        diff_path = diff.split(":", 1)[0]
        matched = [pattern for pattern in patterns if fnmatch.fnmatchcase(diff_path, pattern)]
        used.update(matched)
        if not matched:
            unexpected.append(diff)
    stale = [pattern for pattern in patterns if pattern not in used]
    return unexpected, stale


def sort_tables(node: Any, top_level: bool = True) -> Any:
    """Sort the rows of nested tables by their id columns, for comparing results that the
    API returned in a different row order (it does not order coloc groups or rare results).
    The top-level table keeps its order, as search results are ordered on purpose."""
    if isinstance(node, dict) and node.get("kind") == "table":
        if not top_level:
            node["rows"] = sorted(node["rows"], key=_row_key)
        for row in node["rows"]:
            for value in row.values():
                sort_tables(value, top_level=False)
    elif isinstance(node, dict) and node.get("kind") == "object":
        for value in node["fields"].values():
            sort_tables(value, top_level=False)
    elif isinstance(node, dict) and node.get("kind") == "list":
        for value in node["items"]:
            sort_tables(value, top_level=False)
    return node


_ROW_KEY_COLUMNS = (
    "coloc_group_id",
    "rare_result_group_id",
    "study_extraction_id",
    "id",
    "study_id",
    "variant_id",
    "lead_variant_id",
    "proxy_variant_id",
    "study_extraction_a_id",
    "study_extraction_b_id",
    "trait_id",
    "gene_id",
    "name",
)


def _row_key(row: dict[str, Any]) -> list[tuple[int, float, str]]:
    key = []
    for column in _ROW_KEY_COLUMNS:
        value = row.get(column)
        number = _number(value)
        key.append((0, number, "") if number is not None else (1, 0.0, str(value)))
    return key
