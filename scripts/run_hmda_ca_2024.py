#!/usr/bin/env python3
"""Run frozen HMDA source admission and emit a research-locked artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fairlendkit.research.hmda_ca_2024 import (
    HMDAContractError,
    analyze_frame,
    admit_source_archive,
    configuration_sha256,
    fail_closed_artifact,
    load_admitted_rows,
    success_artifact,
    write_json_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = admit_source_archive(arguments.archive)
    config = configuration_sha256(root / "docs" / "research" / "hmda")
    command = ["python", "scripts/run_hmda_ca_2024.py", "--archive", arguments.archive, "--output", arguments.output]
    generated_at = None
    output_path = Path(arguments.output)
    if output_path.exists():
        try:
            generated_at = json.loads(output_path.read_text()).get("generated_at_utc")
        except (OSError, json.JSONDecodeError):
            pass
    reasons = []
    if source.duplicate_row_count:
        reasons.append("hmda_duplicate_rows_detected")
    if reasons:
        artifact = fail_closed_artifact(source, reasons, configuration_sha256=config, command=command, generated_at_utc=generated_at)
    else:
        try:
            estimands, flow = analyze_frame(load_admitted_rows(arguments.archive))
            artifact = success_artifact(source, estimands, flow, configuration_sha256=config, command=command, generated_at_utc=generated_at)
        except HMDAContractError as exc:
            artifact = fail_closed_artifact(source, [exc.reason_code], configuration_sha256=config, command=command, generated_at_utc=generated_at)
    write_json_artifact(artifact, arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
