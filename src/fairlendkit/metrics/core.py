"""Small, explicit metric primitives used by later group orchestration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

CANONICAL_UNDEFINED_REASONS = frozenset(
    {
        "empty_population",
        "zero_total_weight",
        "no_favorable_outcomes",
        "zero_favorable_outcome_weight",
        "no_unfavorable_outcomes",
        "zero_unfavorable_outcome_weight",
        "no_favorable_decisions",
        "zero_favorable_decision_weight",
        "constant_score",
        "metric_not_applicable",
        "comparison_metric_undefined",
        "reference_metric_undefined",
        "component_metric_undefined",
        "zero_reference_selection_rate",
    }
)


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
            if self.undefined_reason not in CANONICAL_UNDEFINED_REASONS:
                raise ValueError("undefined_reason must use a canonical reason code")
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
    return _proportion(decisions, normalized_weights)


def denial_rate(
    favorable_decision: Sequence[bool], weights: Sequence[float] | None = None
) -> MetricValue:
    """Return unfavorable decisions divided by all records."""

    decisions, normalized_weights = _validated_inputs(favorable_decision, weights)
    return _proportion([not value for value in decisions], normalized_weights)


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
        "no_favorable_outcomes",
        "zero_favorable_outcome_weight",
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
        "no_unfavorable_outcomes",
        "zero_unfavorable_outcome_weight",
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
        "no_favorable_outcomes",
        "zero_favorable_outcome_weight",
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
    return _proportion(matches, normalized_weights)


def precision(
    favorable_outcome: Sequence[bool],
    favorable_decision: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return favorable outcomes among favorable decisions."""

    outcomes, decisions, normalized_weights = _validated_pair(
        favorable_outcome, favorable_decision, weights
    )
    return _conditional_rate(
        outcomes,
        decisions,
        normalized_weights,
        "no_favorable_decisions",
        "zero_favorable_decision_weight",
    )


