"""Aggregate-only guards for the external CFPB Making Ends Meet PUFs."""

from __future__ import annotations

from typing import Mapping, Sequence

DISPOSITION = "external_only"
USAGE = "quality_only"
IDENTIFIER_COLUMN = "ID"
SAMPLES = {
    1: {
        "rows": 2986,
        "columns": 612,
        "archive_sha256": "664fb88960969ddecb7945a5b605ef1504df556f22f0a82f22d8ae86271f9009",
        "csv_sha256": "607770805ee67829ddf2a5782d6542d5ca8c380b4e0e1f9c53cd23047793d5e8",
        "weights": ("w1weight", "w2weight", "w3weight", "w321weight"),
    },
    3: {
        "rows": 2125,
        "columns": 404,
        "archive_sha256": "ee0e119aa358978e20777d618ef2ae7cb0c0b0eee3cdbd56e6b926a39b7ddc51",
        "csv_sha256": "97887ff1bce9fbee98f67e71accd8e703e7e42f892601af157a255912d9459a1",
        "weights": ("weight", "w2weight", "w2comb_weight"),
    },
    4: {
        "rows": 2136,
        "columns": 396,
        "archive_sha256": "2e76cf9eb24d3f822afedcb3e7b0d32d7c5ad3db30285bf477dbaa981dd639ab",
        "csv_sha256": "fe7763cb508dedad4c6086018696b5f58320a84be2ed20c7a00d1a8e29f5e51e",
        "weights": ("weight", "comb_weight", "w2weight", "w2comb_weight"),
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
    },
    6: {
        "rows": 2630,
        "columns": 346,
        "archive_sha256": "cfa280a45ed256db42be0cc4df87b0db182ebf11f19983aaeab981ed1543deca",
        "csv_sha256": "1d9288d40af00f739ad88fa5997f1f84a0116ea9a49c4399f029bba5d3287900",
        "weights": ("weight_paper", "weight_online", "comb_weight_paper", "comb_weight_online"),
    },
}


class MakingEndsMeetIntegrityError(ValueError):
    """Raised when aggregate evidence differs from a reviewed CFPB package."""


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


def analysis_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Remove the linkable random ID from any bounded aggregate analysis."""
    if IDENTIFIER_COLUMN not in columns:
        raise MakingEndsMeetIntegrityError("random respondent ID is required for isolation checks")
    return tuple(column for column in columns if column != IDENTIFIER_COLUMN)
