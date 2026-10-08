import runpy
import hashlib

from fairlendkit import AuditResult


def test_synthetic_schema_v2_example_is_executable_and_deterministic(capsys):
    runpy.run_path("examples/synthetic/run_audit.py")
    first = capsys.readouterr().out
    runpy.run_path("examples/synthetic/run_audit.py")
    second = capsys.readouterr().out

    result = AuditResult.model_validate_json(first)
    assert result.schema_version == "2.0"
    assert first == second
    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == (
        "3b5c7166ed4893d808dacb2bb731e2a86ae59f5706e9ac6ec6dd58a03eca823c"
    )
