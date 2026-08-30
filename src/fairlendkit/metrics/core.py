"""Small, explicit metric primitives used by later group orchestration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MetricValue:
    """A metric value and its calculation evidence.

    Undefined metrics carry ``value=None`` and a reason. This is intentionally
    different from a defined value of zero.
    """

    value: float | None
    numerator: float | None
    denominator: float | None
    undefined_reason: str | None = None

    def __post_init__(self) -> None:
        evidence = (self.numerator, self.denominator)
        if any(
            value is not None and not _is_finite_metric_number(value)
            for value in evidence
        ):
            raise ValueError("metric evidence must be finite numeric values or None")
        if self.value is None:
            if not self.undefined_reason:
                raise ValueError("an undefined metric requires undefined_reason")
            return
        if not _is_finite_metric_number(self.value):
            raise ValueError("a defined metric value must be finite")
        if self.undefined_reason is not None:
            raise ValueError("a defined metric cannot have undefined_reason")

    @property
    def is_defined(self) -> bool:
        return self.value is not None


def selection_rate(
    favorable_decision: Sequence[bool], weights: Sequence[float] | None = None
) -> MetricValue:
    """Return favorable decisions divided by all records."""

    decisions, normalized_weights = _validated_inputs(favorable_decision, weights)
    return _proportion(decisions, normalized_weights, "no records or positive weight")


def true_positive_rate(
    favorable_outcome: Sequence[bool],
    favorable_decision: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return favorable decisions among favorable observed outcomes."""

    outcomes, decisions, normalized_weights = _validated_pair(
        favorable_outcome, favorable_decision, weights
    )
    return _conditional_rate(
        decisions,
        outcomes,
        normalized_weights,
        "no favorable outcomes or positive weight",
    )


