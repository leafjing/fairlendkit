import runpy
import hashlib
from pathlib import Path

from fairlendkit import AuditResult


def test_synthetic_schema_v2_example_is_executable_and_deterministic(capsys, monkeypatch):
    monkeypatch.setattr("fairlendkit.application._package_version", lambda: "0.1.0.dev0")
    runpy.run_path("examples/synthetic/run_audit.py")
    first = capsys.readouterr().out
    runpy.run_path("examples/synthetic/run_audit.py")
    second = capsys.readouterr().out

    result = AuditResult.model_validate_json(first)
    assert result.schema_version == "2.0"
    assert first == second
    oracle = Path("examples/synthetic/audit-result-v2.json").read_bytes()
    assert first.encode("utf-8") == oracle
    expected = Path("examples/synthetic/audit-result-v2.sha256").read_text().strip()
    assert hashlib.sha256(oracle).hexdigest() == expected
