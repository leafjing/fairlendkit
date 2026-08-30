"""Configuration models with explicit credit-score semantics."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = str | int | bool
ColumnName = Annotated[str, Field(min_length=1)]


class ScoreDirection(StrEnum):
    """How score values relate to the configured favorable outcome."""

    HIGHER_IS_MORE_FAVORABLE = "higher_is_more_favorable"
    LOWER_IS_MORE_FAVORABLE = "lower_is_more_favorable"


class ThresholdOperator(StrEnum):
    """Comparison used to derive the configured favorable decision."""

    GREATER_THAN_OR_EQUAL = "ge"
    LESS_THAN_OR_EQUAL = "le"


class AuditConfig(BaseModel):
    """Validated semantic and column contract for one audit run.

    Unknown fields are rejected so misspelled semantic settings cannot be
    silently ignored.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_column: ColumnName
    score_column: ColumnName
    favorable_label: Label
    score_direction: ScoreDirection
    protected_attributes: tuple[ColumnName, ...] = Field(min_length=1)
    reference_groups: dict[ColumnName, Label] = Field(min_length=1)
    favorable_decision_label: Label = Field(
        description=(
            "Value representing the beneficial decision. For a derived decision, "
            "a score satisfying the inclusive threshold rule receives this meaning."
        )
    )
    decision_column: ColumnName | None = None
    decision_threshold: float | None = Field(
        default=None,
        description="Finite score boundary used to derive a favorable decision.",
    )
    threshold_operator: ThresholdOperator | None = Field(
        default=None,
        description=(
            "Inclusive comparison: ge means score >= threshold; "
            "le means score <= threshold."
        ),
    )
    sample_weight_column: ColumnName | None = None
    candidate_proxy_features: tuple[ColumnName, ...] = ()
    minimum_group_size: int = Field(default=30, ge=1)
    confidence_level: float = Field(default=0.95, gt=0.0, lt=1.0)
    missing_value_policy: Literal["exclude", "error"] = "error"

    @model_validator(mode="after")
    def validate_semantics(self) -> "AuditConfig":
        protected = set(self.protected_attributes)
        references = set(self.reference_groups)
        if len(protected) != len(self.protected_attributes):
            raise ValueError("protected_attributes must not contain duplicates")
        if protected != references:
            raise ValueError(
                "reference_groups must contain exactly one explicit value for "
                "each protected attribute"
            )
        has_observed_decision = self.decision_column is not None
        has_derived_decision = self.decision_threshold is not None
        if has_observed_decision == has_derived_decision:
            raise ValueError(
                "configure exactly one of decision_column or decision_threshold"
            )
        if has_derived_decision != (self.threshold_operator is not None):
            raise ValueError(
                "decision_threshold and threshold_operator must be configured together"
            )
        if self.decision_threshold is not None and not math.isfinite(self.decision_threshold):
            raise ValueError("decision_threshold must be finite")
        expected_operator = {
            ScoreDirection.HIGHER_IS_MORE_FAVORABLE: ThresholdOperator.GREATER_THAN_OR_EQUAL,
            ScoreDirection.LOWER_IS_MORE_FAVORABLE: ThresholdOperator.LESS_THAN_OR_EQUAL,
        }[self.score_direction]
        if self.threshold_operator is not None and self.threshold_operator != expected_operator:
            raise ValueError(
                "threshold_operator is inconsistent with score_direction: "
                f"expected {expected_operator.value!r}"
            )
        return self

    def is_favorable_decision_score(self, score: float) -> bool:
        """Return whether a score satisfies the inclusive derived-decision rule.

        This method is available only for threshold-derived decisions. ``True``
        means the record receives the meaning in ``favorable_decision_label``;
        it does not describe the observed outcome or ``favorable_label``.
        """

        if self.decision_threshold is None or self.threshold_operator is None:
            raise ValueError("configuration uses an observed decision_column")
        try:
            numeric_score = float(score)
        except (TypeError, ValueError) as error:
            raise ValueError("score must be a finite number") from error
        if not math.isfinite(numeric_score):
            raise ValueError("score must be a finite number")
        if self.threshold_operator == ThresholdOperator.GREATER_THAN_OR_EQUAL:
            return numeric_score >= self.decision_threshold
        return numeric_score <= self.decision_threshold
