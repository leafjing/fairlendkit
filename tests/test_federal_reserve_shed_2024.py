import pytest

from fairlendkit.research.federal_reserve_shed_2024 import (
    ADMISSION_STATUS,
    ADOPTED,
    DISPOSITION,
    EXPECTED,
    REDISTRIBUTION,
    USAGE,
    Shed2024IntegrityError,
    analysis_columns,
    summarize_numeric,
    validate_summary,
)


def _valid() -> dict[str, object]:
    return {
        "rows": EXPECTED["rows"],
        "columns": EXPECTED["columns"],
        "archive_sha256": EXPECTED["archive_sha256"],
        "csv_sha256": EXPECTED["csv_sha256"],
        "identifier_nulls": 0,
        "identifier_unique": EXPECTED["rows"],
        "weights": EXPECTED["weights"],
        "missingness": EXPECTED["missingness"],
        "imputation_flags": EXPECTED["imputation_flags"],
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
        ("archive_sha256", "0" * 64, "SHA-256"),
        ("csv_sha256", "0" * 64, "SHA-256"),
        ("identifier_nulls", 1, "identifier"),
        ("identifier_unique", 1, "identifier"),
        ("weights", {}, "weight"),
        ("missingness", (1, 1, 1), "missingness"),
        ("imputation_flags", (1, 1, 1, 1, 1), "imputation"),
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
