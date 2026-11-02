#!/usr/bin/env python3
"""Print canonical JSON for the fixed simulated impact benchmark."""

from fairlendkit.research.simulated_impact_benchmark import run_benchmark


if __name__ == "__main__":
    print(run_benchmark().canonical_json())
