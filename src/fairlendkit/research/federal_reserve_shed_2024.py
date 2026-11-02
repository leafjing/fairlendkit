"""Aggregate-only guards for the external 2024 Federal Reserve SHED PUF."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence

ADMISSION_STATUS = "evidence_incomplete"
ADOPTED = False
DISPOSITION = "external_only"
USAGE = "quality_only"
REDISTRIBUTION = "prohibited"
IDENTIFIER_COLUMN = "shedid"
IDENTIFIER_COLUMNS = (IDENTIFIER_COLUMN,)
SPECIAL_RESPONSE_RULES = {
    "not_asked": {
        "UNION100": ("Not asked",),
        "ind1": ("-2",),
        "ppcm0160": ("Not asked",),
        "ppcm1301": ("Not asked",),
    },
    "dont_know": {
        "A6": ("Don’t know",),
        "CH2A": ("Don’t know",),
        "D47": ("Don’t know",),
        "E2A": ("Don’t know",),
        "K0": ("Don’t know",),
        "SL13": ("Don’t know",),
        "SL3": ("Don’t know",),
        "SL4": ("Don’t know",),
        "ppfs1482": ("Don’t know",),
    },
    "refused": {
        "CH2A": ("Refused",),
        "ND1_e": ("Refused",),
        "UNION100": ("Refused",),
        "ind1": ("-1",),
        "ppcm0160": ("Refused",),
        "ppcm1301": ("Refused",),
    },
}
EXPECTED = {
    "rows": 12295,
    "columns": 751,
    "schema_sha256": "63fd0317d14b9634f9dafd3f3a63932c2c40d41d764c220d01cad34a4cbde6e9",
    "identifier_index": 0,
    "identifier_year_counts": {
        "2013": 58,
        "2014": 47,
        "2015": 42,
        "2016": 124,
        "2017": 524,
        "2018": 579,
        "2019": 570,
        "2020": 694,
        "2021": 680,
        "2022": 1188,
        "2023": 1262,
        "2024": 6527,
    },
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
    "special_response_rules_sha256": "a19cf85d3459959ae0481eed2e7278703c0a2e6819993511c6ee1493a222efc9",
    "special_responses": {"not_asked": 20300, "dont_know": 4313, "refused": 537},
}


class Shed2024IntegrityError(ValueError):
    """Raised when aggregate evidence differs from the reviewed SHED package."""


def canonical_sha256(value: object) -> str:
    """Hash JSON-compatible evidence with one deterministic representation."""
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def schema_sha256(columns: Sequence[str]) -> str:
    """Hash the ordered, case-sensitive schema without retaining respondent rows."""
    return canonical_sha256(list(columns))


def special_response_rules_sha256(
    rules: Mapping[str, Mapping[str, Sequence[str]]],
) -> str:
    """Hash the codebook-derived column/value mapping deterministically."""
    canonical = {
        category: [[column, list(values)] for column, values in sorted(columns.items())]
        for category, columns in sorted(rules.items())
    }
    return canonical_sha256(canonical)


def summarize_special_responses(
    rows: Iterable[Mapping[str, str]],
    rules: Mapping[str, Mapping[str, Sequence[str]]] = SPECIAL_RESPONSE_RULES,
) -> dict[str, int]:
    """Count only codebook-mapped special answers; blanks remain separate."""
    counts = {category: 0 for category in rules}
    required = {column for columns in rules.values() for column in columns}
    for row in rows:
        if not required.issubset(row):
            raise Shed2024IntegrityError("special-response source column is missing")
        for category, columns in rules.items():
            counts[category] += sum(row[column] in values for column, values in columns.items())
    return counts


def summarize_identifier_years(values: Iterable[str]) -> dict[str, int]:
    """Count current and historical case IDs by their four-digit cohort prefix."""
    counts: dict[str, int] = {}
    for value in values:
        if len(value) != 9 or not value.isascii() or not value.isdigit():
            raise Shed2024IntegrityError("shedid is blank or malformed")
        year = value[:4]
        counts[year] = counts.get(year, 0) + 1
    return counts


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
    schema_sha256: str,
    archive_sha256: str,
    csv_sha256: str,
    identifier_column: str,
    identifier_index: int,
    identifier_nulls: int,
    identifier_unique: int,
    identifier_year_counts: Mapping[str, int],
    weights: Mapping[str, Sequence[int | float]],
    missingness: Sequence[int],
    imputation_flags: Sequence[int],
    special_response_rules_sha256: str,
    special_responses: Mapping[str, int],
) -> None:
    """Fail closed on package, identifier, weight, or aggregate-evidence drift."""
    if (rows, columns) != (EXPECTED["rows"], EXPECTED["columns"]):
        raise Shed2024IntegrityError("SHED shape changed")
    if schema_sha256 != EXPECTED["schema_sha256"]:
        raise Shed2024IntegrityError("SHED ordered schema changed")
    if archive_sha256 != EXPECTED["archive_sha256"] or csv_sha256 != EXPECTED["csv_sha256"]:
        raise Shed2024IntegrityError("SHED package or CSV SHA-256 changed")
    if (
        identifier_column != IDENTIFIER_COLUMN
        or identifier_index != EXPECTED["identifier_index"]
        or identifier_nulls != 0
        or identifier_unique != rows
    ):
        raise Shed2024IntegrityError("SHED identifier is missing or non-unique")
    if dict(identifier_year_counts) != EXPECTED["identifier_year_counts"]:
        raise Shed2024IntegrityError("SHED current or historical case identifiers changed")
    if {name: tuple(values) for name, values in weights.items()} != EXPECTED["weights"]:
        raise Shed2024IntegrityError("SHED weight statistics changed")
    if tuple(missingness) != EXPECTED["missingness"]:
        raise Shed2024IntegrityError("SHED missingness changed")
    if tuple(imputation_flags) != EXPECTED["imputation_flags"]:
        raise Shed2024IntegrityError("SHED imputation flags changed")
    if special_response_rules_sha256 != EXPECTED["special_response_rules_sha256"]:
        raise Shed2024IntegrityError("SHED special-response mapping changed")
    if dict(special_responses) != EXPECTED["special_responses"]:
        raise Shed2024IntegrityError("SHED special-response counts changed")


def analysis_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Remove the longitudinal identifier from bounded aggregate analysis."""
    for identifier in IDENTIFIER_COLUMNS:
        identifier_matches = [column for column in columns if column.casefold() == identifier]
        if identifier_matches != [identifier]:
            raise Shed2024IntegrityError(f"{identifier} is required for isolation checks")
    return tuple(column for column in columns if column not in IDENTIFIER_COLUMNS)
