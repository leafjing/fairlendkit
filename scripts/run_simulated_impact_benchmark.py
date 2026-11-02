#!/usr/bin/env python3
"""Generate canonical JSON for the fixed simulated impact benchmark."""

import argparse
from pathlib import Path

from fairlendkit.research.simulated_impact_benchmark import run_benchmark


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_benchmark().canonical_json()
    if args.output is not None:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
