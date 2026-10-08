"""Stable inner contracts shared by metric calculation and outer reporting."""

from enum import StrEnum


class MetricNameV2(StrEnum):
    """Canonical Schema 2.0 metric identities."""

    SELECTION_RATE = "selection_rate"
    DENIAL_RATE = "denial_rate"
    ACCURACY = "accuracy"
    PRECISION = "precision"
    TRUE_POSITIVE_RATE = "true_positive_rate"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_NEGATIVE_RATE = "false_negative_rate"
    BRIER_SCORE = "brier_score"
    ROC_AUC = "roc_auc"
    SELECTION_RATE_DIFFERENCE = "selection_rate_difference"
    ADVERSE_IMPACT_RATIO = "adverse_impact_ratio"
    DEMOGRAPHIC_PARITY_DIFFERENCE = "demographic_parity_difference"
    EQUAL_OPPORTUNITY_DIFFERENCE = "equal_opportunity_difference"
    EQUALIZED_ODDS_GAP = "equalized_odds_gap"
