import pytest

from fairlendkit.research.cfpb_making_ends_meet import (
    DISPOSITION,
    SAMPLES,
    USAGE,
    MakingEndsMeetIntegrityError,
    analysis_columns,
    validate_sample_summary,
)


def _valid(sample: int) -> dict[str, object]:
    expected = SAMPLES[sample]
    return {
        "rows": expected["rows"],
        "columns": expected["columns"],
        "archive_sha256": expected["archive_sha256"],
        "csv_sha256": expected["csv_sha256"],
        "identifier_nulls": 0,
        "identifier_unique": expected["rows"],
        "weight_columns": expected["weights"],
    }


def test_all_reviewed_samples_validate_as_external_quality_only() -> None:
    for sample in SAMPLES:
        validate_sample_summary(sample, **_valid(sample))  # type: ignore[arg-type]
    assert DISPOSITION == "external_only"
    assert USAGE == "quality_only"
    assert set(SAMPLES) == {1, 3, 4, 5, 6}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rows", 1, "shape"),
        ("columns", 1, "shape"),
        ("archive_sha256", "0" * 64, "SHA-256"),
        ("csv_sha256", "0" * 64, "SHA-256"),
        ("identifier_nulls", 1, "respondent ID"),
        ("identifier_unique", 1, "respondent ID"),
        ("weight_columns", ("wrong",), "weight columns"),
    ],
)
def test_sample_evidence_drift_fails_closed(field: str, value: object, message: str) -> None:
    evidence = _valid(1)
    evidence[field] = value
    with pytest.raises(MakingEndsMeetIntegrityError, match=message):
        validate_sample_summary(1, **evidence)  # type: ignore[arg-type]


def test_unpublished_sample_two_is_rejected() -> None:
    with pytest.raises(MakingEndsMeetIntegrityError, match="not part"):
        validate_sample_summary(2, **_valid(1))  # type: ignore[arg-type]


def test_random_id_is_removed_from_analysis_columns() -> None:
    assert analysis_columns(("ID", "weight", "difficulty_paying")) == (
        "weight", "difficulty_paying",
    )
    with pytest.raises(MakingEndsMeetIntegrityError, match="required"):
        analysis_columns(("weight", "difficulty_paying"))
