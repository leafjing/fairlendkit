from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, AuditResultV2, DataValidationError, run_audit
from fairlendkit.report import AuditResultV1_0, migrate_audit_result_v1_0


def config(**changes):
    values = dict(
        outcome_column="outcome", score_column="score",
        population_definition="Completed applications", sampling_definition="All records",
        score_type="probability", dataset_version="data-v1", model_version="model-v1",
        data_as_of="2026-07-01T00:00:00Z", execution_timestamp="2026-07-02T00:00:00Z",
        favorable_label=1, score_direction="higher_is_more_favorable",
        protected_attributes=("group",), reference_groups={"group": "A"},
        allowed_groups={"group": ("A", "B")}, favorable_decision_label=1,
        decision_threshold=0.5, threshold_operator="ge", minimum_group_size=1,
        bootstrap_resamples=5, minimum_valid_resamples=1,
    )
    values.update(changes)
    return AuditConfig(**values)


def frame():
    return pd.DataFrame({
        "outcome": [1, 0, 1, 0, 1, 0],
        "score": [0.9, 0.7, 0.8, 0.4, 0.6, 0.1],
        "group": ["A", "A", "A", "B", "B", "B"],
    })


def test_run_audit_assembles_deterministic_schema_v2_without_mutation():
    data = frame()
    original = data.copy(deep=True)
    first = run_audit(data, config())
    second = run_audit(data, config())

    assert isinstance(first, AuditResultV2)
    assert first.schema_version == "2.0"
    assert first.model_dump_json() == second.model_dump_json()
    assert first.practitioner_review_notes == ()
    assert first.observed_metrics
    assert all(item.reliability != "not_assessed" for item in first.observed_metrics)
    pd.testing.assert_frame_equal(data, original)


def test_public_api_rejects_wrong_types_before_work():
    with pytest.raises(TypeError, match="pandas DataFrame"):
        run_audit([], config())
    with pytest.raises(TypeError, match="AuditConfig"):
        run_audit(frame(), {})


def test_migration_rejects_non_v1_and_adds_absent_evidence_markers():
    legacy = AuditResultV1_0.model_validate_json((Path(__file__).parents[1] / "examples" / "synthetic" / "audit-result.json").read_text())
    migrated = migrate_audit_result_v1_0(legacy.model_dump(mode="json"))
    assert migrated.schema_version == "2.0"
    assert all(item.reliability == "not_assessed" for item in migrated.observed_metrics)
    assert all(item.affected_metric_keys == () for item in migrated.limitations)
    legacy_dump = legacy.model_dump(mode="json")
    migrated_dump = migrated.model_dump(mode="json")
    for section in ("metadata", "validation", "screening_flags", "uncertainty", "practitioner_review_notes"):
        assert migrated_dump[section] == legacy_dump[section]
    assert [item["value"] for item in migrated_dump["observed_metrics"]] == [item["value"] for item in legacy_dump["observed_metrics"]]
    assert [(item["code"], item["detail"]) for item in migrated_dump["limitations"]] == [(item["code"], item["detail"]) for item in legacy_dump["limitations"]]
    assert AuditResultV2.model_validate_json(migrated.model_dump_json()) == migrated
    with pytest.raises(ValidationError, match="Input should be '1.0'"):
        migrate_audit_result_v1_0(migrated.model_dump(mode="json"))


def test_v2_requires_new_fields_and_enforces_metric_invariants():
    payload = run_audit(frame(), config()).model_dump(mode="json")
    del payload["observed_metrics"][0]["reliability"]
    with pytest.raises(ValidationError, match="reliability"):
        AuditResultV2.model_validate(payload)

    payload = run_audit(frame(), config()).model_dump(mode="json")
    payload["observed_metrics"][0]["value"]["value"] = 2.0
    with pytest.raises(ValidationError, match="within"):
        AuditResultV2.model_validate(payload)

    payload = run_audit(frame(), config()).model_dump(mode="json")
    payload["observed_metrics"][0]["sample_count"] = 0
    with pytest.raises(ValidationError, match="positive sample_count"):
        AuditResultV2.model_validate(payload)


def test_v2_enforces_uncertainty_alias_and_canonical_order():
    payload = run_audit(frame(), config()).model_dump(mode="json")
    payload["uncertainty"][0]["lower"] = -1.0
    with pytest.raises(ValidationError, match="metric range"):
        AuditResultV2.model_validate(payload)

    payload = run_audit(frame(), config()).model_dump(mode="json")
    alias = next(item for item in payload["observed_metrics"] if item["metric"] == "demographic_parity_difference")
    alias["value"]["value"] += 0.1
    with pytest.raises(ValidationError, match="identical evidence"):
        AuditResultV2.model_validate(payload)

    payload = run_audit(frame(), config()).model_dump(mode="json")
    payload["observed_metrics"][0], payload["observed_metrics"][1] = payload["observed_metrics"][1], payload["observed_metrics"][0]
    with pytest.raises(ValidationError, match="canonical order"):
        AuditResultV2.model_validate(payload)


