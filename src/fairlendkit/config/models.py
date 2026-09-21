"""Configuration models with explicit credit-score semantics."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Label = str | int | bool
ColumnName = Annotated[str, Field(min_length=1)]
NonBlankText = Annotated[str, Field(min_length=1, pattern=r".*\S.*")]


class ScoreDirection(StrEnum):
    """How score values relate to the configured favorable outcome."""

    HIGHER_IS_MORE_FAVORABLE = "higher_is_more_favorable"
    LOWER_IS_MORE_FAVORABLE = "lower_is_more_favorable"


class ThresholdOperator(StrEnum):
    """Comparison used to derive the configured favorable decision."""

    GREATER_THAN_OR_EQUAL = "ge"
    LESS_THAN_OR_EQUAL = "le"


class ScoreType(StrEnum):
    """Whether scores have probability semantics or only ranking semantics."""

    PROBABILITY = "probability"
    RANKING = "ranking"


class AuditConfig(BaseModel):
    """Validated semantic and column contract for one audit run.

    Unknown fields are rejected so misspelled semantic settings cannot be
    silently ignored.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
    )

    outcome_column: ColumnName
    score_column: ColumnName
    population_definition: NonBlankText
    sampling_definition: NonBlankText
    score_type: ScoreType
    dataset_version: NonBlankText | None
    model_version: NonBlankText | None
    data_as_of: AwareDatetime | None
    execution_timestamp: AwareDatetime
    favorable_label: Label
    score_direction: ScoreDirection
    protected_attributes: tuple[ColumnName, ...] = Field(min_length=1)
    reference_groups: dict[ColumnName, Label] = Field(min_length=1)
    allowed_groups: dict[ColumnName, tuple[Label, ...]] = Field(min_length=1)
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
    unknown_group_policy: Literal["exclude", "error"] = "error"

    @model_validator(mode="after")
    def validate_semantics(self) -> "AuditConfig":
        protected = set(self.protected_attributes)
        references = set(self.reference_groups)
        allowed = set(self.allowed_groups)
        if len(protected) != len(self.protected_attributes):
            raise ValueError("protected_attributes must not contain duplicates")
        if protected != references:
            raise ValueError(
                "reference_groups must contain exactly one explicit value for "
                "each protected attribute"
            )
        if protected != allowed:
            raise ValueError(
                "allowed_groups must contain exactly one explicit value list for "
                "each protected attribute"
            )
        for attribute, values in self.allowed_groups.items():
            if not values:
                raise ValueError(f"allowed_groups[{attribute!r}] must not be empty")
            if _has_typed_duplicates(values):
                raise ValueError(
                    f"allowed_groups[{attribute!r}] must not contain duplicates"
                )
            if not _contains_typed_value(values, self.reference_groups[attribute]):
                raise ValueError(
                    f"reference_groups[{attribute!r}] must belong to allowed_groups"
                )
        column_roles: list[tuple[str, str]] = [
            (self.outcome_column, "outcome_column"),
            (self.score_column, "score_column"),
            *(
                (column, f"protected_attributes[{index}]")
                for index, column in enumerate(self.protected_attributes)
            ),
            *(
                (column, f"candidate_proxy_features[{index}]")
                for index, column in enumerate(self.candidate_proxy_features)
            ),
        ]
        if self.decision_column is not None:
            column_roles.append((self.decision_column, "decision_column"))
        if self.sample_weight_column is not None:
            column_roles.append((self.sample_weight_column, "sample_weight_column"))
        roles_by_column: dict[str, list[str]] = {}
        for column, role in column_roles:
            roles_by_column.setdefault(column, []).append(role)
        conflicts = {
            column: roles for column, roles in roles_by_column.items() if len(roles) > 1
        }
        if conflicts:
            details = "; ".join(
                f"{column!r}: {', '.join(roles)}"
                for column, roles in sorted(conflicts.items())
            )
            raise ValueError(f"columns must have exactly one semantic role; {details}")
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


def _contains_typed_value(values: tuple[Label, ...], expected: Label) -> bool:
    return any(_typed_values_equal(value, expected) for value in values)


def _has_typed_duplicates(values: tuple[Label, ...]) -> bool:
    return any(
        _typed_values_equal(value, earlier)
        for index, value in enumerate(values)
        for earlier in values[:index]
    )


def _typed_values_equal(actual: object, expected: object) -> bool:
    return type(actual) is type(expected) and actual == expected
