#!/usr/bin/env python3
"""Produce raw-only Paper 2 smoke resource evidence; never run experiment analysis."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from fairlendkit.research.paper2.execution import (
    build_manifest,
    host_resource_capacity,
    validate_resource_preflight,
)
from fairlendkit.research.paper2.resource_benchmark import benchmark_full_smoke_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-capacity", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(repo_root)
    evidence = benchmark_full_smoke_pipeline(manifest)
    capacity = host_resource_capacity(repo_root)
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