def false_positive_rate(
    favorable_outcome: Sequence[bool],
    favorable_decision: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return favorable decisions among unfavorable observed outcomes."""

    outcomes, decisions, normalized_weights = _validated_pair(
        favorable_outcome, favorable_decision, weights
    )
    unfavorable_outcome = [not value for value in outcomes]
    return _conditional_rate(
        decisions,
        unfavorable_outcome,
        normalized_weights,
        "no unfavorable outcomes or positive weight",
    )


def false_negative_rate(
    favorable_outcome: Sequence[bool],
    favorable_decision: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return unfavorable decisions among favorable observed outcomes."""

    outcomes, decisions, normalized_weights = _validated_pair(
        favorable_outcome, favorable_decision, weights
    )
    unfavorable_decision = [not value for value in decisions]
    return _conditional_rate(
        unfavorable_decision,
        outcomes,
        normalized_weights,
        "no favorable outcomes or positive weight",
    )


def accuracy(
    favorable_outcome: Sequence[bool],
    favorable_decision: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return agreement between normalized outcome and decision indicators."""

    outcomes, decisions, normalized_weights = _validated_pair(
        favorable_outcome, favorable_decision, weights
    )
    matches = [outcome == decision for outcome, decision in zip(outcomes, decisions)]
    return _proportion(matches, normalized_weights, "no records or positive weight")


def brier_score(
    favorable_outcome: Sequence[bool],
    favorable_probability: Sequence[float],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return mean squared error of favorable-outcome probabilities."""

    outcomes = _validated_booleans(favorable_outcome, "favorable_outcome")
    probabilities = [float(value) for value in favorable_probability]
    if len(outcomes) != len(probabilities):
        raise ValueError("metric inputs must have equal lengths")
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("favorable_probability values must be finite and within [0, 1]")
    normalized_weights = _validated_weights(weights, len(outcomes))
    denominator = sum(normalized_weights)
    if denominator == 0:
        return MetricValue(None, None, 0.0, "no records or positive weight")
    numerator = sum(
        weight * (probability - float(outcome)) ** 2
        for outcome, probability, weight in zip(
            outcomes, probabilities, normalized_weights
        )
    )
    return MetricValue(numerator / denominator, numerator, denominator)


def adverse_impact_ratio(
    comparison_selection_rate: MetricValue, reference_selection_rate: MetricValue
) -> MetricValue:
    """Return comparison selection rate divided by reference selection rate."""

    _validate_unit_rate(comparison_selection_rate, "comparison selection rate")
    _validate_unit_rate(reference_selection_rate, "reference selection rate")
    if not comparison_selection_rate.is_defined:
        return MetricValue(None, None, None, "comparison selection rate is undefined")
    if not reference_selection_rate.is_defined:
        return MetricValue(None, None, None, "reference selection rate is undefined")
    if reference_selection_rate.value == 0:
        return MetricValue(
            None,
            comparison_selection_rate.value,
            0.0,
            "reference selection rate is zero",
        )
    return MetricValue(
        comparison_selection_rate.value / reference_selection_rate.value,
        comparison_selection_rate.value,
        reference_selection_rate.value,
    )


def demographic_parity_difference(
    comparison_selection_rate: MetricValue, reference_selection_rate: MetricValue
) -> MetricValue:
    """Return comparison minus reference selection rate."""

    _validate_unit_rate(comparison_selection_rate, "comparison selection rate")
    _validate_unit_rate(reference_selection_rate, "reference selection rate")
    return _difference(
        comparison_selection_rate, reference_selection_rate, "selection rate"
    )


def equal_opportunity_difference(
    comparison_true_positive_rate: MetricValue,
    reference_true_positive_rate: MetricValue,
) -> MetricValue:
    """Return comparison minus reference true-positive rate."""

    _validate_unit_rate(comparison_true_positive_rate, "comparison true-positive rate")
    _validate_unit_rate(reference_true_positive_rate, "reference true-positive rate")
    return _difference(
        comparison_true_positive_rate,
        reference_true_positive_rate,
        "true-positive rate",
    )


def _difference(comparison: MetricValue, reference: MetricValue, name: str) -> MetricValue:
    if not comparison.is_defined:
        return MetricValue(None, None, None, f"comparison {name} is undefined")
    if not reference.is_defined:
        return MetricValue(None, None, None, f"reference {name} is undefined")
    return MetricValue(
        comparison.value - reference.value,
        comparison.value,
        reference.value,
    )


def _validate_unit_rate(metric: MetricValue, name: str) -> None:
    if not isinstance(metric, MetricValue):
        raise TypeError(f"{name} must be a MetricValue")
    if metric.value is not None and not 0.0 <= metric.value <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")


def _is_finite_metric_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _conditional_rate(
    event: Sequence[bool],
    condition: Sequence[bool],
    weights: Sequence[float],
    undefined_reason: str,
) -> MetricValue:
    denominator = sum(weight for include, weight in zip(condition, weights) if include)
    if denominator == 0:
        return MetricValue(None, None, 0.0, undefined_reason)
    numerator = sum(
        weight
        for occurred, include, weight in zip(event, condition, weights)
        if occurred and include
    )
    return MetricValue(numerator / denominator, numerator, denominator)


def _proportion(
    event: Sequence[bool], weights: Sequence[float], undefined_reason: str
) -> MetricValue:
    denominator = sum(weights)
    if denominator == 0:
        return MetricValue(None, None, 0.0, undefined_reason)
    numerator = sum(weight for occurred, weight in zip(event, weights) if occurred)
    return MetricValue(numerator / denominator, numerator, denominator)


def _validated_pair(
    left: Sequence[bool], right: Sequence[bool], weights: Sequence[float] | None
) -> tuple[list[bool], list[bool], list[float]]:
    normalized_left = _validated_booleans(left, "favorable_outcome")
    normalized_right = _validated_booleans(right, "favorable_decision")
    if len(normalized_left) != len(normalized_right):
        raise ValueError("metric inputs must have equal lengths")
    return (
        normalized_left,
        normalized_right,
        _validated_weights(weights, len(normalized_left)),
    )


def _validated_inputs(
    values: Sequence[bool], weights: Sequence[float] | None
) -> tuple[list[bool], list[float]]:
    normalized = _validated_booleans(values, "favorable_decision")
    return normalized, _validated_weights(weights, len(normalized))


def _validated_booleans(values: Iterable[bool], name: str) -> list[bool]:
    normalized = list(values)
    if any(type(value) is not bool for value in normalized):
        raise TypeError(f"{name} must contain normalized boolean values")
    return normalized


def _validated_weights(weights: Sequence[float] | None, length: int) -> list[float]:
    if weights is None:
        return [1.0] * length
    normalized = [float(value) for value in weights]
    if len(normalized) != length:
        raise ValueError("weights and metric inputs must have equal lengths")
    if any(not math.isfinite(value) or value < 0 for value in normalized):
        raise ValueError("weights must be finite and non-negative")
    maximum = max(normalized, default=0.0)
    if maximum == 0.0:
        return normalized
    # Scale invariance preserves every implemented weighted rate while keeping
    # sums finite even when callers provide values near the float limit.
    return [value / maximum for value in normalized]
