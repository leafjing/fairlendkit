import pytest

from fairlendkit.research.cfpb_making_ends_meet import (
    DISPOSITION,
    REDISTRIBUTION,
    SAMPLES,
    USAGE,
    MakingEndsMeetIntegrityError,
    analysis_columns,
    summarize_missingness,
    summarize_weight_values,
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
        "weight_statistics": expected["weight_statistics"],
        "missingness": expected["missingness"],
        "special_response_counts": expected["special_response_counts"],
    }


def test_all_reviewed_samples_validate_as_external_quality_only() -> None:
    for sample in SAMPLES:
        validate_sample_summary(sample, **_valid(sample))  # type: ignore[arg-type]
    assert DISPOSITION == "external_only"
    assert USAGE == "quality_only"
    assert REDISTRIBUTION == "prohibited"
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
        ("weight_statistics", {}, "weight statistics"),
        ("missingness", (1, 1, 1, 1), "missingness"),
        ("special_response_counts", {"wrong": 1}, "special-response"),
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


def test_aggregate_summaries_keep_blanks_and_special_codes_distinct() -> None:
    assert summarize_weight_values(("", "1.5", "0", "-2", "nan", "bad")) == (
        1, 2, 1, 1, -2.0, 1.5,
    )
    rows = (
        {"survey": "", "response": "3", "imputed_flag": "0"},
        {"survey": "1", "response": "", "imputed_flag": "1"},
    )
    assert summarize_missingness(rows, ("survey", "response", "imputed_flag")) == (
        2, 2, 1, 1,
    )


def test_weight_summary_without_finite_values_fails_closed() -> None:
    with pytest.raises(MakingEndsMeetIntegrityError, match="no finite"):
        summarize_weight_values(("", "nan"))
