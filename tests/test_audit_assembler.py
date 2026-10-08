from pathlib import Path

import pandas as pd
import pytest

from fairlendkit import AuditConfig, AuditResultV2, run_audit
from fairlendkit.report import AuditResultV1_0, migrate_audit_result_v1_0


def config(**changes):
    values = dict(
        outcome_column="outcome", score_column="score",
        population_definition="Completed applications", sampling_definition="All records",
        score_type="probability", dataset_version="data-v1", model_version="model-v1",
        data_as_of="2026-07-01T00:00:00Z", execution_timestamp="2026-07-02T00:00:00Z",
        favorable_label=1, score_direction="higher_is_more_favorable",
        protected_attributes=("group",), reference_groups={"group": "A"},
        allowed_groups={"group": ("A", "B")}, favorable_decision_label=1,
        decision_threshold=0.5, threshold_operator="ge", minimum_group_size=1,
        bootstrap_resamples=5, minimum_valid_resamples=1,
    )
    values.update(changes)
    return AuditConfig(**values)


def frame():
    return pd.DataFrame({
        "outcome": [1, 0, 1, 0, 1, 0],
        "score": [0.9, 0.7, 0.8, 0.4, 0.6, 0.1],
        "group": ["A", "A", "A", "B", "B", "B"],
    })


def test_run_audit_assembles_deterministic_schema_v2_without_mutation():
    data = frame()
    original = data.copy(deep=True)
    first = run_audit(data, config())
    second = run_audit(data, config())

    assert isinstance(first, AuditResultV2)
    assert first.schema_version == "2.0"
    assert first.model_dump_json() == second.model_dump_json()
    assert first.practitioner_review_notes == ()
    assert first.observed_metrics
    assert all(item.reliability != "not_assessed" for item in first.observed_metrics)
    pd.testing.assert_frame_equal(data, original)


def test_public_api_rejects_wrong_types_before_work():
    with pytest.raises(TypeError, match="pandas DataFrame"):
        run_audit([], config())
    with pytest.raises(TypeError, match="AuditConfig"):
        run_audit(frame(), {})


def test_migration_rejects_non_v1_and_adds_absent_evidence_markers():
    legacy = AuditResultV1_0.model_validate_json((Path(__file__).parents[1] / "examples" / "synthetic" / "audit-result.json").read_text())
    migrated = migrate_audit_result_v1_0(legacy.model_dump(mode="json"))
    assert migrated.schema_version == "2.0"
    assert all(item.reliability == "not_assessed" for item in migrated.observed_metrics)
    assert all(item.affected_metric_keys == () for item in migrated.limitations)
    with pytest.raises(Exception):
        migrate_audit_result_v1_0(migrated.model_dump(mode="json"))
