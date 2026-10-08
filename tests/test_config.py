import math

import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, ScoreDirection


def config_values(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "population_definition": "All applications in the review period",
        "score_type": "ranking",
        "dataset_version": None,
        "model_version": None,
        "data_as_of": None,
        "favorable_label": 1,
        "score_direction": ScoreDirection.HIGHER_IS_MORE_FAVORABLE,
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
        "allowed_groups": {"group": ("A", "B")},
        "unknown_group_policy": "error",
        "favorable_decision_label": 1,
        "decision_threshold": 0.5,
        "threshold_operator": "ge",
    }
    values.update(overrides)
    return values


def test_score_direction_is_explicit_and_reversible():
    higher = AuditConfig(**config_values())
    lower = AuditConfig(
        **config_values(
            score_direction=ScoreDirection.LOWER_IS_MORE_FAVORABLE,
            threshold_operator="le",
        )
    )

    assert higher.score_direction != lower.score_direction


@pytest.mark.parametrize(
    "field",
    [
        "population_definition",
        "score_type",
        "dataset_version",
        "model_version",
        "data_as_of",
    ],
)
def test_run_context_fields_must_be_explicit(field):
    values = config_values()
    values.pop(field)

    with pytest.raises(ValidationError, match=field):
        AuditConfig(**values)


def test_population_definition_cannot_be_blank():
    with pytest.raises(ValidationError, match="must not be blank"):
        AuditConfig(**config_values(population_definition="   "))


def test_probability_and_ranking_scores_are_distinguished():
    probability = AuditConfig(**config_values(score_type="probability"))
    ranking = AuditConfig(**config_values(score_type="ranking"))

    assert probability.score_type != ranking.score_type


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
                allowed_groups={"group": ("A", "B"), "region": ("north",)},
            )
        )


def test_allowed_values_required_for_every_protected_attribute():
    with pytest.raises(ValidationError, match="allowed_groups"):
        AuditConfig(**config_values(allowed_groups={"other": ("A",)}))


def test_reference_group_must_be_allowed_with_exact_type():
    with pytest.raises(ValidationError, match="must be one of its allowed values"):
        AuditConfig(
            **config_values(
                reference_groups={"group": True},
                allowed_groups={"group": (1, 2)},
            )
        )


def test_allowed_values_cannot_have_typed_duplicates():
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        AuditConfig(**config_values(allowed_groups={"group": ("A", "A")}))


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
