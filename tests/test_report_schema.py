import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fairlendkit.report import (
    AUDIT_RESULT_SCHEMA_VERSION,
    AuditResult,
    Limitation,
    PractitionerReviewNote,
    WarningRecord,
)


@pytest.fixture()
def example_payload():
    path = (
        Path(__file__).parents[1]
        / "examples"
        / "synthetic"
        / "audit-result.json"
    )
    return json.loads(path.read_text())


def test_synthetic_example_validates_and_round_trips(example_payload):
    result = AuditResult.model_validate(example_payload)
    serialized = result.model_dump_json()

    assert AuditResult.model_validate_json(serialized) == result
    assert result.schema_version == AUDIT_RESULT_SCHEMA_VERSION
    assert result.observed_metrics[0].value.value == 0.5


def test_generated_json_schema_is_versioned_and_requires_all_sections():
    schema = AuditResult.model_json_schema()
    properties = schema["properties"]

    assert properties["schema_version"]["const"] == AUDIT_RESULT_SCHEMA_VERSION
    assert set(schema["required"]) == {
        "schema_version",
        "metadata",
        "validation",
        "observed_metrics",
        "screening_flags",
        "uncertainty",
        "limitations",
        "practitioner_review_notes",
    }


def test_result_contract_rejects_automated_compliance_field(example_payload):
    example_payload["compliance_status"] = "compliant"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AuditResult.model_validate(example_payload)


@pytest.mark.parametrize(
    "record",
    [
        lambda: WarningRecord(code="verdict", message="The model is compliant."),
        lambda: Limitation(code="verdict", detail="The policy is non-compliant."),
    ],
)
def test_automated_text_rejects_compliance_verdicts(record):
    with pytest.raises(ValidationError, match="cannot state compliance"):
        record()


def test_practitioner_notes_are_explicitly_human_authored():
    note = PractitionerReviewNote(
        author="Independent reviewer",
        recorded_at="2026-08-30T00:00:00Z",
        text="Counsel review is recorded separately from automated evidence.",
    )

    assert note.source == "practitioner"


def test_exclusion_counts_must_reconcile(example_payload):
    example_payload["validation"]["analyzed_rows"] = 3

    with pytest.raises(ValidationError, match="must equal input rows"):
        AuditResult.model_validate(example_payload)


def test_uncertainty_must_reference_known_metric(example_payload):
    example_payload["uncertainty"][0]["metric_key"] = "unknown.metric"

    with pytest.raises(ValidationError, match="unknown metric key"):
        AuditResult.model_validate(example_payload)


def test_renderer_contract_contains_no_raw_prediction_arrays():
    result_properties = AuditResult.model_json_schema()["properties"]

    assert "y_true" not in result_properties
    assert "y_score" not in result_properties
    assert "decisions" not in result_properties
    assert "weights" not in result_properties


def test_result_rejects_metric_value_outside_its_contract(example_payload):
    example_payload["observed_metrics"][0]["value"]["value"] = 1.1

    with pytest.raises(ValidationError, match="selection_rate must be within"):
        AuditResult.model_validate(example_payload)


def test_defined_metric_requires_positive_sample_count(example_payload):
    example_payload["observed_metrics"][0]["sample_count"] = 0

    with pytest.raises(ValidationError, match="sample_count zero"):
        AuditResult.model_validate(example_payload)
