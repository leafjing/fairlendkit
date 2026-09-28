import json
import math

import pandas as pd
import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, LayeredValidationResult, SingleRunProfile, validate_audit_data
from fairlendkit.report import AuditResult


def config(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "Completed applications",
        "sampling_definition": "All records",
        "score_type": "ranking",
        "dataset_version": "v1",
        "model_version": None,
        "data_as_of": "2026-07-01T00:00:00Z",
        "execution_timestamp": "2026-07-02T00:00:00Z",
        "favorable_label": 1,
        "score_direction": "higher_is_more_favorable",
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B", "C")},
        "favorable_decision_label": 1,
        "decision_threshold": 0.5,
        "threshold_operator": "ge",
        "minimum_group_size": 1,
        "record_id_column": "id",
    }
    values.update(overrides)
    return AuditConfig(**values)


def frame():
    return pd.DataFrame(
        {
            "id": ["r1", "r2", "r3", "r4"],
            "outcome": [1, 0, 1, 0],
            "score": [0.0, 1.0, 2.0, 10.0],
            "group": ["A", "A", "B", "B"],
        }
    )


def test_epic_2_1_ac1_complete_profile_attached_and_legacy_null():
    result = validate_audit_data(frame(), config())
    assert result.profile is not None
    assert (result.profile.input_rows, result.profile.eligible_rows, result.profile.excluded_rows) == (4, 4, 0)
    legacy = result.model_dump()
    legacy.pop("profile")
    assert LayeredValidationResult.model_validate(legacy).profile is None
    assert SingleRunProfile.model_validate_json(result.profile.model_dump_json()) == result.profile


def test_epic_2_1_ac2_missingness_input_scope_typed_groups_and_zeros():
    data = frame()
    data.loc[2, "score"] = None
    result = validate_audit_data(data, config(missing_value_policy="exclude"))
    entries = [item for item in result.profile.missingness if item.field == "score"]
    assert [(item.group.attributes if item.group else None, item.missing_count, item.total_count) for item in entries] == [
        (None, 1, 4),
        ({"group": "A"}, 0, 2),
        ({"group": "B"}, 1, 2),
    ]
    assert entries[0].missing_rate == 0.25


def test_epic_2_1_ac3_configured_zero_count_groups_and_reference_flags():
    profile = validate_audit_data(frame(), config()).profile
    assert [(item.group.attributes["group"], item.population, item.count, item.is_reference) for item in profile.groups] == [
        ("A", "input", 2, True), ("A", "eligible", 2, True),
        ("B", "input", 2, False), ("B", "eligible", 2, False),
        ("C", "input", 0, False), ("C", "eligible", 0, False),
    ]


def test_epic_2_1_ac3_integer_groups_use_numeric_canonical_order():
    data = frame().assign(group=[10, 2, 10, 2])
    profile = validate_audit_data(
        data,
        config(
            allowed_groups={"group": (10, 2)},
            reference_groups={"group": 2},
        ),
    ).profile
    assert [item.group.attributes["group"] for item in profile.groups] == [2, 2, 10, 10]


def test_epic_2_1_ac4_all_anomalies_reconcile_without_duplicate_issues():
    data = pd.DataFrame(
        {
            "id": ["x", "x", "z", "w", "v"],
            "outcome": [1, 1, 0, 1, 0],
            "score": [None, 0.9, 0.2, 0.8, 0.4],
            "group": ["A", "A", "C", "B", "A"],
        }
    )
    result = validate_audit_data(
        data,
        config(
            allowed_groups={"group": ("A", "B")},
            duplicate_policy="exclude",
            missing_value_policy="exclude",
            unknown_group_policy="exclude",
        ),
    )
    observed = {item.code.value: item.count for item in result.profile.anomalies}
    assert set(observed) == {"missing_required_value", "unknown_protected_group", "unexpected_category", "duplicate_record", "non_finite_numeric"}
    assert observed["missing_required_value"] == 1
    assert observed["unknown_protected_group"] == 1
    assert observed["duplicate_record"] == 2
    assert all(issue.code not in observed for issue in result.profile.issues)
    assert sum(observed.values()) > result.excluded_rows