def test_failure_path_preserves_dataframe_exactly():
    data = frame().drop(columns="score")
    original = data.copy(deep=True)
    with pytest.raises(DataValidationError):
        run_audit(data, config())
    pd.testing.assert_frame_equal(data, original)


def test_e2e_states_flags_observed_decision_and_empty_group():
    data = frame().assign(decision=[1, 1, 1, 0, 1, 0])
    observed = run_audit(
        data,
        config(decision_threshold=None, threshold_operator=None, decision_column="decision", minimum_group_size=4),
    )
    assert any(item.reliability == "unreliable" for item in observed.observed_metrics)
    assert observed.screening_flags == ()
    assert any(item.code == "small_group" for item in observed.limitations)

    ranking = run_audit(frame(), config(score_type="ranking", allowed_groups={"group": ("A", "B", "C")}))
    brier = [item for item in ranking.observed_metrics if item.metric == "brier_score"]
    assert all(item.reliability == "not_applicable" for item in brier)
    empty = [item for item in ranking.observed_metrics if item.group and item.group.attributes.get("group") == "C"]
    assert empty and all(not item.value.is_defined for item in empty)
    assert any(flag.code == "air_below_threshold" for flag in run_audit(frame(), config()).screening_flags)


def test_e2e_semantic_reversals_and_multiple_attributes():
    baseline = run_audit(frame(), config())
    relabeled = frame().assign(outcome=["yes" if value == 1 else "no" for value in frame()["outcome"]])
    relabeled_result = run_audit(relabeled, config(favorable_label="yes", favorable_decision_label="approved"))
    assert [item.value.value for item in baseline.observed_metrics] == [item.value.value for item in relabeled_result.observed_metrics]
    reversed_score = frame().assign(score=lambda value: 1.0 - value["score"])
    lower = run_audit(reversed_score, config(score_direction="lower_is_more_favorable", decision_threshold=0.5, threshold_operator="le"))
    assert [item.value.value for item in baseline.observed_metrics] == [item.value.value for item in lower.observed_metrics]

    reversed_reference = run_audit(frame(), config(reference_groups={"group": "B"}))
    baseline_difference = next(item.value.value for item in baseline.observed_metrics if item.metric == "selection_rate_difference")
    reversed_difference = next(item.value.value for item in reversed_reference.observed_metrics if item.metric == "selection_rate_difference")
    assert baseline_difference == -reversed_difference

    data = frame().assign(region=["X", "Y", "X", "Y", "X", "Y"])
    multiple = run_audit(data, config(
        protected_attributes=("region", "group"),
        reference_groups={"region": "X", "group": "A"},
        allowed_groups={"region": ("X", "Y"), "group": ("A", "B")},
    ))
    attributes = {next(iter(item.group.attributes)) for item in multiple.observed_metrics if item.group and "__scope__" not in item.group.attributes}
    assert attributes == {"group", "region"}


def test_e2e_zero_weight_and_bootstrap_insufficiency_are_typed():
    weighted = frame().assign(weight=[1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    result = run_audit(weighted, config(sample_weight_column="weight"))
    group_b = [item for item in result.observed_metrics if item.group and item.group.attributes.get("group") == "B"]
    assert group_b and all(not item.value.is_defined for item in group_b)
    assert {item.value.undefined_reason.code for item in group_b} >= {"zero_total_weight"}

    sparse = run_audit(frame(), config(bootstrap_resamples=5, minimum_valid_resamples=5))
    insufficient = [item for item in sparse.limitations if item.code == "insufficient_valid_resamples"]
    assert insufficient
    assert all(item.affected_metric_keys for item in insufficient)


def test_e2e_sparse_class_and_precision_support_reasons_are_typed():
    sparse = frame().assign(outcome=[1, 0, 1, 0, 0, 0], score=[0.9, 0.7, 0.8, 0.4, 0.3, 0.1])
    result = run_audit(sparse, config())
    group_b = [item for item in result.observed_metrics if item.group and item.group.attributes.get("group") == "B"]
    reasons = {item.metric: item.value.undefined_reason.code for item in group_b if item.value.undefined_reason}
    assert reasons["precision"] == "no_favorable_decisions"
    assert reasons["true_positive_rate"] == "no_favorable_outcomes"
    assert reasons["roc_auc"] == "no_favorable_outcomes"
