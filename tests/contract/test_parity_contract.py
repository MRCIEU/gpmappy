"""Parity contract between gpmappy and the gpmapr R package.

gpmapr's side is recorded in tests/contract/gpmapr/ by
scripts/parity/generate_gpmapr_contract.R:

* surface.json: every function gpmapr exports, with its formals.
* golden/<id>.json: for each scenario in scenarios.json, the HTTP requests gpmapr
  made against the shared fixtures and its normalized result, error and warnings.

These tests check that gpmappy exports the same functions with the same parameters,
and that replaying each scenario produces the same requests and the same output.
When gpmapr is checked out next to this repo (or at $GPMAPR_PATH) and Rscript is
installed, the snapshot is regenerated and must match what is committed.
"""

from __future__ import annotations

import filecmp
import inspect
import math
import os
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import Any

import pytest
from _parity import (
    CONTRACT_DIR,
    GPMAPR_DIR,
    SCENARIOS,
    FixtureTransport,
    apply_divergences,
    compare,
    load_golden,
    load_surface,
    normalize,
    resolve_fixture_paths,
)

import gpmappy
from gpmappy import GpmapClient, get_default_client, set_default_client
from gpmappy.constants import API_TO_PACKAGE_VERSION
from gpmappy.exceptions import GpmappyError
from gpmappy.version import package_version

REPO_ROOT = CONTRACT_DIR.parent.parent
SURFACE = load_surface()
R_EXPORTS = {entry["name"]: entry for entry in SURFACE["exports"]}

# gpmappy exports that gpmapr does not, and why.
PYTHON_ONLY_EXPORTS = {
    "GpmapClient": "object-oriented client; the module-level functions wrap a default instance",
    "get_default_client": "access the client behind the module-level functions",
    "set_default_client": "replace the client behind the module-level functions",
    "select_api": "gpmapr keeps select_api() internal and sets the URL on load",
    "version_api": "gpmapr keeps version_api() internal and checks it on load",
    "get_all_snp_pleiotropies": "deprecated alias of get_all_variant_pleiotropies()",
}
# Parameters gpmappy adds to gpmapr's signatures.
PYTHON_ONLY_PARAMS = {"as_dataframe"}


# ---------------------------------------------------------------------------
# Exported surface
# ---------------------------------------------------------------------------
def test_gpmapr_exports_are_all_exported() -> None:
    missing = sorted(set(R_EXPORTS) - set(gpmappy.__all__))
    assert not missing, f"gpmapr exports missing from gpmappy.__all__: {missing}"


def test_python_only_exports_are_documented() -> None:
    undocumented = sorted(set(gpmappy.__all__) - set(R_EXPORTS) - set(PYTHON_ONLY_EXPORTS))
    assert not undocumented, f"Add these to PYTHON_ONLY_EXPORTS or gpmapr: {undocumented}"
    stale = sorted(
        name for name in PYTHON_ONLY_EXPORTS if name in R_EXPORTS or name not in gpmappy.__all__
    )
    assert not stale, f"Remove these from PYTHON_ONLY_EXPORTS: {stale}"


def test_supports_the_same_api_versions_as_gpmapr() -> None:
    supported = sorted(
        api for api, versions in API_TO_PACKAGE_VERSION.items() if package_version() in versions
    )
    assert supported == SURFACE["api_versions"], (
        f"gpmappy {package_version()} supports API {supported}, gpmapr {SURFACE['version']} "
        f"supports {SURFACE['api_versions']}: update API_TO_PACKAGE_VERSION"
    )


def _python_params(function: Any) -> list[inspect.Parameter]:
    return [
        param
        for param in inspect.signature(function).parameters.values()
        if param.name not in PYTHON_ONLY_PARAMS and param.name != "self"
    ]


def _defaults_match(r_default: Any, py_default: Any) -> bool:
    if r_default is None or py_default is None:
        return r_default is None and py_default is None
    if isinstance(r_default, bool) or isinstance(py_default, bool):
        return r_default is py_default
    if isinstance(r_default, (int, float)) and isinstance(py_default, (int, float)):
        return math.isclose(r_default, py_default)
    return bool(r_default == py_default)


@pytest.mark.parametrize("target", ["wrapper", "client"])
@pytest.mark.parametrize("name", sorted(R_EXPORTS))
def test_signature_matches_gpmapr(name: str, target: str) -> None:
    function = getattr(gpmappy, name) if target == "wrapper" else getattr(GpmapClient, name)
    r_params = R_EXPORTS[name]["params"]
    py_params = _python_params(function)

    assert [p.name for p in py_params] == [
        p["name"] for p in r_params
    ], f"{name}() parameters differ from gpmapr"
    for r_param, py_param in zip(r_params, py_params):
        py_required = py_param.default is inspect.Parameter.empty
        assert (
            py_required == r_param["required"]
        ), f"{name}({py_param.name}) required={py_required}, gpmapr required={r_param['required']}"
        if not py_required:
            assert _defaults_match(r_param["default"], py_param.default), (
                f"{name}({py_param.name}) default {py_param.default!r}, "
                f"gpmapr default {r_param['r_default']}"
            )