def brier_score(
    favorable_outcome: Sequence[bool],
    favorable_probability: Sequence[float],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return mean squared error of favorable-outcome probabilities."""

    outcomes = _validated_booleans(favorable_outcome, "favorable_outcome")
    probabilities = [
        _validated_finite_number(value, "favorable_probability")
        for value in favorable_probability
    ]
    if len(outcomes) != len(probabilities):
        raise ValueError("metric inputs must have equal lengths")
    if any(not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("favorable_probability values must be finite and within [0, 1]")
    normalized_weights = _validated_weights(weights, len(outcomes))
    denominator = sum(normalized_weights)
    if denominator == 0:
        reason = "empty_population" if not outcomes else "zero_total_weight"
        return MetricValue(None, None, 0.0, reason)
    numerator = sum(
        weight * (probability - float(outcome)) ** 2
        for outcome, probability, weight in zip(
            outcomes, probabilities, normalized_weights
        )
    )
    return MetricValue(numerator / denominator, numerator, denominator)


def roc_auc(
    favorable_outcome: Sequence[bool],
    favorable_score: Sequence[float],
    weights: Sequence[float] | None = None,
) -> MetricValue:
    """Return the weighted favorable-vs-unfavorable ranking probability."""

    outcomes = _validated_booleans(favorable_outcome, "favorable_outcome")
    scores = [
        _validated_finite_number(value, "favorable_score")
        for value in favorable_score
    ]
    if len(outcomes) != len(scores):
        raise ValueError("metric inputs must have equal lengths")
    normalized_weights = _validated_weights(weights, len(outcomes))
    if not outcomes:
        return MetricValue(None, None, None, "empty_population")
    favorable = [
        (score, weight)
        for outcome, score, weight in zip(outcomes, scores, normalized_weights)
        if outcome
    ]
    unfavorable = [
        (score, weight)
        for outcome, score, weight in zip(outcomes, scores, normalized_weights)
        if not outcome
    ]
    if not favorable:
        return MetricValue(None, None, None, "no_favorable_outcomes")
    if not unfavorable:
        return MetricValue(None, None, None, "no_unfavorable_outcomes")
    favorable_weight = sum(weight for _, weight in favorable)
    unfavorable_weight = sum(weight for _, weight in unfavorable)
    if favorable_weight == 0:
        return MetricValue(None, None, 0.0, "zero_favorable_outcome_weight")
    if unfavorable_weight == 0:
        return MetricValue(None, None, 0.0, "zero_unfavorable_outcome_weight")
    if min(scores) == max(scores):
        return MetricValue(
            None,
            None,
            favorable_weight * unfavorable_weight,
            "constant_score",
        )
    if weights is None:
        # The pairwise definition contributes only 0, 0.5, or 1 per pair.
        # Aggregate equal-score runs to preserve that exact numerator while
        # avoiding the quadratic pair materialization used for weighted AUC.
        by_score: dict[float, list[int]] = {}
        for outcome, score in zip(outcomes, scores):
            counts = by_score.setdefault(score, [0, 0])
            counts[0 if outcome else 1] += 1
        numerator = 0.0
        unfavorable_below = 0
        for score in sorted(by_score):
            favorable_count, unfavorable_count = by_score[score]
            numerator += favorable_count * (
                unfavorable_below + 0.5 * unfavorable_count
            )
            unfavorable_below += unfavorable_count
        denominator = favorable_weight * unfavorable_weight
        return MetricValue(numerator / denominator, numerator, denominator)
    numerator = sum(
        favorable_item_weight
        * unfavorable_item_weight
        * (
            1.0
            if favorable_item_score > unfavorable_item_score
            else 0.5
            if favorable_item_score == unfavorable_item_score
            else 0.0
        )
        for favorable_item_score, favorable_item_weight in favorable
        for unfavorable_item_score, unfavorable_item_weight in unfavorable
    )
    denominator = favorable_weight * unfavorable_weight
    return MetricValue(numerator / denominator, numerator, denominator)


def adverse_impact_ratio(
    comparison_selection_rate: MetricValue, reference_selection_rate: MetricValue
) -> MetricValue:
    """Return comparison selection rate divided by reference selection rate."""

    _validate_unit_rate(comparison_selection_rate, "comparison selection rate")
    _validate_unit_rate(reference_selection_rate, "reference selection rate")
    if not comparison_selection_rate.is_defined:
        return MetricValue(None, None, None, "comparison_metric_undefined")
    if not reference_selection_rate.is_defined:
        return MetricValue(None, None, None, "reference_metric_undefined")
    if reference_selection_rate.value == 0:
        return MetricValue(
            None,
            comparison_selection_rate.value,
            0.0,
            "zero_reference_selection_rate",
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

    return selection_rate_difference(comparison_selection_rate, reference_selection_rate)


def selection_rate_difference(
    comparison_selection_rate: MetricValue, reference_selection_rate: MetricValue
) -> MetricValue:
    """Return comparison minus reference selection rate."""

    _validate_unit_rate(comparison_selection_rate, "comparison selection rate")
    _validate_unit_rate(reference_selection_rate, "reference selection rate")
    return _difference(comparison_selection_rate, reference_selection_rate)


def equal_opportunity_difference(
    comparison_true_positive_rate: MetricValue,
    reference_true_positive_rate: MetricValue,
) -> MetricValue:
    """Return comparison minus reference true-positive rate."""

    _validate_unit_rate(comparison_true_positive_rate, "comparison true-positive rate")
    _validate_unit_rate(reference_true_positive_rate, "reference true-positive rate")
    return _difference(comparison_true_positive_rate, reference_true_positive_rate)


def equalized_odds_gap(
    comparison_true_positive_rate: MetricValue,
    reference_true_positive_rate: MetricValue,
    comparison_false_positive_rate: MetricValue,
    reference_false_positive_rate: MetricValue,
) -> MetricValue:
    """Return the maximum absolute TPR or FPR difference."""

    rates = (
        (comparison_true_positive_rate, "comparison true-positive rate"),
        (reference_true_positive_rate, "reference true-positive rate"),
        (comparison_false_positive_rate, "comparison false-positive rate"),
        (reference_false_positive_rate, "reference false-positive rate"),
    )
    for metric, name in rates:
        _validate_unit_rate(metric, name)
    if any(not metric.is_defined for metric, _ in rates):
        return MetricValue(None, None, None, "component_metric_undefined")
    tpr_delta = abs(
        comparison_true_positive_rate.value - reference_true_positive_rate.value
    )
    fpr_delta = abs(
        comparison_false_positive_rate.value - reference_false_positive_rate.value
    )
    return MetricValue(max(tpr_delta, fpr_delta), tpr_delta, fpr_delta)


def _difference(comparison: MetricValue, reference: MetricValue) -> MetricValue:
    if not comparison.is_defined:
        return MetricValue(None, None, None, "comparison_metric_undefined")
    if not reference.is_defined:
        return MetricValue(None, None, None, "reference_metric_undefined")
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
    empty_reason: str,
    zero_weight_reason: str,
) -> MetricValue:
    if not any(condition):
        return MetricValue(None, None, 0.0, empty_reason)
    denominator = sum(weight for include, weight in zip(condition, weights) if include)
    if denominator == 0:
        return MetricValue(None, None, 0.0, zero_weight_reason)
    numerator = sum(
        weight
        for occurred, include, weight in zip(event, condition, weights)
        if occurred and include
    )
    return MetricValue(numerator / denominator, numerator, denominator)


def _proportion(event: Sequence[bool], weights: Sequence[float]) -> MetricValue:
    if not event:
        return MetricValue(None, None, 0.0, "empty_population")
    denominator = sum(weights)
    if denominator == 0:
        return MetricValue(None, None, 0.0, "zero_total_weight")
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


def _validated_finite_number(value: object, name: str) -> float:
    if not _is_finite_metric_number(value):
        raise TypeError(f"{name} must contain finite numeric values")
    return float(value)


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
