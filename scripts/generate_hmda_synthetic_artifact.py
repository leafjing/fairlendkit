#!/usr/bin/env python3
"""Generate the deterministic, research-locked synthetic HMDA evidence artifact."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

from fairlendkit.research.hmda_ca_2024 import (
    SourceEvidence, analyze_frame, configuration_sha256, success_artifact,
    write_json_artifact,
)


def synthetic_rows(per_cell: int = 300) -> pd.DataFrame:
    rows = []
    for group, ethnicity in (("focal", "Hispanic or Latino"), ("reference", "Not Hispanic or Latino")):
        for income in (25, 75, 125, 200, 300):
            for loan_amount in (75000, 200000, 400000, 600000):
                for index in range(per_cell):
                    rows.append({
                        "activity_year": "2024", "lei": f"LEI{index:017d}", "state_code": "CA",
                        "county_code": "06001" if ((index % 4 != 0) if group == "focal" else (index % 4 == 0)) else "06013", "census_tract": "06001000100",
                        "action_taken": "1" if (index * 37) % 100 < ((65 if ((index % 4 != 0) if group == "focal" else (index % 4 == 0)) else 45) + (5 if group == "focal" else 0)) else "3",
                        "loan_type": "1", "lien_status": "1", "loan_purpose": "1", "occupancy_type": "1",
                        "construction_method": "1", "total_units": "1", "loan_amount": str(loan_amount),
                        "income": str(income), "debt_to_income_ratio": "<20%" if index % 2 == 0 else "40",
                        "combined_loan_to_value_ratio": "50" if (index // 2) % 2 == 0 else "85",
                        "property_value": str(loan_amount + 100000 + index * index * 10),
                        "loan_term": str(120 + (index * 7) % 360),
                        "applicant_age": ("<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74")[index % 7],
                        "derived_ethnicity": ethnicity,
                        "derived_race": "Black or African American" if group == "focal" else "White",
                        "derived_sex": "Female" if group == "focal" else "Male",
                    })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=5)
    args = parser.parse_args()
    frame = synthetic_rows()
    csv_bytes = frame.to_csv(index=False).encode()
    estimands, flow = analyze_frame(frame, bootstrap_replicates=args.bootstrap_replicates)
    source = SourceEvidence(
        "synthetic://generate_hmda_synthetic_artifact.synthetic_rows", len(csv_bytes),
        hashlib.sha256(csv_bytes).hexdigest(), "generated-in-memory.csv", len(csv_bytes),
        hashlib.sha256(",".join(frame.columns).encode()).hexdigest(), tuple(frame.columns), len(frame), 0,
        hashlib.sha256("".join(map(str, range(len(frame)))).encode()).hexdigest(),
    )
    command = [sys.executable, "scripts/generate_hmda_synthetic_artifact.py", "--output", args.output,
               "--generated-at-utc", args.generated_at_utc, "--bootstrap-replicates", str(args.bootstrap_replicates)]
    artifact = success_artifact(
        source, estimands, flow, configuration_sha256=configuration_sha256("docs/research/hmda"),
        command=command, generated_at_utc=args.generated_at_utc,
    )
    write_json_artifact(artifact, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
