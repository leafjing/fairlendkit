"""Metric contracts for normalized favorable-outcome and decision indicators."""

from fairlendkit.metrics.core import (
    MetricValue,
    accuracy,
    adverse_impact_ratio,
    brier_score,
    denial_rate,
    demographic_parity_difference,
    equalized_odds_gap,
    equal_opportunity_difference,
    false_negative_rate,
    false_positive_rate,
    precision,
    roc_auc,
    selection_rate,
    selection_rate_difference,
    true_positive_rate,
)

__all__ = [
    "MetricValue",
    "accuracy",
    "adverse_impact_ratio",
    "brier_score",
    "denial_rate",
    "demographic_parity_difference",
    "equalized_odds_gap",
    "equal_opportunity_difference",
    "false_negative_rate",
    "false_positive_rate",
    "precision",
    "roc_auc",
    "selection_rate",
    "selection_rate_difference",
    "true_positive_rate",
]
