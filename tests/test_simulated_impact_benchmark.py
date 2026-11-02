import json
from pathlib import Path

import pytest

from fairlendkit.research.simulated_impact_benchmark import (
    ScenarioExpectations,
    baseline_decisions,
    generate_simulated_applicants,
    policy_metrics,
    run_benchmark,
    tool_decisions,
)


def test_fixed_population_and_decision_outputs_are_reproducible():
    first = generate_simulated_applicants()
    second = generate_simulated_applicants()
    assert first == second
    result = run_benchmark(repetitions=1)
    assert result.input_sha256 == "53f8e9a5aa9eb6b9b5cc5fc7f282b144b8add52b6725b1dd3aad899ab7006fc3"
    assert result.covered_applicants == 6329
    assert result.baseline.approvals == 892
    assert result.tool.approvals == 979
    assert result.approval_increment == 87
    assert result.credit_increment == 696_000
    assert result.average_incremental_credit == 8_000


def test_metrics_are_directly_recomputed_from_rows_and_decisions():
    rows = generate_simulated_applicants()
    baseline = policy_metrics(rows, baseline_decisions(rows))
    tool = policy_metrics(rows, tool_decisions(rows))
    assert tool.approvals - baseline.approvals == 87
    assert baseline.approved_bad_rate == pytest.approx(0.11883408071748879)
    assert tool.approved_bad_rate == pytest.approx(0.1205311542390194)
    assert baseline.adverse_impact_ratio == pytest.approx(0.6682109677493104)
    assert tool.adverse_impact_ratio == pytest.approx(0.7268557376172784)


def test_output_labels_simulation_and_runtime_is_measurement_only():
    result = run_benchmark(repetitions=2)
    payload = json.loads(result.canonical_json())
    assert payload["benchmark_id"] == "fairlendkit-simulated-impact-v1"
    assert payload["evidence_status"] == "simulation_not_production_evidence"
    assert payload["evidence_class"] == "simulation_not_production_evidence"
    assert "Synthetic simulation only" in payload["disclaimer"]
    assert payload["baseline_median_seconds"] >= 0
    assert payload["tool_median_seconds"] >= 0
    assert payload["policy_assumptions"]["baseline_credit_score_minimum"] == 680
    assert payload["formulas"]["credit_increment"] == (
        "approval_increment * assumed_average_credit"
    )
    assert payload["runtime_environment"]["timer"] == "time.perf_counter_ns"
    assert payload["scenario_id"] == "fairlendkit-sim-impact-v1"
    assert payload["analyst_effort_scenario"]["baseline_person_hours"] == 80
    assert payload["analyst_effort_scenario"]["tool_assisted_person_hours"] == 32
    assert payload["review_coverage_scenario"]["baseline_people"] == 2000
    assert payload["review_coverage_scenario"]["tool_people"] == 10000
    assert payload["risk_constraint"]["passed"] is False
    assert payload["risk_constraint"]["reason_code"] == (
        "impact_risk_noninferiority_failed"
    )
    assert payload["constraint_status"] == "failed"
    assert payload["reason_code"] == "impact_risk_noninferiority_failed"
    assert payload["input_file_sha256"] == payload["input_sha256"]
    assert payload["decision_set_digests"]["baseline_approved_count"] == 892
    assert payload["decision_set_digests"]["tool_approved_count"] == 979
    assert payload["scenario_expectations"]["passed"] is False
    assert payload["scenario_expectations"]["reason_code"] == (
        "impact_expectations_not_met"
    )
    assert payload["publication_gate"]["candidate_copy_status"] == (
        "locked_pending_evidence"
    )
    external_copy = payload["publication_gate"]["external_summary_candidate"]
    assert "量化影响评估（固定样本情景测算）" in external_copy
    assert "预设流程工时假设" in external_copy
    assert "分别估算为80和32人时" in external_copy
    assert "预计" in external_copy
    assert "模拟" not in external_copy
    assert "已实现" not in external_copy
    assert "87个新增批准" in external_copy
    assert "测算可支持" in external_copy
    assert "696,000美元" in external_copy
    assert "尚未经过客户生产环境试点验证" in (
        payload["publication_gate"]["external_summary_footnote"]
    )
    assert payload["publication_gate"]["external_summary_footnote"] == (
        "结果基于固定样本、流程工时和授信额度假设，尚未经过客户生产环境试点验证。"
    )
    assert payload["risk_constraint"]["allowed_absolute_tolerance"] == 0.0
    assert payload["config_summary"]["population_size"] == 10000
    assert "same deterministic" in payload["config_summary"]["evaluation_sample"]
    assert payload["group_evidence"]["tool"]["reference"]["sample_size"] > 0
    assert payload["group_evidence"]["tool"]["comparison"]["sample_size"] > 0


def test_checked_in_artifact_matches_deterministic_result():
    result = json.loads(run_benchmark().canonical_json())
    artifact = json.loads(
        Path("docs/artifacts/simulated-impact-benchmark-v1.json").read_text(
            encoding="utf-8"
        )
    )
    for runtime_field in (
        "baseline_median_seconds",
        "tool_median_seconds",
        "runtime_environment",
        "runtime_statistics",
        "generated_at_utc",
    ):
        result.pop(runtime_field)
        artifact.pop(runtime_field)
    assert artifact == result


def test_invalid_population_repetitions_and_shape_fail_closed():
    with pytest.raises(ValueError, match="population_size"):
        generate_simulated_applicants(population_size=0)
    with pytest.raises(ValueError, match="repetitions"):
        run_benchmark(repetitions=0)
    with pytest.raises(ValueError, match="equal lengths"):
        policy_metrics(generate_simulated_applicants(population_size=10), (True,))


def test_expectations_do_not_change_decisions_or_derived_results():
    canonical = run_benchmark(repetitions=1)
    changed = run_benchmark(
        repetitions=1,
        expectations=ScenarioExpectations(
            incremental_approvals=-999,
            baseline_absolute_gap=0.99,
            tool_absolute_gap=0.98,
        ),
    )
    assert changed.input_sha256 == canonical.input_sha256
    assert changed.decision_set_digests == canonical.decision_set_digests
    assert changed.baseline == canonical.baseline
    assert changed.tool == canonical.tool
    assert changed.approval_increment == canonical.approval_increment
    assert changed.credit_increment == canonical.credit_increment
    assert changed.scenario_expectations != canonical.scenario_expectations
