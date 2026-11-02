#!/usr/bin/env python3
"""Emit the fixed, dependency-free fairness interoperability spike artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fairlendkit.research.fairness_interop import build_interop_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(
        build_interop_artifact(), ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
