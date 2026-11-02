import json
from pathlib import Path

import pytest

from fairlendkit.research.simulated_impact_benchmark import (
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
    assert result.input_sha256 == "6eae1134ac5986dd53ba6baba01e339d66bba4bbdfeac378e757167e82ba77a9"
    assert result.covered_applicants == 6329
    assert result.baseline.approvals == 4351
    assert result.tool.approvals == 4598
    assert result.approval_increment == 247
    assert result.credit_increment == 2731500
    assert result.average_incremental_credit == pytest.approx(2_731_500 / 247)


def test_metrics_are_directly_recomputed_from_rows_and_decisions():
    rows = generate_simulated_applicants()
    baseline = policy_metrics(rows, baseline_decisions(rows))
    tool = policy_metrics(rows, tool_decisions(rows))
    assert tool.approvals - baseline.approvals == 247
    assert tool.approved_credit - baseline.approved_credit == 2_731_500
    assert baseline.approved_bad_rate == pytest.approx(0.34934497816593885)
    assert tool.approved_bad_rate == pytest.approx(0.34145280556763813)
    assert baseline.adverse_impact_ratio == pytest.approx(0.7830240080470594)
    assert tool.adverse_impact_ratio == pytest.approx(0.7996940012359449)


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
        "tool.approved_credit - baseline.approved_credit"
    )
    assert payload["runtime_environment"]["timer"] == "time.perf_counter_ns"
    assert payload["scenario_id"] == "fairlendkit-sim-impact-v1"
    assert payload["analyst_effort_scenario"]["baseline_person_hours"] == 80
    assert payload["analyst_effort_scenario"]["tool_assisted_person_hours"] == 32
    assert payload["review_coverage_scenario"]["baseline_people"] == 2000
    assert payload["review_coverage_scenario"]["tool_people"] == 10000
    assert payload["risk_constraint"]["passed"] is True
    assert payload["constraint_status"] == "passed"
    assert payload["reason_code"] == "constraints_passed"
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
