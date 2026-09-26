import math

import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, ScoreDirection


def config_values(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "Completed applications in the review period",
        "sampling_definition": "All eligible records; no sampling",
        "score_type": "ranking",
        "dataset_version": "applications-v1",
        "model_version": None,
        "data_as_of": "2026-07-01T00:00:00Z",
        "execution_timestamp": "2026-07-02T12:30:00Z",
        "favorable_label": 1,
        "score_direction": ScoreDirection.HIGHER_IS_MORE_FAVORABLE,
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B")},
        "favorable_decision_label": 1,
        "decision_threshold": 0.5,
        "threshold_operator": "ge",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("field", ["population_definition", "sampling_definition"])
@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_run_context_definitions_must_be_non_blank(field, value):
    with pytest.raises(ValidationError):
        AuditConfig(**config_values(**{field: value}))


@pytest.mark.parametrize("field", ["dataset_version", "model_version"])
def test_versions_must_be_non_blank_or_explicitly_unavailable(field):
    with pytest.raises(ValidationError):
        AuditConfig(**config_values(**{field: "  "}))

    assert getattr(AuditConfig(**config_values(**{field: None})), field) is None


def test_score_type_is_explicit_and_closed():
    config = AuditConfig(**config_values(score_type="probability"))

    assert config.score_type == "probability"

    with pytest.raises(ValidationError):
        AuditConfig(**config_values(score_type="unknown"))


@pytest.mark.parametrize("field", ["data_as_of", "execution_timestamp"])
def test_run_context_timestamps_require_timezone(field):
    with pytest.raises(ValidationError):
        AuditConfig(**config_values(**{field: "2026-07-01T00:00:00"}))


def test_run_context_serialization_keeps_as_of_and_execution_times_distinct():
    config = AuditConfig(**config_values())
    serialized = config.model_dump(mode="json")

    assert serialized["data_as_of"] == "2026-07-01T00:00:00Z"
    assert serialized["execution_timestamp"] == "2026-07-02T12:30:00Z"
    assert serialized["data_as_of"] != serialized["execution_timestamp"]


@pytest.mark.parametrize(
    "field",
    [
        "population_definition",
        "sampling_definition",
        "score_type",
        "dataset_version",
        "model_version",
        "data_as_of",
        "execution_timestamp",
    ],
)
def test_run_context_fields_are_explicitly_required(field):
    values = config_values()
    del values[field]

    with pytest.raises(ValidationError, match="Field required"):
        AuditConfig(**values)


def test_nullable_run_context_fields_require_explicit_null_when_unavailable():
    config = AuditConfig(
        **config_values(dataset_version=None, model_version=None, data_as_of=None)
    )

    assert config.dataset_version is None
    assert config.model_version is None
    assert config.data_as_of is None


def test_score_direction_is_explicit_and_reversible():
    higher = AuditConfig(**config_values())
    lower = AuditConfig(
        **config_values(
            score_direction=ScoreDirection.LOWER_IS_MORE_FAVORABLE,
            threshold_operator="le",
        )
    )

    assert higher.score_direction != lower.score_direction


@pytest.mark.parametrize("threshold", [math.inf, -math.inf, math.nan])
def test_non_finite_threshold_is_invalid(threshold):
    with pytest.raises(ValidationError, match="decision_threshold must be finite"):
        AuditConfig(**config_values(decision_threshold=threshold))


def test_reference_group_required_for_every_protected_attribute():
    with pytest.raises(ValidationError, match="exactly one explicit value"):
        AuditConfig(
            **config_values(
                protected_attributes=("group", "region"),
                reference_groups={"group": "A"},
                allowed_groups={"group": ("A",), "region": ("north",)},
            )
        )


def test_observed_and_threshold_decisions_are_mutually_exclusive():
    with pytest.raises(ValidationError, match="exactly one"):
        AuditConfig(
            **config_values(
                decision_column="approved",
                decision_threshold=0.5,
            )
        )


def test_a_decision_source_is_required():
    with pytest.raises(ValidationError, match="exactly one"):
        AuditConfig(
            **config_values(decision_threshold=None, threshold_operator=None)
        )


def test_threshold_operator_must_match_score_direction():
    with pytest.raises(ValidationError, match="inconsistent with score_direction"):
        AuditConfig(**config_values(threshold_operator="le"))


@pytest.mark.parametrize(
    ("direction", "operator", "score", "expected"),
    [
        ("higher_is_more_favorable", "ge", 0.5, True),
        ("higher_is_more_favorable", "ge", 0.499, False),
        ("lower_is_more_favorable", "le", 0.5, True),
        ("lower_is_more_favorable", "le", 0.501, False),
    ],
)
def test_derived_decision_threshold_is_inclusive(
    direction, operator, score, expected
):
    config = AuditConfig(
        **config_values(score_direction=direction, threshold_operator=operator)
    )

    assert config.is_favorable_decision_score(score) is expected


def test_threshold_schema_records_inclusive_boundary_semantics():
    properties = AuditConfig.model_json_schema()["properties"]

    assert "score >= threshold" in properties["threshold_operator"]["description"]
    assert "score <= threshold" in properties["threshold_operator"]["description"]


@pytest.mark.parametrize(
    ("overrides", "conflicting_roles"),
    [
        ({"score_column": "outcome"}, "outcome_column, score_column"),
        (
            {
                "protected_attributes": ("score",),
                "reference_groups": {"score": "A"},
                "allowed_groups": {"score": ("A",)},
            },
            "score_column, protected_attributes[0]",
        ),
        ({"sample_weight_column": "outcome"}, "outcome_column, sample_weight_column"),
        ({"candidate_proxy_features": ("score",)}, "score_column, candidate_proxy_features[0]"),
        (
            {"candidate_proxy_features": ("proxy", "proxy")},
            "candidate_proxy_features[0], candidate_proxy_features[1]",
        ),
    ],
)
def test_columns_cannot_share_semantic_roles(overrides, conflicting_roles):
    with pytest.raises(ValidationError, match="exactly one semantic role") as error:
        AuditConfig(**config_values(**overrides))

    assert conflicting_roles in str(error.value)


def test_allowed_groups_required_for_every_protected_attribute():
    with pytest.raises(ValidationError, match="allowed_groups must contain exactly"):
        AuditConfig(
            **config_values(
                protected_attributes=("group", "region"),
                reference_groups={"group": "A", "region": "north"},
            )
        )


def test_reference_group_must_be_in_type_sensitive_allowed_groups():
    with pytest.raises(ValidationError, match="must belong to allowed_groups"):
        AuditConfig(
            **config_values(
                reference_groups={"group": True},
                allowed_groups={"group": (1,)},
            )
        )


def test_allowed_groups_reject_type_sensitive_duplicates_only():
    config = AuditConfig(
        **config_values(
            reference_groups={"group": True},
            allowed_groups={"group": (True, 1, "1")},
        )
    )

    assert config.allowed_groups["group"] == (True, 1, "1")


def test_structural_configuration_serializes_with_stable_defaults():
    config = AuditConfig(**config_values())

    assert config.model_dump(mode="json")["duplicate_policy"] == "error"
    assert config.record_id_column is None
    assert config.expected_categories == {}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"expected_categories": {"score": (1,)}}, "expected_categories keys"),
        ({"expected_categories": {"outcome": ()}}, "must not be empty"),
        ({"expected_categories": {"outcome": (1, 1)}}, "must not contain duplicates"),
        ({"expected_categories": {"outcome": (0,)}}, "favorable_label"),
        ({"expected_categories": {"group": ("B",)}}, "reference group"),
        ({"record_id_column": "score"}, "exactly one semantic role"),
    ],
)
def test_structural_configuration_rejects_invalid_contracts(overrides, message):
    with pytest.raises(ValidationError, match=message):
        AuditConfig(**config_values(**overrides))


def test_expected_categories_are_type_sensitive():
    config = AuditConfig(
        **config_values(
            favorable_label=True,
            expected_categories={"outcome": (True, 1, "1")},
        )
    )

    assert config.expected_categories["outcome"] == (True, 1, "1")
