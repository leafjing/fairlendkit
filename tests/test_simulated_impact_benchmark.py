import json
from dataclasses import replace
from pathlib import Path

import pytest

from fairlendkit.research.simulated_impact_benchmark import (
    ScenarioExpectations,
    baseline_decisions,
    evaluate_risk_gate,
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
    assert result.input_sha256 == "cb57ee569995fbcbf61fe63202d5a37a9b4f2a738e7b8aafd0a912657ed9434f"
    assert result.covered_applicants == 6329
    assert result.baseline.approvals == 4351
    assert result.tool.approvals == 4598
    assert result.approval_increment == 247
    assert result.incremental_approvals == 247
    assert result.credit_increase_usd == 1_976_000


def test_metrics_are_directly_recomputed_from_rows_and_decisions():
    rows = generate_simulated_applicants()
    baseline = policy_metrics(rows, baseline_decisions(rows))
    tool = policy_metrics(rows, tool_decisions(rows))
    assert tool.approvals - baseline.approvals == 247
    assert baseline.approved_bad_rate == pytest.approx(0.34934497816593885)
    assert tool.approved_bad_rate == pytest.approx(0.34145280556763813)
    assert baseline.adverse_impact_ratio == pytest.approx(0.7830240080470594)
    assert tool.adverse_impact_ratio == pytest.approx(0.7996940012359449)


def test_output_labels_simulation_and_runtime_is_measurement_only():
    result = run_benchmark(repetitions=2)
    payload = json.loads(result.canonical_json())
    assert payload["benchmark_id"] == "fairlendkit-simulated-impact-v1"
    assert payload["code_commit_basis"] == "961ffbd"
    assert payload["policy_assumptions"]["code_commit_basis_definition"].startswith(
        "Git commit containing the benchmark generator"
    )
    assert payload["evidence_status"] == "simulation_not_production_evidence"
    assert payload["evidence_class"] == "simulation_not_production_evidence"
    assert "Synthetic simulation only" in payload["disclaimer"]
    assert payload["baseline_median_seconds"] >= 0
    assert payload["tool_median_seconds"] >= 0
    assert payload["policy_assumptions"]["baseline_credit_score_minimum"] == 680
    assert payload["formulas"]["credit_increase_usd"] == (
        "incremental_approvals * fixed_credit_amount_usd"
    )
    assert payload["policy_assumptions"]["fixed_credit_amount_usd"] == 8000
    assert payload["runtime_environment"]["timer"] == "time.perf_counter_ns"
    assert payload["scenario_id"] == "fairlendkit-sim-impact-v1"
    assert payload["analyst_effort_scenario"]["baseline_person_hours"] == 80
    assert payload["analyst_effort_scenario"]["tool_assisted_person_hours"] == 32
    assert payload["review_coverage_scenario"]["baseline_people"] == 2000
    assert payload["review_coverage_scenario"]["tool_people"] == 10000
    assert payload["risk_constraint"]["passed"] is True
    assert payload["risk_constraint"]["reason_code"] == (
        "impact_risk_noninferiority_passed"
    )
    assert payload["constraint_status"] == "failed"
    assert payload["reason_code"] == "scenario_expectations_not_reproduced"
    assert payload["input_file_sha256"] == payload["input_sha256"]
    assert payload["decision_set_digests"]["baseline_approved_count"] == 4351
    assert payload["decision_set_digests"]["tool_approved_count"] == 4598
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
    assert "分别估算为{{baseline_person_hours}}和{{tool_person_hours}}人时" in external_copy
    assert "预计" in external_copy
    assert "模拟" not in external_copy
    assert "已实现" not in external_copy
    assert "{{population_size}}" in external_copy
    assert "{{baseline_person_hours}}" in external_copy
    assert "247" not in external_copy
    assert "1,976,000" not in external_copy
    assert "12个" not in external_copy
    assert "5个" not in external_copy
    assert "尚未经过客户生产环境试点验证" in (
        payload["publication_gate"]["external_summary_footnote"]
    )
    assert payload["publication_gate"]["external_summary_footnote"] == (
        "结果基于固定样本、流程工时和授信额度假设，尚未经过客户生产环境试点验证。"
    )
    assert payload["risk_constraint"]["allowed_absolute_tolerance"] == 0.0
    assert payload["config_summary"]["population_size"] == 10000
    assert "same deterministic" in payload["config_summary"]["evaluation_sample"]
    assert payload["config_summary"]["outcome_label"] == (
        "bad_12m = 90+ DPD or charge-off"
    )
    assert "cross-section" not in json.dumps(payload["config_summary"])
    assert "favorable_outcome" not in json.dumps(payload["config_summary"])
    assert "requested_credit" not in json.dumps(payload["config_summary"])
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
    assert changed.credit_increase_usd == canonical.credit_increase_usd
    assert changed.scenario_expectations != canonical.scenario_expectations


def test_actual_seed_changes_config_hash_and_input_identity():
    canonical = run_benchmark(repetitions=1, seed=20261102)
    changed = run_benchmark(repetitions=1, seed=20261103)
    assert changed.seed == 20261103
    assert changed.config_sha256 != canonical.config_sha256
    assert changed.input_sha256 != canonical.input_sha256


def test_unmatured_approved_rows_are_excluded_from_risk_denominator(monkeypatch):
    rows = list(generate_simulated_applicants(population_size=20))
    approved_index = next(
        index for index, decision in enumerate(baseline_decisions(rows)) if decision
    )
    rows[approved_index] = replace(
        rows[approved_index], outcome_matured_12m=False, bad_12m=True
    )
    frozen = tuple(rows)
    monkeypatch.setattr(
        "fairlendkit.research.simulated_impact_benchmark.generate_simulated_applicants",
        lambda **_: frozen,
    )
    result = run_benchmark(population_size=20, repetitions=1)
    assert result.risk_constraint["baseline_matured_approved_count"] == (
        result.baseline.approvals - 1
    )
    assert result.risk_constraint["baseline_bad_count"] <= (
        result.risk_constraint["baseline_matured_approved_count"]
    )


def test_publication_reason_priority_and_locked_status():
    expectations_only = run_benchmark(repetitions=1)
    assert expectations_only.reason_code == "scenario_expectations_not_reproduced"
    assert expectations_only.publication_gate["candidate_copy_status"] == (
        "locked_pending_evidence"
    )
    assert "247" not in expectations_only.publication_gate["external_summary_candidate"]
    assert "1,976,000" not in expectations_only.publication_gate["external_summary_candidate"]


def test_risk_failure_takes_priority_over_expectation_failure(monkeypatch):
    monkeypatch.setattr(
        "fairlendkit.research.simulated_impact_benchmark.evaluate_risk_gate",
        lambda **_: {
            "passed": False,
            "reason_code": "impact_risk_noninferiority_failed",
        },
    )
    result = run_benchmark(repetitions=1)
    assert result.reason_code == "impact_risk_noninferiority_failed"
    assert result.constraint_status == "failed"
    assert result.publication_gate["candidate_copy_status"] == (
        "locked_pending_evidence"
    )


def test_risk_gate_fail_closed_reason_codes():
    failed = evaluate_risk_gate(
        baseline_bad_count=1,
        baseline_matured_count=10,
        tool_bad_count=2,
        tool_matured_count=10,
    )
    assert failed["passed"] is False
    assert failed["reason_code"] == "impact_risk_noninferiority_failed"

    empty = evaluate_risk_gate(
        baseline_bad_count=0,
        baseline_matured_count=0,
        tool_bad_count=0,
        tool_matured_count=10,
    )
    assert empty == {
        "passed": False,
        "reason_code": "impact_risk_denominator_empty",
    }

    invalid = evaluate_risk_gate(
        baseline_bad_count=11,
        baseline_matured_count=10,
        tool_bad_count=0,
        tool_matured_count=10,
    )
    assert invalid == {
        "passed": False,
        "reason_code": "impact_outcome_contract_invalid",
    }
