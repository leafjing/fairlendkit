from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_NOTES = REPO_ROOT / "docs" / "releases" / "v0.1.0rc1.md"


def _run_bash(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_release_plan_is_fail_closed_after_first_oid_failure(tmp_path: Path) -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    command_block = text.split("```bash\n", 1)[1].split("\n```", 1)[0]
    assert command_block.startswith("set -euo pipefail\n")

    marker = tmp_path / "marker-must-not-run"
    merge_marker = tmp_path / "merge-must-not-run"
    tag_marker = tmp_path / "tag-must-not-run"
    result = _run_bash(
        f"""
set -euo pipefail
merge_stub() {{ touch {merge_marker}; }}
tag_stub() {{ touch {tag_marker}; }}
test actual-main-oid = reviewed-main-oid
touch {marker}
merge_stub
tag_stub
""",
        tmp_path,
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
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    for field in ("headRefOid", "baseRefOid", "reviewDecision", "mergeStateStatus"):
        assert f"jq -r .{field}" in text

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
PR_STATE={json.dumps(json.dumps(payload))}
test "$(printf '%s' "$PR_STATE" | jq -r .headRefOid)" = reviewed-release-sha
test "$(printf '%s' "$PR_STATE" | jq -r .baseRefOid)" = reviewed-main-sha
test "$(printf '%s' "$PR_STATE" | jq -r .reviewDecision)" = APPROVED
test "$(printf '%s' "$PR_STATE" | jq -r .mergeStateStatus)" = CLEAN
touch {marker}
""",
        tmp_path,
    )

    assert result.returncode != 0, changed_field
    assert not marker.exists(), changed_field


def test_matching_pr_identity_fields_reach_merge_stub(tmp_path: Path) -> None:
    payload = {
        "headRefOid": "reviewed-release-sha",
        "baseRefOid": "reviewed-main-sha",
        "reviewDecision": "APPROVED",
        "mergeStateStatus": "CLEAN",
    }
    marker = tmp_path / "merge-ran"
    result = _run_bash(
        f"""
set -euo pipefail
PR_STATE={json.dumps(json.dumps(payload))}
test "$(printf '%s' "$PR_STATE" | jq -r .headRefOid)" = reviewed-release-sha
test "$(printf '%s' "$PR_STATE" | jq -r .baseRefOid)" = reviewed-main-sha
test "$(printf '%s' "$PR_STATE" | jq -r .reviewDecision)" = APPROVED
test "$(printf '%s' "$PR_STATE" | jq -r .mergeStateStatus)" = CLEAN
touch {marker}
""",
        tmp_path,
    )

    assert result.returncode == 0
    assert marker.is_file()
