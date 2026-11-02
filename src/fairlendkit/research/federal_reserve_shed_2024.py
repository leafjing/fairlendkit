"""Aggregate-only guards for the external 2024 Federal Reserve SHED PUF."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

ADMISSION_STATUS = "evidence_incomplete"
ADOPTED = False
DISPOSITION = "external_only"
USAGE = "quality_only"
REDISTRIBUTION = "prohibited"
IDENTIFIER_COLUMN = "shedid"
EXPECTED = {
    "rows": 12295,
    "columns": 751,
    "archive_sha256": "b455d02356a0c01a02d7f478c02d772515491564e905ce13db55f272f83567c1",
    "csv_sha256": "82897c55a7c3dc1c056270506714d174732215927419f7d571400612cdd30819",
    "weights": {
        "weight": (0, 0, 0, 0, 0.1788, 3.5159),
        "weight_pop": (0, 0, 0, 0, 3771.794, 74172.6995),
        "panel_weight": (8280, 0, 0, 0, 0.0943, 3.2902),
        "panel_weight_pop": (8280, 0, 0, 0, 6094.602, 212555.405),
    },
    "missingness": (2159319, 254, 497),
    "imputation_flags": (342, 4204890, 0, 4191995, 12895),
    "special_responses": {"not_asked": 20300, "dont_know": 4313, "refused": 537},
}


class Shed2024IntegrityError(ValueError):
    """Raised when aggregate evidence differs from the reviewed SHED package."""


def summarize_numeric(values: Sequence[str]) -> tuple[int, int, int, int, float, float]:
    """Return missing/non-finite/zero/negative/min/max without retaining rows."""
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
        raise Shed2024IntegrityError("numeric field has no finite observations")
    return missing, non_finite, zero, negative, min(finite), max(finite)


def validate_summary(
    *,
    rows: int,
    columns: int,
    archive_sha256: str,
    csv_sha256: str,
    identifier_nulls: int,
    identifier_unique: int,
    weights: Mapping[str, Sequence[int | float]],
    missingness: Sequence[int],
    imputation_flags: Sequence[int],
    special_responses: Mapping[str, int],
) -> None:
    """Fail closed on package, identifier, weight, or aggregate-evidence drift."""
    if (rows, columns) != (EXPECTED["rows"], EXPECTED["columns"]):
        raise Shed2024IntegrityError("SHED shape changed")
    if archive_sha256 != EXPECTED["archive_sha256"] or csv_sha256 != EXPECTED["csv_sha256"]:
        raise Shed2024IntegrityError("SHED package or CSV SHA-256 changed")
    if identifier_nulls != 0 or identifier_unique != rows:
        raise Shed2024IntegrityError("SHED identifier is missing or non-unique")
    if {name: tuple(values) for name, values in weights.items()} != EXPECTED["weights"]:
        raise Shed2024IntegrityError("SHED weight statistics changed")
    if tuple(missingness) != EXPECTED["missingness"]:
        raise Shed2024IntegrityError("SHED missingness changed")
    if tuple(imputation_flags) != EXPECTED["imputation_flags"]:
        raise Shed2024IntegrityError("SHED imputation flags changed")
    if dict(special_responses) != EXPECTED["special_responses"]:
        raise Shed2024IntegrityError("SHED special-response counts changed")


def analysis_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Remove the longitudinal identifier from bounded aggregate analysis."""
    if IDENTIFIER_COLUMN not in columns:
        raise Shed2024IntegrityError("shedid is required for isolation checks")
    return tuple(column for column in columns if column != IDENTIFIER_COLUMN)
