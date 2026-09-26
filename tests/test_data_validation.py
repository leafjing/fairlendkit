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
    unknown_evidence = next(
        item
        for item in summary.exclusion_evidence
        if item.reason == "unknown_protected_group"
    )
    assert unknown_evidence.attribute == "group"
    assert unknown_evidence.observed_value == "C"
    assert unknown_evidence.count == 2


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


def test_small_group_counts_keep_boolean_and_integer_groups_distinct():
    data = make_data().assign(group=[1, True, True])
    config = make_config(
        reference_groups={"group": 1},
        allowed_groups={"group": (1, True)},
        minimum_group_size=2,
    )

    summary = validate_audit_data(data, config)

    assert summary.small_groups == ("group=1",)


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


def test_rejected_run_retains_all_reason_codes_and_evidence():
    data = pd.DataFrame(
        {
            "outcome": [1, 0, 1],
            "score": [0.9, None, 0.7],
            "group": ["A", "C", None],
        }
    )

    with pytest.raises(DataValidationError) as caught:
        validate_audit_data(data, make_config())

    assert caught.value.reason_counts == {
        "missing_required_value": 2,
        "unknown_protected_group": 1,
    }
    assert {
        (item.reason, item.attribute, item.observed_value, item.count)
        for item in caught.value.evidence
    } == {
        ("missing_required_value", "group", None, 1),
        ("missing_required_value", "score", None, 1),
        ("unknown_protected_group", "group", "C", 1),
    }


@pytest.mark.parametrize("use_record_id", [False, True])
@pytest.mark.parametrize("policy", ["error", "exclude", "allow"])
def test_duplicate_policies_apply_to_all_occurrences(policy, use_record_id):
    data = pd.DataFrame(
        {
            "outcome": [1, 1, 0, 1],
            "score": [0.9, 0.9, 0.2, 0.8],
            "group": ["A", "A", "B", "A"],
            "id": ["same", "same", "other", "unique"],
        }
    )
    config = make_config(
        duplicate_policy=policy,
        record_id_column="id" if use_record_id else None,
        minimum_group_size=1,
    )
    if policy == "error" or (policy == "allow" and use_record_id):
        with pytest.raises(DataValidationError, match="duplicate|unique"):
            validate_audit_data(data, config)
        return

    summary = validate_audit_data(data, config)
    assert summary.duplicate_rows == 2
    assert summary.exclusion_reason_counts["duplicate_record"] == 2
    assert summary.excluded_rows == (2 if policy == "exclude" else 0)


def test_record_id_duplicates_are_type_sensitive():
    data = make_data().assign(id=pd.Series([1, True, "1"], dtype=object))
    summary = validate_audit_data(
        data,
        make_config(record_id_column="id", duplicate_policy="allow", minimum_group_size=1),
    )

    assert summary.duplicate_rows == 0


def test_missing_record_ids_follow_missing_policy_and_required_columns():
    with pytest.raises(DataValidationError, match="missing required columns: id"):
        validate_audit_data(make_data(), make_config(record_id_column="id"))

    summary = validate_audit_data(
        make_data().assign(id=["a", None, "c"]),
        make_config(
            record_id_column="id",
            missing_value_policy="exclude",
            minimum_group_size=1,
        ),
    )
    assert summary.excluded_rows == 1
    assert summary.duplicate_rows == 0


@pytest.mark.parametrize("values", [["0.9", "0.4", "0.7"], [True, False, True]])
def test_score_requires_non_boolean_numeric_dtype(values):
    with pytest.raises(DataValidationError, match="non-boolean numeric dtype"):
        validate_audit_data(make_data().assign(score=values), make_config())


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_infinite_numbers_have_stable_reason(value):
    data = make_data()
    data.loc[1, "score"] = value
    with pytest.raises(DataValidationError, match="non-finite") as caught:
        validate_audit_data(data, make_config())

    assert caught.value.reason_counts["non_finite_numeric"] == 1


@pytest.mark.parametrize(
    ("weights", "message"),
    [([-1.0, 1.0, 1.0], "non-negative"), ([0.0, 0.0, 0.0], "positive sum")],
)
def test_weight_bounds_apply_to_final_eligible_rows(weights, message):
    with pytest.raises(DataValidationError, match=message):
        validate_audit_data(
            make_data().assign(weight=weights),
            make_config(sample_weight_column="weight"),
        )


def test_excluded_negative_weight_does_not_invalidate_final_eligible_rows():
    data = make_data().assign(weight=[1.0, 1.0, -1.0], id=["a", "b", "dup"])
    data = pd.concat([data, data.iloc[[2]]], ignore_index=True)

    summary = validate_audit_data(
        data,
        make_config(
            sample_weight_column="weight",
            record_id_column="id",
            duplicate_policy="exclude",
            minimum_group_size=1,
        ),
    )
    assert summary.eligible_rows == 2


def test_expected_categories_reject_unexpected_typed_values():
    data = make_data().assign(outcome=pd.Series([True, 0, True], dtype=object))
    config = make_config(
        favorable_label=True,
        expected_categories={"outcome": (True, 0)},
    )
    validate_audit_data(data, config)

    data.loc[1, "outcome"] = 1
    with pytest.raises(DataValidationError, match="unexpected categories") as caught:
        validate_audit_data(data, config)
    assert caught.value.reason_counts["unexpected_category"] == 1


def test_multiple_reasons_count_independently_but_exclusions_use_union():
    data = pd.DataFrame(
        {
            "outcome": [1, 1, 0, 0, 1],
            "score": [0.9, 0.9, 0.2, 0.1, 0.8],
            "group": ["A", "A", "C", "B", "A"],
            "id": [None, None, "c", "d", "e"],
        }
    )
    summary = validate_audit_data(
        data,
        make_config(
            record_id_column="id",
            duplicate_policy="exclude",
            missing_value_policy="exclude",
            unknown_group_policy="exclude",
            minimum_group_size=1,
        ),
    )

    assert summary.reason_counts == (
        ("missing_required_value", 2),
        ("unknown_protected_group", 1),
    )
    assert summary.excluded_rows == 3


def test_duplicate_and_unknown_exclusions_do_not_hide_each_other():
    data = pd.DataFrame(
        {
            "outcome": [1, 1, 0, 0, 1],
            "score": [0.9, 0.9, 0.2, 0.1, 0.8],
            "group": ["A", "A", "C", "B", "A"],
        }
    )
    summary = validate_audit_data(
        data,
        make_config(
            duplicate_policy="exclude",
            unknown_group_policy="exclude",
            minimum_group_size=1,
        ),
    )
    assert summary.reason_counts == (
        ("duplicate_record", 2),
        ("unknown_protected_group", 1),
    )
    assert summary.excluded_rows == 3


def test_validation_counts_are_permutation_invariant_and_input_is_unchanged():
    data = pd.concat([make_data(), make_data().iloc[[0]]], ignore_index=True)
    before = data.copy(deep=True)
    config = make_config(duplicate_policy="exclude", minimum_group_size=1)

    first = validate_audit_data(data, config)
    second = validate_audit_data(data.sample(frac=1, random_state=7), config)

    assert first == second
    pd.testing.assert_frame_equal(data, before)
