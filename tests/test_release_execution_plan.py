from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_NOTES = REPO_ROOT / "docs" / "releases" / "v0.1.0rc1.md"
PR_GATE = REPO_ROOT / "scripts" / "verify_release_pr_gate.sh"


def _run_bash(
    script: str,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=None if env is None else {**os.environ, **env},
    )


def _gate_env(**updates: str) -> dict[str, str]:
    values = {
        "CURRENT_MAIN_SHA": "reviewed-main-sha",
        "REVIEWED_MAIN_SHA": "reviewed-main-sha",
        "REVIEWED_RELEASE_SHA": "reviewed-release-sha",
        "PR_STATE": json.dumps(
            {
                "headRefOid": "reviewed-release-sha",
                "baseRefOid": "reviewed-main-sha",
                "reviewDecision": "APPROVED",
                "mergeStateStatus": "CLEAN",
            }
        ),
    }
    values.update(updates)
    return values


def test_release_plan_is_fail_closed_after_first_oid_failure(tmp_path: Path) -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    command_block = text.split("```bash\n", 1)[1].split("\n```", 1)[0]
    assert command_block.startswith("set -euo pipefail\n")
    gate_call = "bash scripts/verify_release_pr_gate.sh"
    assert gate_call in command_block
    assert command_block.rindex(gate_call) < command_block.index("gh pr merge")

    marker = tmp_path / "marker-must-not-run"
    merge_marker = tmp_path / "merge-must-not-run"
    tag_marker = tmp_path / "tag-must-not-run"
    result = _run_bash(
        f"""
set -euo pipefail
bash {PR_GATE}
touch {marker}
touch {merge_marker}
touch {tag_marker}
""",
        tmp_path,
        env=_gate_env(CURRENT_MAIN_SHA="drifted-main-sha"),
    )

    assert result.returncode != 0
    assert not marker.exists()
    assert not merge_marker.exists()
    assert not tag_marker.exists()


@pytest.mark.parametrize(
    "changed_field",
    ("headRefOid", "baseRefOid", "reviewDecision", "mergeStateStatus"),
)
def test_each_pr_identity_field_drift_stops_before_merge_stub(
    tmp_path: Path,
    changed_field: str,
) -> None:
    expected = {
        "headRefOid": "reviewed-release-sha",
        "baseRefOid": "reviewed-main-sha",
        "reviewDecision": "APPROVED",
        "mergeStateStatus": "CLEAN",
    }
    payload = dict(expected)
    payload[changed_field] = "DRIFTED"
    marker = tmp_path / f"merge-ran-{changed_field}"
    result = _run_bash(
        f"""
set -euo pipefail
bash {PR_GATE}
touch {marker}
""",
        tmp_path,
        env=_gate_env(PR_STATE=json.dumps(payload)),
    )

    assert result.returncode != 0, changed_field
    assert not marker.exists(), changed_field


def test_matching_pr_identity_fields_reach_merge_stub(tmp_path: Path) -> None:
    marker = tmp_path / "merge-ran"
    tag_marker = tmp_path / "tag-must-not-run-before-merge"
    result = _run_bash(
        f"""
set -euo pipefail
bash {PR_GATE}
printf x >> {marker}
""",
        tmp_path,
        env=_gate_env(),
    )

    assert result.returncode == 0
    assert marker.read_text(encoding="utf-8") == "x"
    assert not tag_marker.exists()
