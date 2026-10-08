"""Optional vectorized evaluators for exact unweighted bootstrap primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from fairlendkit.metrics.contracts import MetricNameV2


@dataclass(frozen=True)
class UnweightedScopeBatchEvaluator:
    metric: MetricNameV2
    outcomes: tuple[bool, ...]
    decisions: tuple[bool, ...]
    scores: tuple[float, ...]
    source: tuple[int, ...]
    fallback: Callable[[tuple[int, ...]], float | None]

    def __call__(self, draw: tuple[int, ...]) -> float | None:
        return self.fallback(draw)

    def evaluate_batch(self, draws: np.ndarray) -> tuple[float | None, ...] | None:
        """Return exact count-based values, or ``None`` for fallback metrics."""
        if self.metric is MetricNameV2.BRIER_SCORE:
            return None
        source = np.asarray(self.source, dtype=np.intp)
        indices = source[draws]
        decisions = np.asarray(self.decisions, dtype=np.bool_)[indices]
        outcomes = np.asarray(self.outcomes, dtype=np.bool_)[indices]
        size = draws.shape[1]
        if self.metric is MetricNameV2.ROC_AUC:
            return _unweighted_auc_batch(
                draws,
                np.asarray(self.outcomes, dtype=np.bool_)[source],
                np.asarray(self.scores, dtype=np.float64)[source],
            )
        if self.metric is MetricNameV2.SELECTION_RATE:
            values = decisions.sum(axis=1) / size
        elif self.metric is MetricNameV2.DENIAL_RATE:
            values = (~decisions).sum(axis=1) / size
        elif self.metric is MetricNameV2.ACCURACY:
            values = (outcomes == decisions).sum(axis=1) / size
        elif self.metric is MetricNameV2.PRECISION:
            support = decisions.sum(axis=1)
            numerator = (outcomes & decisions).sum(axis=1)
            values = _optional_ratio(numerator, support)
        elif self.metric in (
            MetricNameV2.TRUE_POSITIVE_RATE,
            MetricNameV2.FALSE_NEGATIVE_RATE,
        ):
            support = outcomes.sum(axis=1)
            favorable = (outcomes & decisions).sum(axis=1)
            numerator = (
                favorable
                if self.metric is MetricNameV2.TRUE_POSITIVE_RATE
                else support - favorable
            )
            values = _optional_ratio(numerator, support)
        elif self.metric is MetricNameV2.FALSE_POSITIVE_RATE:
            unfavorable = ~outcomes
            support = unfavorable.sum(axis=1)
            values = _optional_ratio((unfavorable & decisions).sum(axis=1), support)
        else:
            return None
        return tuple(None if np.isnan(value) else float(value) for value in values)


@dataclass(frozen=True)
class UnweightedComparisonBatchEvaluator:
    metric: MetricNameV2
    outcomes: tuple[bool, ...]
    decisions: tuple[bool, ...]
    comparison_source: tuple[int, ...]
    reference_source: tuple[int, ...]
    fallback: Callable[[tuple[int, ...], tuple[int, ...]], float | None]

    def __call__(
        self, comparison_draw: tuple[int, ...], reference_draw: tuple[int, ...]
    ) -> float | None:
        return self.fallback(comparison_draw, reference_draw)

    def evaluate_comparison_batch(
        self, comparison_draws: np.ndarray, reference_draws: np.ndarray
    ) -> tuple[float | None, ...]:
        decisions = np.asarray(self.decisions, dtype=np.bool_)
        outcomes = np.asarray(self.outcomes, dtype=np.bool_)
        comparison = np.asarray(self.comparison_source, dtype=np.intp)[comparison_draws]
        reference = np.asarray(self.reference_source, dtype=np.intp)[reference_draws]
        comparison_decisions = decisions[comparison]
        reference_decisions = decisions[reference]
        comparison_selection = comparison_decisions.sum(axis=1) / comparison.shape[1]
        reference_selection = reference_decisions.sum(axis=1) / reference.shape[1]
        if self.metric in (
            MetricNameV2.SELECTION_RATE_DIFFERENCE,
            MetricNameV2.DEMOGRAPHIC_PARITY_DIFFERENCE,
        ):
            values = comparison_selection - reference_selection
        elif self.metric is MetricNameV2.ADVERSE_IMPACT_RATIO:
            values = _optional_ratio(comparison_selection, reference_selection)
        else:
            comparison_outcomes = outcomes[comparison]
            reference_outcomes = outcomes[reference]
            comparison_tpr = _conditional_rate(comparison_outcomes, comparison_decisions, True)
            reference_tpr = _conditional_rate(reference_outcomes, reference_decisions, True)
            if self.metric is MetricNameV2.EQUAL_OPPORTUNITY_DIFFERENCE:
                values = comparison_tpr - reference_tpr
            else:
                comparison_fpr = _conditional_rate(
                    comparison_outcomes, comparison_decisions, False
                )
                reference_fpr = _conditional_rate(
                    reference_outcomes, reference_decisions, False
                )
                values = np.maximum(
                    np.abs(comparison_tpr - reference_tpr),
                    np.abs(comparison_fpr - reference_fpr),
                )
        return tuple(None if np.isnan(value) else float(value) for value in values)


def _optional_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    values = np.full(numerator.shape, np.nan, dtype=np.float64)
    np.divide(numerator, denominator, out=values, where=denominator != 0)
    return values


def _conditional_rate(
    outcomes: np.ndarray, decisions: np.ndarray, favorable: bool
) -> np.ndarray:
    mask = outcomes if favorable else ~outcomes
    return _optional_ratio((mask & decisions).sum(axis=1), mask.sum(axis=1))


def _unweighted_auc_batch(
    draws: np.ndarray, outcomes: np.ndarray, scores: np.ndarray
) -> tuple[float | None, ...]:
    """Evaluate the exact pair-count AUC definition for every draw."""
    rows, size = draws.shape
    counts = np.zeros((rows, size), dtype=np.int32)
    np.add.at(
        counts,
        (np.repeat(np.arange(rows, dtype=np.intp), size), draws.reshape(-1)),
        1,
    )
    order = np.argsort(scores, kind="stable")
    ordered_scores = scores[order]
    ordered_counts = counts[:, order]
    ordered_outcomes = outcomes[order]
    doubled_numerator = np.zeros(rows, dtype=np.int64)
    unfavorable_below = np.zeros(rows, dtype=np.int64)
    start = 0
    while start < size:
        end = start + 1
        while end < size and ordered_scores[end] == ordered_scores[start]:
            end += 1
        score_counts = ordered_counts[:, start:end]
        score_outcomes = ordered_outcomes[start:end]
        favorable = score_counts[:, score_outcomes].sum(axis=1, dtype=np.int64)
        unfavorable = score_counts[:, ~score_outcomes].sum(axis=1, dtype=np.int64)
        doubled_numerator += favorable * (2 * unfavorable_below + unfavorable)
        unfavorable_below += unfavorable
        start = end
    favorable_total = counts[:, outcomes].sum(axis=1, dtype=np.int64)
    unfavorable_total = counts[:, ~outcomes].sum(axis=1, dtype=np.int64)
    denominator = favorable_total * unfavorable_total
    values = np.full(rows, np.nan, dtype=np.float64)
    defined = (favorable_total != 0) & (unfavorable_total != 0)
    np.divide(
        doubled_numerator.astype(np.float64) * 0.5,
        denominator,
        out=values,
        where=defined,
    )
    return tuple(None if np.isnan(value) else float(value) for value in values)
