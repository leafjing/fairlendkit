"""Metric contracts for normalized favorable-outcome and decision indicators."""

from fairlendkit.metrics.core import (
    MetricValue,
    accuracy,
    adverse_impact_ratio,
    brier_score,
    demographic_parity_difference,
    equal_opportunity_difference,
    false_negative_rate,
    false_positive_rate,
    selection_rate,
    true_positive_rate,
)

__all__ = [
    "MetricValue",
    "accuracy",
    "adverse_impact_ratio",
    "brier_score",
    "demographic_parity_difference",
    "equal_opportunity_difference",
    "false_negative_rate",
    "false_positive_rate",
    "selection_rate",
    "true_positive_rate",
]

