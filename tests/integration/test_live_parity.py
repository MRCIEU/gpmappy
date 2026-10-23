"""End-to-end parity: gpmapr and gpmappy against the same live GPMap API.

Runs every call in live_parity_scenarios.json through gpmapr (sourced from a checkout by
scripts/parity/run_gpmapr_live.R) and gpmappy, and compares the normalized results. The
API returns coloc groups and rare results in a different order on each call, so nested
tables are compared ignoring row order.

Needs ``--run-live`` (or GPMAPPY_RUN_LIVE=1), GPMAPPY_PARITY_URL (e.g.
http://localhost:8000), Rscript, and a gpmapr checkout (../gpmapr or $GPMAPR_PATH).
"""

from __future__ import annotations

import inspect
import json
import os
import shutil
import subprocess
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import gpmappy
from gpmappy import GpmapClient, get_default_client, set_default_client
from gpmappy.config import GpmapConfig
from gpmappy.exceptions import GpmappyError

REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "tests" / "contract"))
from _parity import compare, normalize, sort_tables  # noqa: E402

SCENARIOS = json.loads((Path(__file__).parent / "live_parity_scenarios.json").read_text())
API_URL = os.environ.get("GPMAPPY_PARITY_URL")
GPMAPR_PATH = Path(os.environ.get("GPMAPR_PATH", REPO_ROOT.parent / "gpmapr"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live,
    pytest.mark.skipif(
        not API_URL or shutil.which("Rscript") is None or not (GPMAPR_PATH / "NAMESPACE").is_file(),
        reason="needs GPMAPPY_PARITY_URL, Rscript and a gpmapr checkout",
    ),
]


@pytest.fixture(scope="module")
def gpmapr_results(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out_dir = tmp_path_factory.mktemp("gpmapr_live")
    subprocess.run(
        [
            "Rscript",
            str(REPO_ROOT / "scripts" / "parity" / "run_gpmapr_live.R"),
            str(GPMAPR_PATH),
            str(API_URL),
            str(Path(__file__).parent / "live_parity_scenarios.json"),
            str(out_dir),
        ],
        check=True,
        capture_output=True,
        timeout=1800,
    )
    return out_dir


@pytest.fixture(scope="module", autouse=True)
def live_client() -> Iterator[None]:
    original = get_default_client()
    set_default_client(GpmapClient(GpmapConfig(base_url=str(API_URL))))
    yield
    set_default_client(original)


def _run(scenario: dict[str, Any]) -> dict[str, Any]:
    function = getattr(gpmappy, scenario["function"])
    kwargs = dict(scenario["args"])
    if "as_dataframe" in inspect.signature(function).parameters:
        kwargs["as_dataframe"] = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return {"result": normalize(function(**kwargs))}
    except GpmappyError as exc:
        return {"error": str(exc)}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_live_result_matches_gpmapr(gpmapr_results: Path, scenario: dict[str, Any]) -> None:
    expected = json.loads((gpmapr_results / f"{scenario['id']}.json").read_text())
    actual = _run(scenario)
    if "error" in expected or "error" in actual:
        assert expected.get("error") and expected["error"] in actual.get(
            "error", ""
        ), f"gpmapr error={expected.get('error')!r}, gpmappy={actual!r}"
        return
    diffs = compare(sort_tables(expected["result"]), sort_tables(actual["result"]), "result")
    assert not diffs, f"{len(diffs)} differences, e.g.:\n" + "\n".join(diffs[:15])
