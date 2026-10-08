import pandas as pd
import pytest

from fairlendkit import AuditConfig, DataValidationError, validate_audit_data


def make_config(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "All applications in the review period",
        "score_type": "ranking",
        "dataset_version": None,
        "model_version": None,
        "data_as_of": None,
        "favorable_label": 1,
        "score_direction": "higher_is_more_favorable",
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B")},
        "unknown_group_policy": "error",
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
    with pytest.raises(DataValidationError, match="not present"):
        validate_audit_data(
            make_data(),
            make_config(
                reference_groups={"group": "C"},
                allowed_groups={"group": ("A", "B", "C")},
            ),
        )


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
    assert summary.exclusion_reason_counts == {"missing_required_value": 1}


def test_overlapping_exclusion_reasons_are_deduplicated():
    data = make_data()
    data.loc[2, "score"] = None
    data.loc[2, "group"] = "C"

    summary = validate_audit_data(
        data,
        make_config(missing_value_policy="exclude", unknown_group_policy="exclude"),
    )

    assert summary.excluded_rows == 1
    assert summary.exclusion_reason_counts == {
        "missing_required_value": 1,
        "unknown_protected_group": 1,
    }


def test_reference_group_must_remain_after_all_exclusions():
    data = make_data().assign(group=["A", "B", "B"])
    data.loc[0, "score"] = None

    with pytest.raises(DataValidationError, match="eligible data"):
        validate_audit_data(data, make_config(missing_value_policy="exclude"))


def test_favorable_label_reversal_is_accepted_when_value_exists():
    config = make_config(favorable_label=0)

    validate_audit_data(make_data(), config)


def test_multiple_protected_attributes_require_known_references():
    data = make_data().assign(region=["north", "south", "north"])
    config = make_config(
        protected_attributes=("group", "region"),
        reference_groups={"group": "A", "region": "north"},
        allowed_groups={
            "group": ("A", "B"),
            "region": ("north", "south"),
        },
    )

    summary = validate_audit_data(data, config)

    assert summary.eligible_rows == 3


def test_boolean_favorable_label_does_not_match_integer_one():
    with pytest.raises(DataValidationError, match="favorable_label is not present"):
        validate_audit_data(make_data(), make_config(favorable_label=True))


def test_boolean_reference_group_does_not_match_integer_one():
    data = make_data().assign(group=[1, 1, 2])

    with pytest.raises(DataValidationError, match="reference group"):
        validate_audit_data(
            data,
            make_config(
                reference_groups={"group": True},
                allowed_groups={"group": (True, 1, 2)},
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


def test_unknown_group_value_errors_by_default():
    data = make_data().assign(group=["A", "B", "C"])

    with pytest.raises(DataValidationError, match="unknown group values.*'C'"):
        validate_audit_data(data, make_config())


def test_excluded_unknown_group_has_stable_reason_and_evidence():
    data = make_data().assign(group=["A", "B", "C"])
    summary = validate_audit_data(
        data, make_config(unknown_group_policy="exclude")
    )

    assert summary.eligible_rows == 2
    assert summary.excluded_rows == 1
    assert summary.exclusion_reason_counts == {"unknown_protected_group": 1}
    assert summary.exclusion_evidence[0].reason_code == "unknown_protected_group"
    assert summary.exclusion_evidence[0].attribute == "group"
    assert summary.exclusion_evidence[0].observed_value == "C"


def test_missing_group_uses_required_value_policy():
    data = make_data()
    data.loc[2, "group"] = None

    with pytest.raises(DataValidationError, match="missing required values"):
        validate_audit_data(
            data,
            make_config(missing_value_policy="error"),
        )


def test_excluded_missing_group_is_counted_not_silent():
    data = make_data()
    data.loc[2, "group"] = None
    summary = validate_audit_data(
        data,
        make_config(missing_value_policy="exclude"),
    )

    assert summary.eligible_rows == 2
    assert summary.excluded_rows == 1


def test_boolean_and_integer_groups_are_counted_separately():
    data = make_data().assign(group=[True, 1, False])
    config = make_config(
        reference_groups={"group": True},
        allowed_groups={"group": (True, 1, False)},
        minimum_group_size=2,
    )

    summary = validate_audit_data(data, config)

    assert summary.small_groups == (
        "group=1",
        "group=False",
        "group=True",
    )
