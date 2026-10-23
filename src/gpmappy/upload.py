"""Validation and column handling for GWAS uploads."""

from __future__ import annotations

import gzip
import warnings
from collections.abc import Mapping, Sequence
from pathlib import Path

from gpmappy.exceptions import ValidationError
from gpmappy.utils import is_guid

MAX_UPLOAD_BYTES = 1024**3
MAX_GWAS_PVALUE_THRESHOLD = 1e-5

# API column name -> upload_gwas() argument name
GWAS_COLUMN_ARGS = {
    "SNP": "snp_col",
    "RSID": "rsid_col",
    "CHR": "chr_col",
    "BP": "bp_col",
    "EA": "ea_col",
    "OA": "oa_col",
    "P": "p_col",
    "EAF": "eaf_col",
    "BETA": "beta_col",
    "SE": "se_col",
    "OR": "or_col",
    "OR_LB": "or_lb_col",
    "OR_UB": "or_ub_col",
}
REQUIRED_COLUMN_ARGS = ("chr_col", "bp_col", "ea_col", "oa_col", "p_col")
LEGACY_COLUMN_ALIASES = {"LB": "OR_LB", "UB": "OR_UB"}
HEADER_DELIMITERS = ("\t", ",", ";", "|")


def validate_upload_arguments(  # noqa: PLR0913
    *,
    file: str,
    name: str,
    p_value_threshold: float,
    email: str | None,
    variable_type: str,
    ancestry: str,
    sample_size: int | float | None,
    reference_build: str,
    compare_with_upload_guids: Sequence[str] | None,
) -> None:
    path = Path(file)
    if not path.is_file() or path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValidationError("file must be a valid file and less than 1GB")
    if not name:
        raise ValidationError("name is required")
    if not email:
        raise ValidationError("email is required")
    if variable_type not in {"continuous", "categorical"}:
        raise ValidationError('variable_type must be "continuous" or "categorical"')
    if ancestry not in {"EUR"}:
        raise ValidationError("ancestry must be EUR")
    if reference_build not in {"GRCh37", "GRCh38"}:
        raise ValidationError("reference_build must be GRCh37 or GRCh38")
    if p_value_threshold <= 0 or p_value_threshold > MAX_GWAS_PVALUE_THRESHOLD:
        raise ValidationError("p_value_threshold must be in (0, 1e-5]")
    if sample_size is None or float(sample_size) <= 0:
        raise ValidationError("sample_size must be a positive number")
    if compare_with_upload_guids is not None and not all(
        is_guid(guid) for guid in compare_with_upload_guids
    ):
        raise ValidationError("compare_with_upload_guids must be a vector of GUIDs")


def build_gwas_column_names(
    column_names: Mapping[str, str] | None,
    col_args: Mapping[str, str | None],
) -> dict[str, str]:
    """Build and validate the column names sent to the API, keyed by API name (CHR, BP, ...).

    ``col_args`` holds the ``*_col`` arguments in signature order. ``column_names``
    is the deprecated mapping (e.g. ``{"CHR": "chr"}``) and cannot be mixed with them.
    """
    provided = {arg: value for arg, value in col_args.items() if value is not None}

    if column_names:
        if provided:
            raise ValidationError(
                "Specify columns with either the *_col arguments or column_names, not both"
            )
        warnings.warn(
            'column_names is deprecated, please use the *_col arguments instead (e.g. chr_col = "chr")',
            FutureWarning,
            stacklevel=3,
        )
        keys = [
            LEGACY_COLUMN_ALIASES.get(str(key).upper(), str(key).upper()) for key in column_names
        ]
        unknown = [key for key in keys if key not in GWAS_COLUMN_ARGS]
        if unknown:
            raise ValidationError(
                f"Unknown column_names: {', '.join(unknown)}. "
                f"Accepted names are: {', '.join(GWAS_COLUMN_ARGS)}"
            )
        provided = {GWAS_COLUMN_ARGS[key]: value for key, value in zip(keys, column_names.values())}

    invalid = [arg for arg, value in provided.items() if not isinstance(value, str) or not value]
    if invalid:
        raise ValidationError(f"{', '.join(invalid)} must be a single column name")

    missing = [arg for arg in REQUIRED_COLUMN_ARGS if arg not in provided]
    if missing:
        raise ValidationError(f"Missing required column arguments: {', '.join(missing)}")
    has_beta = all(arg in provided for arg in ("beta_col", "se_col"))
    has_or = all(arg in provided for arg in ("or_col", "or_lb_col", "or_ub_col"))
    if not has_beta and not has_or:
        raise ValidationError(
            "Either beta_col and se_col, or or_col, or_lb_col and or_ub_col must be specified"
        )

    api_names = {arg: api_name for api_name, arg in GWAS_COLUMN_ARGS.items()}
    return {api_names[arg]: str(value) for arg, value in provided.items()}


def check_gwas_file_columns(file: str, column_names: Mapping[str, str]) -> None:
    """Raise if any requested column is missing from the file header.

    The check is skipped when the header cannot be read or splits into one column.
    """
    header = _read_header(file)
    if len(header) <= 1:
        return
    missing = [column for column in dict.fromkeys(column_names.values()) if column not in header]
    if missing:
        raise ValidationError(f"Columns not found in file: {', '.join(missing)}")


def _read_header(file: str) -> list[str]:
    try:
        if str(file).endswith(".gz"):
            with gzip.open(file, "rt", newline="") as handle:
                line = handle.readline()
        else:
            with open(file, newline="") as handle:
                line = handle.readline()
    except (OSError, UnicodeDecodeError):
        return []

    line = line.rstrip("\r\n")
    delimiter = max(HEADER_DELIMITERS, key=line.count)
    fields = line.split(delimiter) if delimiter in line else line.split()
    return [field.strip().strip('"') for field in fields]
