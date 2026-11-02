"""Aggregate-only integrity guards for Census HTOPS/HPS July 2026 PUF."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Mapping, Sequence

ADMISSION_STATUS = "evidence_incomplete"
ADOPTED = False
DISPOSITION = "external_only"
USAGE = "quality_only"
REDISTRIBUTION = "prohibited"
VARIANCE_OUTPUTS_ENABLED = False
IDENTIFIER_COLUMNS = ("SCRAMID",)

EXPECTED = {
    "rows": 12755,
    "main_columns": 255,
    "replicate_columns": 163,
    "archive_sha256": "43980716428de1b6e2a215973f31b0f0a0af4317107a97ef889dbf569d207a31",
    "main_sha256": "cfc4fc46d15be4b61c0ee924e9b881b3fb742cd668270b3bd532efe5b5a6c380",
    "replicate_sha256": "10b15223c98ee185a3025290e64819841885571ad46099c399fde6e3f48eebf6",
    "dictionary_sha256": "f91b0509a92e00218c8c59aa61237b5b494641860af5e72fc9e30143d9590585",
    "questionnaire_sha256": "ab59743a68470c64aba42dfa8b72ab1ffce9eba8b34a69b0d5bbe53232b6896c",
    "source_accuracy_sha256": "5b17eb1e2b01fe59eb434366a257da979be01c651be14b23f55d83747c644360",
    "quality_measures_sha256": "da5533fef6ca2e9b73457dc8faaf589ef96217d0f9e9d94f08ff2821a77a50bb",
    "user_note_sha256": "186816441c17c109e35b8916c7bea31a0d22336bec98256af6f8b4408ce2d0c8",
    "main_schema_sha256": "a0c1a98b9695c414fe2d5f415e0b7fc8c92e2cc0af739d09eef9f452cdb62c3d",
    "replicate_schema_sha256": "4e7594ebcd61d5b505ba01fabccca8d121593df0c5d37b9d01383e7a2dc49e0d",
    "special_rules_sha256": "0a9c58ae2434eef53ce3e7828b554d7b65f632afbfd299166681560b08c09c03",
    "base_weights": {
        "PWEIGHT": (0, 0, 0, 0, 633.0710898644122, 3941958.426037522),
        "HWEIGHT": (0, 0, 0, 0, 638.1644723523074, 1058697.3650488455),
    },
    "replicate_weights": {
        "PWEIGHT": (80, 0, 0, 0, 0, 167.2803393650417, 6225349.31742791,
                    "1a2bcb4f1689dc858bb0fe4d23f0a43773b23a8dd6cb92a039ed3d226b2b0ff8"),
        "HWEIGHT": (80, 0, 0, 0, 0, 169.82246136495218, 1711612.8305694133,
                    "0eec8ab8d9a9870a0f9042411dc7b404642f9dbe00a88a2a3ed6b35365607a06"),
    },
    "variance_factor": (4, 80),
    "imputation": {
        "A_THHLD_NUMPER": (42, 12713), "A_THHLD_NUMKID": (91, 12664),
        "A_TAGE": (962, 11793), "A_TBIRTH_YEAR": (379, 12376),
        "A_ESEX": (125, 12630), "A_RRACE": (338, 12417),
        "A_EHISPANIC": (228, 12527), "A_REDUC": (83, 12672),
    },
    "special_counts": {"not_in_universe": 1264241, "did_not_answer": 97065},
}


class Htops2607IntegrityError(ValueError):
    """Raised when reviewed HTOPS/HPS evidence drifts."""


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def summarize_numeric(values: Sequence[str]) -> tuple[int, int, int, int, float, float]:
    missing = non_finite = zero = negative = 0
    finite: list[float] = []
    for value in values:
        if value == "": missing += 1; continue
        try: number = float(value)
        except ValueError: non_finite += 1; continue
        if not math.isfinite(number): non_finite += 1; continue
        zero += number == 0; negative += number < 0; finite.append(number)
    if not finite: raise Htops2607IntegrityError("numeric field has no finite values")
    return missing, non_finite, zero, negative, min(finite), max(finite)


def analysis_columns(columns: Sequence[str]) -> tuple[str, ...]:
    matches = [column for column in columns if column.casefold() == "scramid"]
    if matches != ["SCRAMID"]:
        raise Htops2607IntegrityError("SCRAMID is required exactly once for isolation")
    return tuple(column for column in columns if column not in IDENTIFIER_COLUMNS)


def validate_replicate_columns(columns: Sequence[str], prefix: str) -> None:
    """Require full weight 0 followed by exactly replicate weights 1 through 80."""
    expected = (prefix + "0",) + tuple(prefix + str(index) for index in range(1, 81))
    if tuple(columns) != expected:
        raise Htops2607IntegrityError(f"HTOPS {prefix} replicate sequence changed")


def validate_full_sample_weight_rows(
    main_values: Sequence[str], weight_zero_values: Sequence[str], name: str,
) -> None:
    """Require the replicate file's weight 0 to equal the main weight row by row."""
    if len(main_values) != EXPECTED["rows"] or len(weight_zero_values) != EXPECTED["rows"]:
        raise Htops2607IntegrityError(f"HTOPS {name} full-sample weight row count changed")
    for index, (main_value, weight_zero_value) in enumerate(
        zip(main_values, weight_zero_values, strict=True)
    ):
        if main_value != weight_zero_value:
            raise Htops2607IntegrityError(
                f"HTOPS {name} full-sample weight differs at row {index}"
            )


def validate_summary(**evidence: object) -> None:
    """Fail closed unless every aggregate equals the reviewed official package."""
    for key in (
        "rows", "main_columns", "replicate_columns", "archive_sha256", "main_sha256",
        "replicate_sha256", "dictionary_sha256", "questionnaire_sha256",
        "source_accuracy_sha256", "quality_measures_sha256", "user_note_sha256", "main_schema_sha256",
        "replicate_schema_sha256", "special_rules_sha256", "base_weights",
        "replicate_weights", "variance_factor",
        "imputation", "special_counts",
    ):
        actual = evidence.get(key)
        expected = EXPECTED[key]
        if isinstance(expected, dict):
            actual = {name: tuple(value) if isinstance(value, (list, tuple)) else value
                      for name, value in dict(actual or {}).items()}
        if actual != expected:
            raise Htops2607IntegrityError(f"HTOPS {key} changed")
    if evidence.get("identifier_nulls") != 0 or evidence.get("identifier_unique") != EXPECTED["rows"]:
        raise Htops2607IntegrityError("HTOPS identifier changed")
    if evidence.get("identifier_order_matches") is not True:
        raise Htops2607IntegrityError("HTOPS replicate identifier order changed")
