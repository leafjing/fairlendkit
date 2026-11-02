from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_NOTES = REPO_ROOT / "docs" / "releases" / "v0.1.0rc1.md"
PR_GATE = REPO_ROOT / "scripts" / "verify_release_pr_gate.sh"


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _run_gate(
    tmp_path: Path,
    *,
    main_sha: str = "reviewed-main-sha",
    changed_field: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    payload = {
        "headRefOid": "reviewed-release-sha",
        "baseRefOid": "reviewed-main-sha",
        "reviewDecision": "APPROVED",
        "mergeStateStatus": "CLEAN",
    }
    if changed_field is not None:
        payload[changed_field] = "DRIFTED"

    _write_executable(
        bin_dir / "git",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\\n' "$*" >> {calls}
test "$1 $2" = "rev-parse origin/main"
printf '%s\\n' {main_sha!r}
""",
    )
    _write_executable(
        bin_dir / "gh",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'gh %s\\n' "$*" >> {calls}
case "$1 $2" in
  "pr checks") exit 0 ;;
  "pr view") printf '%s\\n' {json.dumps(payload)!r} ;;
  "pr merge") exit 0 ;;
  *) exit 97 ;;
esac
""",
    )
    for command in ("merge", "tag"):
        _write_executable(
            bin_dir / command,
            f"#!/usr/bin/env bash\nprintf '{command} %s\\n' \"$*\" >> {calls}\n",
        )

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "PR": "123",
        "REVIEWED_MAIN_SHA": "reviewed-main-sha",
        "REVIEWED_RELEASE_SHA": "reviewed-release-sha",
    }
    result = subprocess.run(
        ["bash", str(PR_GATE)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result, calls


def _calls(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_release_notes_call_the_single_production_merge_gate() -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    command_block = text.split("```bash\n", 1)[1].split("\n```", 1)[0]
    assert command_block.startswith("set -euo pipefail\n")
    assert command_block.count("bash scripts/verify_release_pr_gate.sh") == 1
    assert "gh pr checks" not in command_block
    assert "gh pr view" not in command_block
    assert "gh pr merge" not in command_block


def test_first_oid_failure_stops_all_side_effect_stubs(tmp_path: Path) -> None:
    result, call_log = _run_gate(tmp_path, main_sha="DRIFTED")
    calls = _calls(call_log)
    assert result.returncode != 0
    assert calls == ["git rev-parse origin/main"]
    assert not any("pr merge" in call for call in calls)
    assert not any(call.startswith("merge ") for call in calls)
    assert not any(call.startswith("tag ") for call in calls)


@pytest.mark.parametrize(
    "changed_field",
    ("headRefOid", "baseRefOid", "reviewDecision", "mergeStateStatus"),
)
def test_each_pr_field_drift_stops_before_merge(
    tmp_path: Path, changed_field: str
) -> None:
    result, call_log = _run_gate(tmp_path, changed_field=changed_field)
    calls = _calls(call_log)
    assert result.returncode != 0
    assert any(call.startswith("gh pr checks ") for call in calls)
    assert any(call.startswith("gh pr view ") for call in calls)
    assert not any(call.startswith("gh pr merge ") for call in calls)
    assert not any(call.startswith("merge ") for call in calls)
    assert not any(call.startswith("tag ") for call in calls)


def test_matching_state_runs_checks_and_merges_exactly_once(tmp_path: Path) -> None:
    result, call_log = _run_gate(tmp_path)
    calls = _calls(call_log)
    assert result.returncode == 0, result.stderr
    assert len([call for call in calls if call.startswith("gh pr checks ")]) == 1
    assert len([call for call in calls if call.startswith("gh pr view ")]) == 1
    merge_calls = [call for call in calls if call.startswith("gh pr merge ")]
    assert merge_calls == [
        "gh pr merge 123 --merge --delete-branch=false "
        "--match-head-commit reviewed-release-sha"
    ]
    assert not any(call.startswith("merge ") for call in calls)
    assert not any(call.startswith("tag ") for call in calls)