# ---------------------------------------------------------------------------
# Scenario outputs
# ---------------------------------------------------------------------------
def _call(function_name: str, args: dict[str, Any]) -> Any:
    """Call an exported function as a scenario describes, with list-of-dict tables."""
    function = getattr(gpmappy, function_name)
    kwargs = {key: _resolve(value) for key, value in args.items()}
    if "as_dataframe" in inspect.signature(function).parameters:
        kwargs["as_dataframe"] = False
    return function(**kwargs)


def _resolve(value: Any) -> Any:
    """A scenario argument: {"$call": {...}} is replaced by the result of that call."""
    if isinstance(value, dict) and "$call" in value:
        return _call(value["$call"]["function"], value["$call"]["args"])
    return resolve_fixture_paths(value)


def _run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    client = GpmapClient()
    transport = FixtureTransport(scenario.get("fixtures", "gpmapr"))
    client._transport = transport  # type: ignore[assignment]

    outcome: dict[str, Any] = {}
    original = get_default_client()
    set_default_client(client)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                outcome["result"] = normalize(_call(scenario["function"], scenario["args"]))
            except GpmappyError as exc:
                outcome["error"] = str(exc)
    finally:
        set_default_client(original)
    outcome["requests"] = transport.requests
    outcome["warnings"] = [str(warning.message) for warning in caught]
    return outcome


def _scenario_diffs(golden: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    if golden["requests"] != actual["requests"]:
        diffs.append(f"requests: gpmapr={golden['requests']} gpmappy={actual['requests']}")

    for message in golden["warnings"]:
        if not any(message in warning for warning in actual["warnings"]):
            diffs.append(
                f"warnings: gpmapr warned {message!r}, gpmappy warned {actual['warnings']}"
            )

    if "error" in golden:
        if "error" not in actual:
            diffs.append(f"error: gpmapr raised {golden['error']!r}, gpmappy returned a result")
        elif golden["error"] not in actual["error"]:
            diffs.append(f"error: gpmapr={golden['error']!r} gpmappy={actual['error']!r}")
    elif "error" in actual:
        diffs.append(f"result: gpmappy raised {actual['error']!r}")
    else:
        diffs += compare(golden.get("result"), actual["result"], "result")
    return diffs


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_matches_gpmapr(scenario: dict[str, Any]) -> None:
    golden = load_golden(scenario["id"])
    actual = _run_scenario(scenario)
    unexpected, stale = apply_divergences(
        _scenario_diffs(golden, actual), scenario.get("divergences", [])
    )
    assert not unexpected, "gpmappy differs from gpmapr:\n" + "\n".join(unexpected)
    assert not stale, f"Declared divergences no longer occur, remove them: {stale}"


def test_every_golden_has_a_scenario() -> None:
    goldens = {path.stem for path in (GPMAPR_DIR / "golden").glob("*.json")}
    assert goldens == {scenario["id"] for scenario in SCENARIOS}


# ---------------------------------------------------------------------------
# Snapshot freshness
# ---------------------------------------------------------------------------
def _gpmapr_checkout() -> Path | None:
    candidate = Path(os.environ.get("GPMAPR_PATH", REPO_ROOT.parent / "gpmapr"))
    return candidate if (candidate / "NAMESPACE").is_file() else None


@pytest.mark.skipif(
    _gpmapr_checkout() is None or shutil.which("Rscript") is None,
    reason="needs a gpmapr checkout (../gpmapr or $GPMAPR_PATH) and Rscript",
)
def test_gpmapr_snapshot_is_current(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "parity" / "generate_gpmapr_contract.R"
    subprocess.run(
        ["Rscript", str(script), str(_gpmapr_checkout()), str(tmp_path)],
        check=True,
        capture_output=True,
        timeout=300,
    )
    changed = []
    for subdir in ("", "golden", "fixtures"):
        comparison = filecmp.dircmp(GPMAPR_DIR / subdir, tmp_path / subdir)
        differing = comparison.diff_files + comparison.left_only + comparison.right_only
        changed += [
            str(Path(subdir) / name) for name in differing if name not in ("golden", "fixtures")
        ]
    assert not changed, (
        f"gpmapr has changed since the contract was recorded ({changed}). Run "
        "`Rscript scripts/parity/generate_gpmapr_contract.R`, review the diff and port the changes."
    )