def test_epic_2_1_ac5_deterministic_distribution_type7_singleton_and_negative_zero():
    data = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d", "e"],
            "outcome": [1, 0, 1, 0, 1],
            "score": [1e16, 1.0, -1e16, -0.0, 3.0],
            "group": ["A", "A", "B", "B", "B"],
        }
    )
    first = validate_audit_data(data, config(allowed_groups={"group": ("A", "B")}))
    second = validate_audit_data(data.iloc[::-1], config(allowed_groups={"group": ("A", "B")}))
    assert first.model_dump_json() == second.model_dump_json()
    distribution = first.profile.score_distribution
    assert distribution.mean == math.fsum(sorted(float(value) for value in data.score)) / 5
    assert distribution.standard_deviation == math.sqrt(math.fsum((value - distribution.mean) ** 2 for value in sorted(data.score)) / 5)
    assert [item.value for item in distribution.quantiles] == [-1e16, 0.0, 1.0, 3.0, 1e16]
    assert '"value":-0.0' not in first.model_dump_json()

    singleton = data.iloc[[1]].assign(group="A", outcome=1)
    one = validate_audit_data(singleton, config(allowed_groups={"group": ("A",)})).profile.score_distribution
    assert one.standard_deviation == 0.0
    assert len({item.value for item in one.quantiles}) == 1


def test_epic_2_1_ac5_derived_nonfinite_fails_closed():
    data = pd.DataFrame(
        {"id": ["a", "b"], "outcome": [1, 0], "score": [-1e308, 1e308], "group": ["A", "A"]}
    )
    with pytest.raises(ValueError, match="invariant failure"):
        validate_audit_data(data, config(allowed_groups={"group": ("A",)}))


def test_epic_2_1_ac6_outcomes_preserve_typed_labels_and_order():
    data = pd.DataFrame(
        {"id": ["a", "b", "c"], "outcome": [True, 1, "1"], "score": [0.1, 0.2, 0.3], "group": ["A", "A", "A"]}
    )
    profile = validate_audit_data(data, config(allowed_groups={"group": ("A",)}, favorable_label=True)).profile
    assert [(type(item.value), item.value, item.count) for item in profile.outcome_distribution] == [(bool, True, 1), (int, 1, 1), (str, "1", 1)]


def test_epic_2_1_ac7_tukey_strict_fences_zero_iqr_and_issue_evidence():
    profile = validate_audit_data(frame(), config()).profile
    assert (profile.outliers.q1, profile.outliers.q3) == (0.75, 4.0)
    assert profile.outliers.upper_fence == 8.875
    assert (profile.outliers.lower_count, profile.outliers.upper_count, profile.outliers.outlier_count) == (0, 1, 1)
    issue = profile.issues[0]
    assert issue.code == "score_outliers_observed"
    assert issue.evidence.count == 1 and issue.evidence.maximum == 8.875

    zero_iqr_data = pd.DataFrame(
        {"id": ["a", "b", "c", "d", "e"], "outcome": [1, 0, 1, 0, 1], "score": [1, 1, 1, 1, 2], "group": ["A"] * 5}
    )
    zero = validate_audit_data(zero_iqr_data, config(allowed_groups={"group": ("A",)})).profile.outliers
    assert zero.iqr == 0 and zero.upper_count == 1

    fence_data = pd.DataFrame(
        {"id": ["a", "b", "c", "d"], "outcome": [1, 0, 1, 0], "score": [0, 0, 1, 5], "group": ["A"] * 4}
    )
    fence = validate_audit_data(fence_data, config(allowed_groups={"group": ("A",)})).profile.outliers
    assert fence.upper_fence == 5 and fence.upper_count == 0


def test_epic_2_1_ac8_freshness_utc_unavailable_and_future():
    shifted = validate_audit_data(frame(), config(data_as_of="2026-06-30T20:00:00-04:00", execution_timestamp="2026-07-02T00:00:00Z")).profile
    assert shifted.freshness.data_as_of == "2026-07-01T00:00:00Z"
    assert shifted.freshness.age_seconds == 86400
    no_outlier = frame().assign(score=[0.0, 1.0, 2.0, 3.0])
    unavailable = validate_audit_data(no_outlier, config(data_as_of=None))
    assert unavailable.profile.freshness.reason_code == "data_freshness_unavailable"
    assert unavailable.layers[-1].status == "passed"
    future = validate_audit_data(frame(), config(data_as_of="2026-07-03T00:00:00Z"))
    assert future.profile.freshness.status == "future_dated"
    assert "data_as_of_after_execution" in {issue.code for issue in future.layers[-1].issues}


