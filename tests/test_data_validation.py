import pandas as pd
import pytest

from fairlendkit import AuditConfig, DataValidationError, validate_audit_data


def make_config(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "favorable_label": 1,
        "score_direction": "higher_is_more_favorable",
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
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
    )

    summary = validate_audit_data(data, config)

    assert summary.eligible_rows == 3

