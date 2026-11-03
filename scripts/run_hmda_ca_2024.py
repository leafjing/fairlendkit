#!/usr/bin/env python3
"""Run frozen HMDA source admission and emit a research-locked artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from fairlendkit.research.hmda_ca_2024 import (
    admit_source_archive,
    configuration_sha256,
    fail_closed_artifact,
    write_json_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = admit_source_archive(arguments.archive)
    reasons = []
    if source.duplicate_row_count:
        reasons.append("hmda_duplicate_rows_detected")
    if not reasons:
        reasons.append("hmda_results_pipeline_not_invoked")
    artifact = fail_closed_artifact(
        source,
        reasons,
        configuration_sha256=configuration_sha256(root / "docs" / "research" / "hmda"),
    )
    write_json_artifact(artifact, arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
