#!/usr/bin/env python3
"""Produce raw-only Paper 2 smoke resource evidence; never run experiment analysis."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from fairlendkit.research.paper2.execution import (
    ExecutionWorkspace,
    benchmark_smoke_resources,
    build_manifest,
    host_resource_capacity,
    validate_resource_preflight,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-capacity", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(repo_root)
    with tempfile.TemporaryDirectory(prefix="paper2-resource-smoke-") as directory:
        workspace = ExecutionWorkspace(Path(directory).resolve(), "smoke")
        evidence = benchmark_smoke_resources(workspace, manifest)
        capacity = host_resource_capacity(workspace.root)
        if args.require_capacity:
            validate_resource_preflight(capacity, evidence)
        print(
            json.dumps(
                {"benchmark": asdict(evidence), "host_capacity": asdict(capacity)},
                sort_keys=True,
                separators=(",", ":"),
            )
        )


if __name__ == "__main__":
    main()
