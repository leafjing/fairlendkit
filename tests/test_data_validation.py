import pandas as pd
import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, DataValidationError, validate_audit_data


def make_config(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "Completed applications in the review period",
        "sampling_definition": "All eligible records; no sampling",
        "score_type": "ranking",
        "dataset_version": "applications-v1",
        "model_version": None,
        "data_as_of": "2026-07-01T00:00:00Z",
        "execution_timestamp": "2026-07-02T12:30:00Z",
        "favorable_label": 1,
        "score_direction": "higher_is_more_favorable",
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B")},
        "favorable_decision_label": 1,
        "decision_threshold": 0.5,
        "threshold_operator": "ge",
        "minimum_group_size": 2,
    }
    values.update(overrides)
    return AuditConfig(**values)


def make_data():
    return pd.DataFrame(
        {
            "outcome": [1, 0, 1],
            "score": [0.9, 0.4, 0.7],
            "group": ["A", "A", "B"],
        }
    )


def test_missing_column_fails_validation():
    with pytest.raises(DataValidationError, match="missing required columns: score"):
        validate_audit_data(make_data().drop(columns="score"), make_config())


def test_unknown_reference_group_fails_validation():
    with pytest.raises(ValidationError, match="must belong to allowed_groups"):
        validate_audit_data(make_data(), make_config(reference_groups={"group": "C"}))


def test_small_groups_are_reported_not_removed():
    summary = validate_audit_data(make_data(), make_config())

    assert summary.eligible_rows == 3
    assert summary.small_groups == ("group='B'",)


def test_excluded_missing_values_are_counted():
    data = make_data()
    data.loc[2, "score"] = None

    summary = validate_audit_data(
        data, make_config(missing_value_policy="exclude")
    )

    assert summary.input_rows == 3
    assert summary.eligible_rows == 2
    assert summary.excluded_rows == 1


def test_favorable_label_reversal_is_accepted_when_value_exists():
    config = make_config(favorable_label=0)

    validate_audit_data(make_data(), config)


def test_multiple_protected_attributes_require_known_references():
    data = make_data().assign(region=["north", "south", "north"])
    config = make_config(
        protected_attributes=("group", "region"),
        reference_groups={"group": "A", "region": "north"},
        allowed_groups={"group": ("A", "B"), "region": ("north", "south")},
    )

    summary = validate_audit_data(data, config)

    assert summary.eligible_rows == 3


def test_boolean_favorable_label_does_not_match_integer_one():
    with pytest.raises(DataValidationError, match="favorable_label is not present"):
        validate_audit_data(make_data(), make_config(favorable_label=True))


def test_boolean_reference_group_does_not_match_integer_one():
    data = make_data().assign(group=[1, 1, 2])

    with pytest.raises(ValidationError, match="must belong to allowed_groups"):
        validate_audit_data(
            data,
            make_config(
                reference_groups={"group": True},
                allowed_groups={"group": (1, 2)},
            ),
        )


def test_boolean_favorable_decision_does_not_match_integer_one():
    data = make_data().assign(decision=[1, 0, 1])
    config = make_config(
        decision_column="decision",
        decision_threshold=None,
        threshold_operator=None,
        favorable_decision_label=True,
    )

    with pytest.raises(DataValidationError, match="favorable_decision_label"):
        validate_audit_data(data, config)


def test_unknown_group_is_not_silently_excluded_by_default():
    data = make_data().assign(group=["A", "B", "C"])

    with pytest.raises(DataValidationError, match="unknown protected groups"):
        validate_audit_data(data, make_config())


def test_missing_and_unknown_exclusions_are_orthogonal_and_deduplicated():
    data = pd.DataFrame(
        {
            "outcome": [1, 0, 1, 0],
            "score": [0.9, None, 0.7, 0.2],
            "group": ["A", "C", None, "C"],
        }
    )
    summary = validate_audit_data(
        data,
        make_config(
            missing_value_policy="exclude",
            unknown_group_policy="exclude",
            minimum_group_size=1,
        ),
    )

    assert summary.eligible_rows == 1
    assert summary.excluded_rows == 3
    assert summary.exclusion_reason_counts == {
        "missing_required_value": 2,
        "unknown_protected_group": 2,
    }
    assert summary.exclusion_evidence[0].attribute == "group"
    assert summary.exclusion_evidence[0].observed_value == "C"
    assert summary.exclusion_evidence[0].count == 2


def test_allowed_groups_use_type_sensitive_membership():
    data = make_data().assign(group=[1, True, 2])
    config = make_config(
        reference_groups={"group": 1},
        allowed_groups={"group": (1, 2)},
        unknown_group_policy="exclude",
        minimum_group_size=1,
    )

    summary = validate_audit_data(data, config)

    assert summary.eligible_rows == 2
    assert summary.exclusion_reason_counts["unknown_protected_group"] == 1


def test_validation_does_not_mutate_input_dataframe():
    data = pd.DataFrame(
        {
            "outcome": pd.Series([1, 0, 1], dtype="Int64"),
            "score": pd.Series([0.9, float("nan"), 0.7], dtype="float64"),
            "group": pd.Series(["A", "C", None], dtype="string"),
        },
        index=pd.Index([10, 20, 30], name="application_id"),
    )
    before = data.copy(deep=True)

    with pytest.raises(DataValidationError):
        validate_audit_data(
            data,
            make_config(
                missing_value_policy="exclude",
                unknown_group_policy="exclude",
            ),
        )

    pd.testing.assert_frame_equal(data, before, check_dtype=True, check_names=True)
