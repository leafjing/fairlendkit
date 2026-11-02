import json
import subprocess
import sys
from pathlib import Path

import pytest

from fairlendkit.research.fairness_interop import (
    PACKAGE_IDENTITIES,
    SAMPLE_ROWS,
    build_interop_artifact,
    sha256_json,
)


ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "docs" / "artifacts" / "fairlearn-aequitas-interop-spike-v1.json"


def test_fixed_sample_and_fairlendkit_metrics_are_reproducible():
    artifact = build_interop_artifact()
    assert artifact["input"]["row_count"] == 8
    assert artifact["input"]["sha256"] == sha256_json(SAMPLE_ROWS)
    assert artifact["fairlendkit"]["reference"] == {
        "selection_rate": 0.75,
        "roc_auc": 1.0,
    }
    assert artifact["fairlendkit"]["comparison"] == {
        "selection_rate": 0.5,
        "roc_auc": 0.75,
    }
    assert artifact["fairlendkit"]["directed_comparison_to_reference"] == {
        "adverse_impact_ratio": 2 / 3,
        "selection_rate_difference": -0.25,
    }


@pytest.mark.parametrize("tool", ["fairlearn", "aequitas"])
def test_not_executed_tools_fail_closed(tool):
    artifact = build_interop_artifact()
    record = artifact["external_execution"][tool]
    assert record["execution_status"] == "not_executed"
    assert record["reason_code"] == "external_not_executed"
    assert record["normalized_values"] is None
    assert record["value_match"] is None
    assert artifact["constraint_status"] == "failed"
    assert artifact["comparisons_emitted"] is False
    assert artifact["candidate_copy_status"] == "locked_research_only"
    assert artifact["match_total"] is None
    assert artifact["mismatch_total"] is None
    assert artifact["not_comparable_total"] is None
    assert artifact["execution_failure_total"] is None
    assert all(value is None for value in artifact["comparison_totals"].values())


def test_package_identity_is_pinned_but_not_claimed_verified():
    artifact = build_interop_artifact()
    for tool, identity in PACKAGE_IDENTITIES.items():
        record = artifact["external_execution"][tool]
        assert record["expected_package_identity"] == identity
        assert record["identity_verified"] is False
        assert record["command"][-2:] == ["--input", "fixed-synthetic-v1"]
        assert record["command_status"] == "planned_not_executed"
        assert record["exit_status"] is None
        assert record["stdout_sha256"] is None
        assert record["stderr_sha256"] is None
        assert record["started_at_utc"] is None
        assert record["ended_at_utc"] is None


def test_dependency_identity_mismatch_and_execution_failure_emit_no_comparisons():
    mismatch = build_interop_artifact(
        fairlearn_status="dependency_identity_mismatch"
    )
    assert mismatch["reason_code"] == "dependency_identity_mismatch"
    failed = build_interop_artifact(aequitas_status="execution_failed")
    assert failed["external_execution"]["aequitas"]["reason_code"] == (
        "external_execution_failed"
    )
    assert failed["reason_code"] == "external_execution_failed"
    for artifact in (mismatch, failed):
        assert artifact["comparisons_emitted"] is False
        assert all(value is None for value in artifact["comparison_totals"].values())
        assert not any(
            record["value_match"] is not None
            for record in artifact["external_execution"].values()
        )


def test_forged_success_without_raw_output_remains_failed():
    artifact = build_interop_artifact(
        fairlearn_status="execution_succeeded",
        aequitas_status="execution_succeeded",
    )
    assert artifact["constraint_status"] == "failed"
    assert artifact["reason_code"] == "external_output_invalid"
    assert artifact["comparisons_emitted"] is False
    assert all(value is None for value in artifact["comparison_totals"].values())


def test_auc_contract_cases_cover_constant_weighted_and_undefined_paths():
    cases = {
        case["case_id"]: case
        for case in build_interop_artifact()["fairlendkit"]["auc_contract_cases"]
    }
    assert cases["constant_two_class_unweighted"]["value"] == 0.5
    assert cases["constant_two_class_unweighted"]["status"] == "defined"
    assert cases["constant_two_class_weighted"]["value"] == 0.5
    assert cases["mixed_ties"]["value"] == pytest.approx(0.75)
    assert cases["single_class"]["reason_code"] == "no_unfavorable_outcomes"
    assert cases["zero_unfavorable_class_weight"]["reason_code"] == (
        "zero_unfavorable_outcome_weight"
    )
    assert cases["empty_sample"]["reason_code"] == "empty_population"
    assert cases["invalid_score"]["reason_code"] == "invalid_score"
    assert all(cases[name]["value"] is None for name in (
        "single_class", "zero_unfavorable_class_weight", "empty_sample", "invalid_score"
    ))


def test_aequitas_auc_is_structured_metric_not_supported():
    auc = build_interop_artifact()["metric_support"]["roc_auc"]
    assert auc["aequitas"] == {
        "api": None,
        "support_status": "metric_not_supported",
        "execution_status": "not_executed",
        "normalized_value": None,
        "value_match": None,
        "reason_code": "metric_not_supported",
    }
    assert auc["fairlearn"]["normalized_value"] is None
    assert auc["fairlearn"]["value_match"] is None


def test_eight_machine_readable_acceptance_rules_are_present():
    rules = build_interop_artifact()["acceptance_rules"]
    assert len(rules) == 8
    assert len(set(rules)) == 8


def test_committed_artifact_matches_builder_exactly():
    assert json.loads(ARTIFACT.read_text(encoding="utf-8")) == build_interop_artifact()


def test_cli_regenerates_committed_artifact(tmp_path):
    output = tmp_path / "artifact.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_fairness_interop_spike.py"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        check=True,
    )
    assert output.read_bytes() == ARTIFACT.read_bytes()
