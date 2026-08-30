import math

import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig, ScoreDirection


def config_values(**overrides):
    values = {
        "outcome_column": "outcome",
        "score_column": "score",
        "favorable_label": 1,
        "score_direction": ScoreDirection.HIGHER_IS_MORE_FAVORABLE,
        "protected_attributes": ("group",),
        "reference_groups": {"group": "A"},
    }
    values.update(overrides)
    return values


def test_score_direction_is_explicit_and_reversible():
    higher = AuditConfig(**config_values())
    lower = AuditConfig(
        **config_values(score_direction=ScoreDirection.LOWER_IS_MORE_FAVORABLE)
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
            )
        )


def test_observed_and_threshold_decisions_are_mutually_exclusive():
    with pytest.raises(ValidationError, match="either an observed"):
        AuditConfig(
            **config_values(
                decision_column="approved",
                favorable_decision_label=1,
                decision_threshold=0.5,
            )
        )

