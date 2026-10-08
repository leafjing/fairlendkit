"""Stable inner contracts shared by metric calculation and outer reporting."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Protocol


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


class UndefinedReasonCodeV2(StrEnum):
    """Canonical Schema 2.0 observed-metric undefined reasons."""

    EMPTY_POPULATION = "empty_population"
    ZERO_TOTAL_WEIGHT = "zero_total_weight"
    NO_FAVORABLE_OUTCOMES = "no_favorable_outcomes"
    ZERO_FAVORABLE_OUTCOME_WEIGHT = "zero_favorable_outcome_weight"
    NO_UNFAVORABLE_OUTCOMES = "no_unfavorable_outcomes"
    ZERO_UNFAVORABLE_OUTCOME_WEIGHT = "zero_unfavorable_outcome_weight"
    COMPARISON_METRIC_UNDEFINED = "comparison_metric_undefined"
    REFERENCE_METRIC_UNDEFINED = "reference_metric_undefined"
    ZERO_REFERENCE_SELECTION_RATE = "zero_reference_selection_rate"
    NO_FAVORABLE_DECISIONS = "no_favorable_decisions"
    ZERO_FAVORABLE_DECISION_WEIGHT = "zero_favorable_decision_weight"
    CONSTANT_SCORE = "constant_score"
    METRIC_NOT_APPLICABLE = "metric_not_applicable"
    COMPONENT_METRIC_UNDEFINED = "component_metric_undefined"


CANONICAL_UNDEFINED_MESSAGES_V2 = {
    UndefinedReasonCodeV2.EMPTY_POPULATION: "No records are available for this metric.",
    UndefinedReasonCodeV2.ZERO_TOTAL_WEIGHT: (
        "The metric population has no positive total weight."
    ),
    UndefinedReasonCodeV2.NO_FAVORABLE_OUTCOMES: (
        "No favorable observed outcomes are available for this metric."
    ),
    UndefinedReasonCodeV2.ZERO_FAVORABLE_OUTCOME_WEIGHT: (
        "Favorable observed outcomes have no positive total weight."
    ),
    UndefinedReasonCodeV2.NO_UNFAVORABLE_OUTCOMES: (
        "No unfavorable observed outcomes are available for this metric."
    ),
    UndefinedReasonCodeV2.ZERO_UNFAVORABLE_OUTCOME_WEIGHT: (
        "Unfavorable observed outcomes have no positive total weight."
    ),
    UndefinedReasonCodeV2.COMPARISON_METRIC_UNDEFINED: (
        "The comparison-group input metric is undefined."
    ),
    UndefinedReasonCodeV2.REFERENCE_METRIC_UNDEFINED: (
        "The reference-group input metric is undefined."
    ),
    UndefinedReasonCodeV2.ZERO_REFERENCE_SELECTION_RATE: (
        "The reference-group selection rate is zero, so the ratio is undefined."
    ),
    UndefinedReasonCodeV2.NO_FAVORABLE_DECISIONS: (
        "No favorable decisions are available for this metric."
    ),
    UndefinedReasonCodeV2.ZERO_FAVORABLE_DECISION_WEIGHT: (
        "Favorable decisions have no positive total weight."
    ),
    UndefinedReasonCodeV2.CONSTANT_SCORE: (
        "Eligible scores are constant, so ranking discrimination is undefined."
    ),
    UndefinedReasonCodeV2.METRIC_NOT_APPLICABLE: (
        "The metric does not apply to the configured score semantics."
    ),
    UndefinedReasonCodeV2.COMPONENT_METRIC_UNDEFINED: (
        "A required component metric is undefined."
    ),
}


class LimitationCode(StrEnum):
    SMALL_GROUP = "small_group"
    SEVERE_OUTCOME_IMBALANCE = "severe_outcome_imbalance"
    SPARSE_DECISION_SUPPORT = "sparse_decision_support"
    INSUFFICIENT_VALID_RESAMPLES = "insufficient_valid_resamples"


@dataclass(frozen=True)
class BootstrapInterval:
    """Implementation-neutral percentile interval evidence."""

    metric_key: str
    confidence_level: float
    lower: float
    upper: float
    valid_resamples: int


@dataclass(frozen=True)
class UncertaintyRequest:
    metric_key: str
    population_size: int
    evaluator: Callable[[tuple[int, ...]], float | None]
    seed: int
    resamples: int
    minimum_valid_resamples: int
    confidence_level: float
    stream_role: str = "scope"


@dataclass(frozen=True)
class ComparisonUncertaintyRequest:
    metric_key: str
    comparison_size: int
    reference_size: int
    evaluator: Callable[[tuple[int, ...], tuple[int, ...]], float | None]
    seed: int
    resamples: int
    minimum_valid_resamples: int
    confidence_level: float


@dataclass(frozen=True)
class UncertaintyEstimate:
    interval: BootstrapInterval | None


class UncertaintyEstimator(Protocol):
    """Replaceable uncertainty implementation owned by the inner contract."""

    def estimate(
        self, request: UncertaintyRequest | ComparisonUncertaintyRequest
    ) -> UncertaintyEstimate: ...
