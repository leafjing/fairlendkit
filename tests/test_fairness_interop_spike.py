import json
import subprocess
import sys
from pathlib import Path

from fairlendkit.research.fairness_interop import (
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


def test_external_values_are_not_invented_when_dependencies_are_not_executed():
    external = build_interop_artifact()["external_execution"]

    assert external["fairlearn"]["status"] == "not_executed_no_runtime_dependency"
    assert external["fairlearn"]["reported_values"] is None
    assert external["aequitas"]["status"] == "not_executed_no_runtime_dependency"
    assert external["aequitas"]["reported_values"] is None


def test_semantic_mapping_has_fail_closed_interop_gates():
    differences = build_interop_artifact()["semantic_differences"]

    assert {item["concept"] for item in differences} == {
        "group_selection_rate",
        "selection_rate_ratio",
        "undefined_and_constant_score_auc",
    }
    assert all(item["interop_gate"].startswith("do_not_") or item["interop_gate"].startswith("preserve_") for item in differences)


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