def test_epic_2_1_ac9_data_quality_contains_exact_profile_issues_without_baseline():
    result = validate_audit_data(frame(), config(data_as_of=None))
    assert result.layers[-1].issues == result.profile.issues
    assert result.layers[-1].status == "warning"  # outlier warning wins over freshness info
    assert all(issue.code != "comparison_baseline_unavailable" for issue in result.profile.issues)


def test_epic_2_1_ac10_mapping_index_and_timezone_spelling_are_invariant():
    data = frame()
    first = validate_audit_data(data, config(data_as_of="2026-07-01T00:00:00Z"))
    reordered = data.iloc[::-1].copy()
    reordered.index = [100, 50, 20, 10]
    second = validate_audit_data(reordered, config(data_as_of="2026-06-30T20:00:00-04:00", allowed_groups={"group": ("A", "B", "C")}, reference_groups={"group": "A"}))
    assert first.model_dump_json() == second.model_dump_json()


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("input_rows",), True),
        (("excluded_rows",), -1),
        (("missingness", 0, "missing_rate"), 2.0),
        (("score_distribution", "mean"), float("inf")),
        (("outliers", "outlier_count"), 99),
        (("anomalies", 0, "total_count"), 3),
        (("freshness", "age_seconds"), 42),
        (("outliers", "field"), "other_score"),
    ],
)
def test_epic_2_1_ac11_strict_models_reject_invalid_values(path, value):
    payload = validate_audit_data(frame(), config()).profile.model_dump()
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        SingleRunProfile.model_validate(payload)


def test_epic_2_1_ac11_unknown_and_raw_identifier_fields_rejected():
    payload = validate_audit_data(frame(), config()).profile.model_dump()
    payload["raw_identifiers"] = ["r1"]
    with pytest.raises(ValidationError, match="Extra inputs"):
        SingleRunProfile.model_validate(payload)
    assert "id" not in json.dumps(payload["outliers"])


def test_epic_2_1_ac11_freshness_rejects_inconsistent_time_order():
    payload = validate_audit_data(frame(), config()).profile.model_dump()
    payload["freshness"]["data_as_of"] = "2026-07-03T00:00:00Z"
    with pytest.raises(ValidationError, match="available freshness"):
        SingleRunProfile.model_validate(payload)

    payload = validate_audit_data(
        frame(), config(data_as_of="2026-07-03T00:00:00Z")
    ).profile.model_dump()
    payload["freshness"]["data_as_of"] = "2026-07-01T00:00:00Z"
    with pytest.raises(ValidationError, match="future_dated freshness"):
        SingleRunProfile.model_validate(payload)


def test_epic_2_1_ac11_rejects_issue_evidence_inconsistent_with_profile():
    payload = validate_audit_data(frame(), config()).profile.model_dump()
    outlier_issue = next(
        issue for issue in payload["issues"] if issue["code"] == "score_outliers_observed"
    )
    outlier_issue["affected_fields"] = ("wrong_score",)
    with pytest.raises(ValidationError, match="outlier issue evidence"):
        SingleRunProfile.model_validate(payload)

    payload = validate_audit_data(
        frame(), config(data_as_of="2026-07-03T00:00:00Z")
    ).profile.model_dump()
    freshness_issue = next(
        issue for issue in payload["issues"] if issue["code"] == "data_as_of_after_execution"
    )
    freshness_issue["evidence"]["observed"] = "2026-07-04T00:00:00Z"
    with pytest.raises(ValidationError, match="future-dated issue evidence"):
        SingleRunProfile.model_validate(payload)

    payload = validate_audit_data(
        frame(), config(data_as_of="2026-07-03T00:00:00Z")
    ).profile.model_dump()
    freshness_issue = next(
        issue for issue in payload["issues"] if issue["code"] == "data_as_of_after_execution"
    )
    freshness_issue["evidence"]["expected"] = "2026-07-05T00:00:00Z"
    with pytest.raises(ValidationError, match="future-dated issue evidence"):
        SingleRunProfile.model_validate(payload)


def test_epic_2_1_ac12_public_compatibility_and_report_schema_are_additive():
    result = validate_audit_data(frame(), config())
    assert result.analyzed_rows == result.eligible_rows
    assert result.exclusion_reason_counts == {}
    validation_schema = AuditResult.model_json_schema()["$defs"]["ValidationEvidence"]
    assert "profile" in validation_schema["properties"]
