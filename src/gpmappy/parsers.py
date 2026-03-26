"""Response parsing utilities."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path


def read_tsv_gz_records(path: str | Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader]
