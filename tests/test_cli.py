from __future__ import annotations

import json
from pathlib import Path

import pytest

from fairlendkit import AuditResultV2
from fairlendkit.cli import EXIT_INPUT, EXIT_OUTPUT, EXIT_USAGE, main


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "data.csv"
    rows = ["outcome,score,decision,group"]
    for group in ("A", "B"):
        for outcome, score, decision in (
            (1, 0.9, 1),
            (0, 0.8, 1),
            (1, 0.2, 0),
            (0, 0.1, 0),
        ):
            rows.extend(f"{outcome},{score},{decision},{group}" for _ in range(10))
    data.write_text("\n".join(rows) + "\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "outcome_column": "outcome",
                "score_column": "score",
                "population_definition": "CLI integration fixture",
                "sampling_definition": "Two fixed rows",
                "score_type": "probability",
                "dataset_version": "fixture-1",
                "model_version": "fixture-1",
                "data_as_of": "2026-01-01T00:00:00Z",
                "execution_timestamp": "2026-01-02T00:00:00Z",
                "favorable_label": 1,
                "score_direction": "higher_is_more_favorable",
                "protected_attributes": ["group"],
                "reference_groups": {"group": "A"},
                "allowed_groups": {"group": ["A", "B"]},
                "favorable_decision_label": 1,
                "decision_column": "decision",
                "duplicate_policy": "allow",
                "minimum_group_size": 1,
                "bootstrap_resamples": 2,
                "minimum_valid_resamples": 1,
            }
        ),
        encoding="utf-8",
    )
    return data, config


def test_cli_writes_canonical_schema_2_json(tmp_path, capsys):
    data, config = _write_inputs(tmp_path)
    output = tmp_path / "reports"

    assert main(["audit", "--data", str(data), "--config", str(config), "--output", str(output)]) == 0

    payload = (output / "audit-result.json").read_bytes()
    assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
    result = AuditResultV2.model_validate_json(payload)
    assert result.schema_version == "2.0"
    assert capsys.readouterr().err == ""


def test_cli_refuses_existing_target_without_overwrite(tmp_path, capsys):
    data, config = _write_inputs(tmp_path)
    output = tmp_path / "reports"
    output.mkdir()
    target = output / "audit-result.json"
    target.write_text("keep me", encoding="utf-8")

    assert main(["audit", "--data", str(data), "--config", str(config), "--output", str(output)]) == EXIT_OUTPUT
    assert target.read_text(encoding="utf-8") == "keep me"
    assert "use --overwrite" in capsys.readouterr().err


def test_cli_reports_input_failure_without_record_data_or_traceback(tmp_path, capsys):
    _, config = _write_inputs(tmp_path)
    missing = tmp_path / "secret-customer-row.csv"

    assert main(["audit", "--data", str(missing), "--config", str(config), "--output", str(tmp_path / "out")]) == EXIT_INPUT
    error = capsys.readouterr().err
    assert "input could not be read or parsed" in error
    assert "secret-customer-row" not in error
    assert "Traceback" not in error


def test_cli_usage_error_is_stable():
    with pytest.raises(SystemExit) as raised:
        main(["audit"])
    assert raised.value.code == EXIT_USAGE
