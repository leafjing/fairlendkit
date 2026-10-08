import json

import pandas as pd
import pytest
from pydantic import ValidationError

from fairlendkit import (
    AuditConfig,
    BaselineComparisonPolicy,
    BaselineSelection,
    LayeredValidationResult,
    attach_baseline_comparison,
    compare_profiles,
    to_validation_evidence,
    validate_audit_data,
)
from fairlendkit.data import canonical_profile_digest


def config(**changes):
    values = dict(
        outcome_column="outcome", score_column="score",
        population_definition="Completed applications", sampling_definition="All records",
        score_type="ranking", dataset_version="data-v1", model_version="model-v1",
        data_as_of="2026-07-01T00:00:00Z", execution_timestamp="2026-07-02T00:00:00Z",
        favorable_label=1, score_direction="higher_is_more_favorable",
        protected_attributes=("group",), reference_groups={"group": "A"},
        allowed_groups={"group": ("A", "B", "C")}, favorable_decision_label=1,
        decision_threshold=0.5, threshold_operator="ge", minimum_group_size=1,
    )
    values.update(changes)
    return AuditConfig(**values)


def frame(*, shifted=False):
    return pd.DataFrame({
        "outcome": [1, 0, 1, 0] if not shifted else [1, 1, 1, 0],
        "score": [0.0, 1.0, 2.0, 3.0] if not shifted else [1.0, 2.0, 3.0, 4.0],
        "group": ["A", "A", "B", "B"] if not shifted else ["A", "B", "B", "B"],
    })


def policy():
    return BaselineComparisonPolicy(
        group_proportion_delta=0.25, missingness_rate_delta=0.1,
        score_quantile_delta=1.0, outcome_proportion_delta=0.25,
    )


def selection(profile=None):
    return BaselineSelection(
        baseline_id="baseline-2026q1", selection_method="run_id",
        selected_value="run-123", profile_digest=None if profile is None else canonical_profile_digest(profile),
    )


def test_explicit_selection_policy_and_artifact_uri_validation():
    with pytest.raises(ValidationError, match="must equal profile_digest"):
        BaselineSelection(baseline_id="x", selection_method="content_digest", selected_value="0" * 64, profile_digest="1" * 64)
    with pytest.raises(ValidationError, match="credentials, query, or fragment"):
        BaselineSelection(baseline_id="x", selection_method="artifact_uri", selected_value="https://user@example.test/a?token=x", profile_digest=None)
    with pytest.raises(ValidationError):
        BaselineComparisonPolicy(group_proportion_delta=True, missingness_rate_delta=.1, score_quantile_delta=.1, outcome_proportion_delta=.1)


def test_missing_baseline_uses_stable_current_owned_manifest_and_reference_closure():
    current = validate_audit_data(frame(), config())
    result = compare_profiles(current, config(), None, None, selection(), policy())
    assert result.status == "unavailable"
    assert len(result.checks) == 26
    assert {check.status for check in result.checks} == {"unavailable"}
    assert result.flags == ()
    assert result.issues[0].evidence.source_check_ids == tuple(check.check_id for check in result.checks)
    assert all(check.reason_code == "baseline_unavailable" for check in result.checks)


def test_digest_mismatch_is_all_or_nothing_incompatible():
    current = validate_audit_data(frame(), config())
    baseline = validate_audit_data(frame(shifted=True), config())
    bad = BaselineSelection(baseline_id="b", selection_method="run_id", selected_value="r", profile_digest="0" * 64)
    result = compare_profiles(current, config(), baseline, config(), bad, policy())
    assert result.status == "incompatible"
    assert {check.status for check in result.checks} == {"incompatible"}
    assert {check.reason_code for check in result.checks} == {"baseline_digest_mismatch"}
    assert result.flags == ()


@pytest.mark.parametrize(
    ("field", "baseline_value"),
    [
        ("population_definition", "Declined applications"),
        ("sampling_definition", "Random sample of eligible records"),
    ],
)
def test_population_scope_mismatch_is_all_or_nothing_incompatible(field, baseline_value):
    current_config = config()
    baseline_config = config(**{field: baseline_value})
    current = validate_audit_data(frame(), current_config)
    baseline = validate_audit_data(frame(), baseline_config)

    result = compare_profiles(
        current,
        current_config,
        baseline,
        baseline_config,
        selection(baseline.profile),
        policy(),
    )

    assert result.status == "incompatible"
    assert {check.status for check in result.checks} == {"incompatible"}
    assert {check.reason_code for check in result.checks} == {"analysis_semantics_mismatch"}
    assert result.flags == ()


def test_numeric_boundaries_versions_zero_groups_and_flag_evidence():
    current = validate_audit_data(frame(shifted=True), config(dataset_version="data-v2"))
    baseline = validate_audit_data(frame(), config())
    result = compare_profiles(current, config(dataset_version="data-v2"), baseline, config(), selection(baseline.profile), policy())
    assert result.status == "partially_completed"  # configured group C has no grouped denominator
    assert any(check.reason_code == "zero_group_sample" for check in result.checks)
    codes = {flag.code for flag in result.flags}
    assert {"group_composition_changed", "score_distribution_changed", "outcome_distribution_changed", "dataset_version_changed"} <= codes
    check_by_id = {check.check_id: check for check in result.checks}
    for flag in result.flags:
        source = check_by_id[flag.source_check_id]
        assert (flag.statistic, flag.threshold, flag.current_value, flag.baseline_value) == (source.statistic, source.threshold, source.current_value, source.baseline_value)
    assert any(flag.threshold == 0.25 for flag in result.flags)  # inclusive equality flags


def test_attach_is_immutable_once_only_and_round_trips_with_report_mapper():
    current = validate_audit_data(frame(), config())
    comparison = compare_profiles(current, config(), current, config(), selection(current.profile), policy())
    attached = attach_baseline_comparison(current, comparison)
    assert current.comparison is None
    assert attached.comparison == comparison
    assert LayeredValidationResult.model_validate_json(attached.model_dump_json()) == attached
    report = to_validation_evidence(attached, exclusions=(), warnings=())
    assert report.comparison == comparison
    assert report.profile == attached.profile
    with pytest.raises(ValueError, match="already attached"):
        attach_baseline_comparison(attached, comparison)


def test_determinism_and_legacy_comparison_null_migration():
    base_frame = frame()
    current_frame = frame(shifted=True)
    baseline = validate_audit_data(base_frame, config())
    first = validate_audit_data(current_frame, config())
    second = validate_audit_data(current_frame.sample(frac=1, random_state=9), config())
    selected = selection(baseline.profile)
    one = compare_profiles(first, config(), baseline, config(), selected, policy())
    two = compare_profiles(second, config(), baseline, config(), selected, policy())
    assert one.model_dump_json() == two.model_dump_json()
    legacy = first.model_dump(mode="json")
    legacy.pop("comparison")
    migrated = LayeredValidationResult.model_validate(legacy)
    assert migrated.comparison is None
    assert json.loads(migrated.model_dump_json())["comparison"] is None
