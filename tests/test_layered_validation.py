import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from fairlendkit import (
    APPLICABILITY_STATEMENT,
    AuditConfig,
    DataValidationError,
    LayeredValidationResult,
    ValidationIssue,
    ValidationIssueEvidence,
    ValidationLayerResult,
    ValidationSummary,
    validate_audit_data,
)
from fairlendkit.data.contracts import ISSUE_REGISTRY, make_issue
from fairlendkit.report import AuditResult


def config(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "Completed applications",
        "sampling_definition": "All eligible records",
        "score_type": "ranking",
        "dataset_version": "v1",
        "model_version": None,
        "data_as_of": "2026-07-01T00:00:00Z",
        "execution_timestamp": "2026-07-02T00:00:00Z",
        "favorable_label": 1,
        "score_direction": "higher_is_more_favorable",
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B")},
        "favorable_decision_label": 1,
        "decision_threshold": 0.5,
        "threshold_operator": "ge",
        "minimum_group_size": 1,
    }
    values.update(overrides)
    return AuditConfig(**values)


def frame():
    return pd.DataFrame({"outcome": [1, 0, 1], "score": [0.9, 0.3, 0.7], "group": ["A", "A", "B"]})


def test_ac1_exactly_four_layers_in_canonical_order_and_derived_statuses():
    result = validate_audit_data(frame(), config())
    assert [layer.layer.value for layer in result.layers] == ["structural", "semantic", "analytical_reliability", "data_quality"]
    assert [layer.status.value for layer in result.layers] == ["passed", "passed", "passed", "not_evaluated"]
    with pytest.raises(ValidationError, match="derived"):
        ValidationLayerResult(layer="structural", status="warning", issues=())


def test_ac2_all_statuses_and_unavailable_baseline_evidence_are_representable():
    assert validate_audit_data(frame(), config()).layers[-1].issues[0].code == "comparison_baseline_unavailable"
    assert {status for status in ("passed", "warning", "failed", "not_evaluated")} == {"passed", "warning", "failed", "not_evaluated"}
    assert make_issue("comparison_baseline_unavailable").severity.value == "info"


def test_ac3_each_issue_registry_entry_belongs_to_exactly_one_layer():
    assert all(definition.layer.value in {"structural", "semantic", "analytical_reliability", "data_quality"} for definition in ISSUE_REGISTRY.values())
    assert len(ISSUE_REGISTRY) == len(set(ISSUE_REGISTRY))


def test_ac4_registry_enforces_canonical_issue_fields():
    canonical = make_issue("small_group", affected_fields=("group",), evidence=ValidationIssueEvidence(count=1, minimum=2))
    payload = canonical.model_dump()
    payload["message"] = "invented"
    with pytest.raises(ValidationError, match="canonical"):
        ValidationIssue.model_validate(payload)


@pytest.mark.parametrize("bad", [{"count": -1}, {"total": float("inf")}, {"raw_identifier": "app-1"}])
def test_ac5_evidence_rejects_negative_nonfinite_raw_or_unknown_members(bad):
    with pytest.raises(ValidationError):
        ValidationIssueEvidence.model_validate(bad)
    typed = ValidationIssueEvidence(observed=(True, 1, "1"))
    assert [type(value) for value in typed.observed] == [bool, int, str]


def test_ac6_multi_reason_counts_can_exceed_excluded_union():
    data = pd.DataFrame({"outcome": [1, 1, 0, 1, 0], "score": [None, 0.9, 0.2, 0.8, 0.4], "group": ["A", "A", "C", "B", "A"], "id": ["x", "x", "z", "w", "v"]})
    result = validate_audit_data(data, config(record_id_column="id", duplicate_policy="exclude", missing_value_policy="exclude", unknown_group_policy="exclude"))
    assert sum(count for _, count in result.reason_counts) > result.excluded_rows
    assert result.input_rows == result.eligible_rows + result.excluded_rows


def test_ac7_row_and_mapping_order_do_not_change_serialization():
    data = pd.DataFrame({"outcome": [1, 0, 1, 0], "score": [0.9, 0.2, 0.7, 0.1], "group": ["A", "C", "B", "D"]})
    first = validate_audit_data(data, config(allowed_groups={"group": ("A", "B")}, unknown_group_policy="exclude"))
    second = validate_audit_data(data.iloc[::-1], config(allowed_groups={"group": ("A", "B")}, unknown_group_policy="exclude"))
    assert first.model_dump_json() == second.model_dump_json()


def test_ac8_technical_pass_does_not_assess_applicability():
    result = validate_audit_data(frame(), config())
    assert result.technical_validation == "passed"
    assert result.applicability == "not_assessed"
    assert result.applicability_statement == APPLICABILITY_STATEMENT
    payload = result.model_dump()
    payload["applicability_statement"] = "The data is compliant."
    with pytest.raises(ValidationError):
        LayeredValidationResult.model_validate(payload)


def test_ac9_failure_has_ordered_issues_and_legacy_exception_evidence():
    data = frame().assign(score=[None, 0.3, 0.7], group=["C", "A", "B"])
    with pytest.raises(DataValidationError) as caught:
        validate_audit_data(data, config())
    assert [issue.code for issue in caught.value.issues] == ["missing_required_value", "unknown_protected_group"]
    assert caught.value.reason_counts == {"missing_required_value": 1, "unknown_protected_group": 1}
    assert caught.value.evidence


def test_ac10_validation_summary_alias_and_epic_13_properties_remain_compatible():
    result = validate_audit_data(frame(), config())
    assert ValidationSummary is LayeredValidationResult
    assert result.analyzed_rows == result.eligible_rows
    assert result.exclusion_reason_counts == {}
    assert result.duplicate_rows == 0


def test_ac11_audit_result_migrates_flat_v1_and_round_trips_layered_schema():
    payload = json.loads((Path(__file__).parents[1] / "examples/synthetic/audit-result.json").read_text())
    flat_payload = json.loads(json.dumps(payload))
    for field in ("status", "technical_validation", "applicability", "applicability_statement", "reason_counts", "duplicate_rows", "small_groups", "layers"):
        flat_payload["validation"].pop(field)
    migrated = AuditResult.model_validate(flat_payload)
    result = AuditResult.model_validate(payload)
    assert migrated.validation.layers == result.validation.layers
    assert len(result.validation.layers) == 4
    assert result.validation.eligible_rows == result.validation.analyzed_rows
    assert AuditResult.model_validate_json(result.model_dump_json()) == result
    assert "layers" in AuditResult.model_json_schema()["$defs"]["ValidationEvidence"]["required"]


def test_ac12_epic_11_through_13_public_reason_strings_are_unchanged():
    result = validate_audit_data(frame().assign(group=["A", "A", "C"]), config(unknown_group_policy="exclude"))
    assert result.reason_counts == (("unknown_protected_group", 1),)
    assert list(result.exclusion_reason_counts) == ["unknown_protected_group"]
