"""Generate one deterministic synthetic Schema 2.0 audit result."""

import pandas as pd

from fairlendkit import AuditConfig, run_audit


data = pd.DataFrame(
    {
        "outcome": [1, 0, 1, 0, 1, 0],
        "score": [0.90, 0.70, 0.80, 0.40, 0.60, 0.10],
        "audit_group": ["reference", "reference", "reference", "comparison", "comparison", "comparison"],
    }
)

config = AuditConfig(
    outcome_column="outcome",
    score_column="score",
    population_definition="Synthetic completed applications",
    sampling_definition="All six synthetic records",
    score_type="probability",
    dataset_version="synthetic-v2",
    model_version="example-model-v1",
    data_as_of="2026-08-29T00:00:00Z",
    execution_timestamp="2026-08-30T00:00:00Z",
    favorable_label=1,
    score_direction="higher_is_more_favorable",
    protected_attributes=("audit_group",),
    reference_groups={"audit_group": "reference"},
    allowed_groups={"audit_group": ("reference", "comparison")},
    favorable_decision_label=1,
    decision_threshold=0.5,
    threshold_operator="ge",
    minimum_group_size=1,
    bootstrap_seed=7,
    bootstrap_resamples=100,
    minimum_valid_resamples=50,
)

print(run_audit(data, config).model_dump_json())
