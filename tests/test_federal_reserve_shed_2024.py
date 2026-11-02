import json
from pathlib import Path

import pytest

from fairlendkit.research.federal_reserve_shed_2024 import (
    ADMISSION_STATUS,
    ADOPTED,
    DISPOSITION,
    EXPECTED,
    REDISTRIBUTION,
    SPECIAL_RESPONSE_RULES,
    USAGE,
    Shed2024IntegrityError,
    analysis_columns,
    schema_sha256,
    special_response_rules_sha256,
    summarize_special_responses,
    summarize_numeric,
    validate_summary,
)


def _valid() -> dict[str, object]:
    return {
        "rows": EXPECTED["rows"],
        "columns": EXPECTED["columns"],
        "schema_sha256": EXPECTED["schema_sha256"],
        "archive_sha256": EXPECTED["archive_sha256"],
        "csv_sha256": EXPECTED["csv_sha256"],
        "identifier_column": "shedid",
        "identifier_index": 0,
        "identifier_nulls": 0,
        "identifier_unique": EXPECTED["rows"],
        "weights": EXPECTED["weights"],
        "missingness": EXPECTED["missingness"],
        "imputation_flags": EXPECTED["imputation_flags"],
        "special_response_rules_sha256": EXPECTED["special_response_rules_sha256"],
        "special_responses": EXPECTED["special_responses"],
    }


def test_reviewed_summary_validates_with_provisional_boundary() -> None:
    validate_summary(**_valid())  # type: ignore[arg-type]
    assert ADMISSION_STATUS == "evidence_incomplete"
    assert ADOPTED is False
    assert DISPOSITION == "external_only"
    assert USAGE == "quality_only"
    assert REDISTRIBUTION == "prohibited"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rows", 1, "shape"),
        ("columns", 1, "shape"),
        ("schema_sha256", "0" * 64, "schema"),
        ("archive_sha256", "0" * 64, "SHA-256"),
        ("csv_sha256", "0" * 64, "SHA-256"),
        ("identifier_column", "respondent_id", "identifier"),
        ("identifier_index", 1, "identifier"),
        ("identifier_nulls", 1, "identifier"),
        ("identifier_unique", 1, "identifier"),
        ("weights", {}, "weight"),
        ("missingness", (1, 1, 1), "missingness"),
        ("imputation_flags", (1, 1, 1, 1, 1), "imputation"),
        ("special_response_rules_sha256", "0" * 64, "mapping"),
        ("special_responses", {}, "special-response"),
    ],
)
def test_evidence_drift_fails_closed(field: str, value: object, message: str) -> None:
    evidence = _valid()
    evidence[field] = value
    with pytest.raises(Shed2024IntegrityError, match=message):
        validate_summary(**evidence)  # type: ignore[arg-type]


def test_numeric_summary_separates_invalid_values() -> None:
    assert summarize_numeric(("", "1", "0", "-2", "nan", "bad")) == (
        1, 2, 1, 1, -2.0, 1.0,
    )


def test_shedid_is_excluded_from_analysis() -> None:
    assert analysis_columns(("shedid", "weight", "B2")) == ("weight", "B2")
    with pytest.raises(Shed2024IntegrityError, match="required"):
        analysis_columns(("weight", "B2"))
    with pytest.raises(Shed2024IntegrityError, match="required"):
        analysis_columns(("shedid", "SHEDID", "weight"))


def test_ordered_schema_digest_detects_name_order_and_case_drift() -> None:
    baseline = schema_sha256(("shedid", "weight", "B2"))
    assert baseline != schema_sha256(("shedid", "B2", "weight"))
    assert baseline != schema_sha256(("SHEDID", "weight", "B2"))


def test_codebook_mapping_and_special_counts_are_deterministic() -> None:
    assert special_response_rules_sha256(SPECIAL_RESPONSE_RULES) == EXPECTED[
        "special_response_rules_sha256"
    ]
    row = {column: "" for columns in SPECIAL_RESPONSE_RULES.values() for column in columns}
    row.update({"ind1": "-2", "A6": "Don't know", "ND1_e": "Refused"})
    assert summarize_special_responses((row,)) == {
        "not_asked": 1,
        "dont_know": 1,
        "refused": 1,
    }


def test_special_response_mapping_drift_fails_closed() -> None:
    drifted = {
        category: dict(columns) for category, columns in SPECIAL_RESPONSE_RULES.items()
    }
    drifted["dont_know"]["A6"] = ("Refused",)
    evidence = _valid()
    evidence["special_response_rules_sha256"] = special_response_rules_sha256(drifted)
    with pytest.raises(Shed2024IntegrityError, match="mapping"):
        validate_summary(**evidence)  # type: ignore[arg-type]


def test_manifest_pins_schema_identifier_and_special_response_rules() -> None:
    manifest = json.loads(
        Path("docs/data-sources/federal-reserve-shed-2024-evaluation-manifest.json")
        .read_text(encoding="utf-8")
    )
    assert manifest["shape"]["ordered_schema_sha256"] == EXPECTED["schema_sha256"]
    assert manifest["identifier"] == {
        "column": "shedid",
        "zero_based_index": 0,
        "missing": 0,
        "unique": 12295,
        "analysis_use": "prohibited",
    }
    evidence = manifest["special_response_evidence"]
    assert evidence["rules_sha256"] == special_response_rules_sha256(evidence["rules"])
    assert evidence["rules_sha256"] == EXPECTED["special_response_rules_sha256"]
    assert evidence["counts"] == EXPECTED["special_responses"]
