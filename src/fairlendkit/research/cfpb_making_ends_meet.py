"""Aggregate-only guards for the external CFPB Making Ends Meet PUFs."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

DISPOSITION = "external_only"
USAGE = "quality_only"
ADMISSION_STATUS = "evidence_incomplete"
ADOPTED = False
TERMS_STATUS = "archived_unverified"
IDENTIFIER_COLUMN = "ID"
REDISTRIBUTION = "prohibited"
WEIGHT_STAT_FIELDS = ("missing", "non_finite", "zero", "negative", "minimum", "maximum")
MISSINGNESS_FIELDS = (
    "blank_cells", "columns_with_blanks", "complete_columns", "imputation_indicator_columns",
)
SAMPLES = {
    1: {
        "rows": 2986,
        "columns": 612,
        "archive_sha256": "664fb88960969ddecb7945a5b605ef1504df556f22f0a82f22d8ae86271f9009",
        "csv_sha256": "607770805ee67829ddf2a5782d6542d5ca8c380b4e0e1f9c53cd23047793d5e8",
        "weights": ("w1weight", "w2weight", "w3weight", "w321weight"),
        "weight_statistics": {
            "w1weight": (0, 0, 0, 0, 32.411503, 14054.265),
            "w2weight": (1118, 0, 0, 0, 48.252583, 26830.291),
            "w3weight": (1240, 0, 0, 0, 61.827072, 58646.918),
            "w321weight": (1538, 0, 0, 0, 72.300713, 72310.953),
        },
        "missingness": (690256, 512, 100, 0),
        "special_response_counts": {},
    },
    3: {
        "rows": 2125,
        "columns": 404,
        "archive_sha256": "ee0e119aa358978e20777d618ef2ae7cb0c0b0eee3cdbd56e6b926a39b7ddc51",
        "csv_sha256": "97887ff1bce9fbee98f67e71accd8e703e7e42f892601af157a255912d9459a1",
        "weights": ("weight", "w2weight", "w2comb_weight"),
        "weight_statistics": {
            "weight": (0, 0, 0, 0, 248.43109, 93385.68),
            "w2weight": (1063, 0, 0, 0, 538.45044, 25063.686),
            "w2comb_weight": (1063, 0, 0, 0, 186.32747, 8673.1348),
        },
        "missingness": (420047, 358, 46, 0),
        "special_response_counts": {"q98:3:don't_know": 25},
    },
    4: {
        "rows": 2136,
        "columns": 396,
        "archive_sha256": "2e76cf9eb24d3f822afedcb3e7b0d32d7c5ad3db30285bf477dbaa981dd639ab",
        "csv_sha256": "fe7763cb508dedad4c6086018696b5f58320a84be2ed20c7a00d1a8e29f5e51e",
        "weights": ("weight", "comb_weight", "w2weight", "w2comb_weight"),
        "weight_statistics": {
            "weight": (0, 0, 0, 0, 402.1825, 15738.883),
            "comb_weight": (0, 0, 0, 0, 402.1825, 15738.883),
            "w2weight": (763, 0, 0, 0, 823.07983, 18949.76),
            "w2comb_weight": (763, 0, 0, 0, 362.354, 8342.4727),
        },
        "missingness": (355351, 371, 25, 0),
        "special_response_counts": {"q81:3:don't_know": 15},
    },
    5: {
        "rows": 3113,
        "columns": 491,
        "archive_sha256": "09e88d34e88b847ffe613c27c0088b587f4317c28547df128ee847d82364eb7f",
        "csv_sha256": "58633701a1cb3a4d85c78a0d3bcdb240b9abdc6aed996d95a64cf700401be04a",
        "weights": (
            "weight", "comb_weight", "w2weight_paper", "w2weight_online",
            "w2comb_weight_online", "w2comb_weight_paper",
        ),
        "weight_statistics": {
            "weight": (0, 0, 0, 0, 529.48383, 7089.5503),
            "comb_weight": (0, 0, 0, 0, 1999.803, 26776.461),
            "w2weight_paper": (1161, 0, 0, 0, 836.19739, 11771.118),
            "w2weight_online": (1339, 0, 0, 0, 875.29626, 14371.805),
            "w2comb_weight_online": (1339, 0, 0, 0, 875.29626, 14371.805),
            "w2comb_weight_paper": (1161, 0, 0, 0, 836.19739, 11771.118),
        },
        "missingness": (713085, 466, 25, 0),
        "special_response_counts": {
            "q75:3:don't_know": 22,
            "q104:5:don't_know": 1668,
            "q105:5:don't_know": 1549,
            "q106:4:don't_know": 959,
        },
    },
    6: {
        "rows": 2630,
        "columns": 346,
        "archive_sha256": "cfa280a45ed256db42be0cc4df87b0db182ebf11f19983aaeab981ed1543deca",
        "csv_sha256": "1d9288d40af00f739ad88fa5997f1f84a0116ea9a49c4399f029bba5d3287900",
        "weights": ("weight_paper", "weight_online", "comb_weight_paper", "comb_weight_online"),
        "weight_statistics": {
            "weight_paper": (0, 0, 0, 0, 465.05878, 9643.7891),
            "weight_online": (306, 0, 0, 0, 512.1629, 14670.264),
            "comb_weight_paper": (0, 0, 0, 0, 793.9455, 16463.818),
            "comb_weight_online": (306, 0, 0, 0, 823.74152, 23595.041),
        },
        "missingness": (361431, 313, 33, 0),
        "special_response_counts": {
            "q79:3:don't_know": 22,
            "q95:5:don't_know": 14,
        },
    },
}


class MakingEndsMeetIntegrityError(ValueError):
    """Raised when aggregate evidence differs from a reviewed CFPB package."""


def summarize_weight_values(values: Sequence[str]) -> tuple[int, int, int, int, float, float]:
    """Return aggregate-only weight evidence without retaining respondent values."""
    missing = non_finite = zero = negative = 0
    finite: list[float] = []
    for value in values:
        if value == "":
            missing += 1
            continue
        try:
            number = float(value)
        except ValueError:
            non_finite += 1
            continue
        if not math.isfinite(number):
            non_finite += 1
            continue
        zero += number == 0
        negative += number < 0
        finite.append(number)
    if not finite:
        raise MakingEndsMeetIntegrityError("weight has no finite observations")
    return missing, non_finite, zero, negative, min(finite), max(finite)


def summarize_missingness(
    rows: Sequence[Mapping[str, str]], columns: Sequence[str]
) -> tuple[int, int, int, int]:
    """Summarize blank cells separately from codebook-labelled response values."""
    blank_by_column = {column: 0 for column in columns}
    for row in rows:
        for column in columns:
            blank_by_column[column] += row[column] == ""
    incomplete = sum(count > 0 for count in blank_by_column.values())
    imputation_columns = sum("imput" in column.lower() for column in columns)
    return sum(blank_by_column.values()), incomplete, len(columns) - incomplete, imputation_columns


def validate_sample_summary(
    sample: int,
    *,
    rows: int,
    columns: int,
    archive_sha256: str,
    csv_sha256: str,
    identifier_nulls: int,
    identifier_unique: int,
    weight_columns: Sequence[str],
    weight_statistics: Mapping[str, Sequence[int | float]],
    missingness: Sequence[int],
    special_response_counts: Mapping[str, int],
) -> None:
    """Fail closed on package, shape, identifier, or weight drift."""
    expected = SAMPLES.get(sample)
    if expected is None:
        raise MakingEndsMeetIntegrityError("sample is not part of the reviewed public release")
    if (rows, columns) != (expected["rows"], expected["columns"]):
        raise MakingEndsMeetIntegrityError("sample shape changed")
    if archive_sha256 != expected["archive_sha256"] or csv_sha256 != expected["csv_sha256"]:
        raise MakingEndsMeetIntegrityError("sample package or CSV SHA-256 changed")
    if identifier_nulls != 0 or identifier_unique != rows:
        raise MakingEndsMeetIntegrityError("random respondent ID is missing or non-unique")
    if tuple(weight_columns) != expected["weights"]:
        raise MakingEndsMeetIntegrityError("sample weight columns changed")
    normalized_weights = {name: tuple(values) for name, values in weight_statistics.items()}
    if normalized_weights != expected["weight_statistics"]:
        raise MakingEndsMeetIntegrityError("sample weight statistics changed")
    if tuple(missingness) != expected["missingness"]:
        raise MakingEndsMeetIntegrityError("sample missingness or imputation evidence changed")
    if dict(special_response_counts) != expected["special_response_counts"]:
        raise MakingEndsMeetIntegrityError("sample codebook special-response counts changed")


def analysis_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Remove the linkable random ID from any bounded aggregate analysis."""
    if IDENTIFIER_COLUMN not in columns:
        raise MakingEndsMeetIntegrityError("random respondent ID is required for isolation checks")
    return tuple(column for column in columns if column != IDENTIFIER_COLUMN)
