import runpy
import hashlib
from pathlib import Path

from fairlendkit import AuditResult


def test_synthetic_schema_v2_example_is_executable_and_deterministic(capsys):
    runpy.run_path("examples/synthetic/run_audit.py")
    first = capsys.readouterr().out
    runpy.run_path("examples/synthetic/run_audit.py")
    second = capsys.readouterr().out

    result = AuditResult.model_validate_json(first)
    assert result.schema_version == "2.0"
    assert first == second
    expected = Path("examples/synthetic/audit-result-v2.sha256").read_text().strip()
    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == expected
