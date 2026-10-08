"""Deterministic group metric orchestration over normalized immutable inputs."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from fairlendkit.config import AuditConfig
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
from fairlendkit.metrics.contracts import MetricNameV2


SCOPE_METRIC_ORDER = (
    MetricNameV2.SELECTION_RATE,
    MetricNameV2.DENIAL_RATE,
    MetricNameV2.ACCURACY,
    MetricNameV2.PRECISION,
    MetricNameV2.TRUE_POSITIVE_RATE,
    MetricNameV2.FALSE_POSITIVE_RATE,
    MetricNameV2.FALSE_NEGATIVE_RATE,
    MetricNameV2.BRIER_SCORE,
    MetricNameV2.ROC_AUC,
)
COMPARISON_METRIC_ORDER = (
    MetricNameV2.SELECTION_RATE_DIFFERENCE,
    MetricNameV2.ADVERSE_IMPACT_RATIO,
    MetricNameV2.DEMOGRAPHIC_PARITY_DIFFERENCE,
    MetricNameV2.EQUAL_OPPORTUNITY_DIFFERENCE,
    MetricNameV2.EQUALIZED_ODDS_GAP,
)


@dataclass(frozen=True, eq=False)
class AuditScope:
    """Immutable, type-preserving group identity."""

    attributes: tuple[tuple[str, str | int | bool], ...]

    def __post_init__(self) -> None:
        if not self.attributes:
            raise ValueError("audit scope must contain at least one attribute")
        if len({name for name, _ in self.attributes}) != len(self.attributes):
            raise ValueError("audit scope attributes must be unique")

    def _typed_identity(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (name, canonical_typed_token(value)) for name, value in self.attributes
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AuditScope) and self._typed_identity() == other._typed_identity()

    def __hash__(self) -> int:
        return hash(self._typed_identity())

    @classmethod
    def overall(cls) -> "AuditScope":
        return cls((("__scope__", "overall"),))


@dataclass(frozen=True)
class CalculatedMetric:
    """One keyed primitive result before reliability and report assembly."""

    key: str
    metric: MetricNameV2
    value: MetricValue
    sample_count: int
    group: AuditScope | None = None
    comparison_group: AuditScope | None = None
    reference_group: AuditScope | None = None

    def __post_init__(self) -> None:
        is_comparison = self.metric in COMPARISON_METRIC_ORDER
        if is_comparison:
            if self.group is not None or self.comparison_group is None or self.reference_group is None:
                raise ValueError("comparison metrics require comparison and reference scopes")
        elif self.group is None or self.comparison_group is not None or self.reference_group is not None:
            raise ValueError("scope metrics require exactly one group scope")


@dataclass(frozen=True)
class NormalizedAuditData:
    """Adapter-neutral inputs whose booleans already use favorable semantics."""

    favorable_outcome: tuple[bool, ...]
    favorable_decision: tuple[bool, ...]
    favorable_score: tuple[float, ...]
    protected_values: Mapping[str, tuple[str | int | bool, ...]]
    weights: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "favorable_outcome", tuple(self.favorable_outcome))
        object.__setattr__(self, "favorable_decision", tuple(self.favorable_decision))
        object.__setattr__(self, "favorable_score", tuple(self.favorable_score))
        if self.weights is not None:
            object.__setattr__(self, "weights", tuple(self.weights))
        object.__setattr__(
            self,
            "protected_values",
            MappingProxyType(
                {name: tuple(values) for name, values in self.protected_values.items()}
            ),
        )
        length = len(self.favorable_outcome)
        if len(self.favorable_decision) != length or len(self.favorable_score) != length:
            raise ValueError("normalized audit inputs must have equal lengths")
        if self.weights is not None and len(self.weights) != length:
            raise ValueError("weights and normalized audit inputs must have equal lengths")
        if any(len(values) != length for values in self.protected_values.values()):
            raise ValueError("protected values and normalized audit inputs must have equal lengths")


def canonical_typed_token(value: str | int | bool | float) -> str:
    """Encode a typed value for collision-free metric keys and ordering."""

    if isinstance(value, bool):
        type_name = "bool"
    elif isinstance(value, int):
        type_name = "int"
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical key values must be finite")
        type_name = "float"
    elif isinstance(value, str):
        type_name = "str"
    else:
        raise TypeError("canonical key values must be strings, integers, booleans, or floats")
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return f"{type_name}-{payload.encode('utf-8').hex()}"


def canonical_metric_key(
    metric: MetricNameV2,
    *,
    group: AuditScope | None = None,
    comparison_group: AuditScope | None = None,
    reference_group: AuditScope | None = None,
) -> str:
    """Build the stable key prescribed by the Milestone 3 contract."""

    if group == AuditScope.overall():
        return f"overall.{metric.value}"
    if group is not None:
        if len(group.attributes) != 1:
            raise ValueError("Milestone 3 group keys require one protected attribute")
        attribute, value = group.attributes[0]
        return f"group.{canonical_typed_token(attribute)}.{canonical_typed_token(value)}.{metric.value}"
    if comparison_group is None or reference_group is None:
        raise ValueError("comparison keys require comparison and reference scopes")
    if len(comparison_group.attributes) != 1 or len(reference_group.attributes) != 1:
        raise ValueError("Milestone 3 comparison keys require one protected attribute")
    attribute, comparison = comparison_group.attributes[0]
    reference_attribute, reference = reference_group.attributes[0]
    if attribute != reference_attribute:
        raise ValueError("comparison and reference scopes must use the same attribute")
    return (
        f"comparison.{canonical_typed_token(attribute)}."
        f"{canonical_typed_token(comparison)}.vs.{canonical_typed_token(reference)}."
        f"{metric.value}"
    )


def calculate_group_metrics(
    data: NormalizedAuditData, config: AuditConfig
) -> tuple[CalculatedMetric, ...]:
    """Calculate overall, configured group, and directed comparison metrics."""

    if not isinstance(data, NormalizedAuditData):
        raise TypeError("data must be NormalizedAuditData")
    if not isinstance(config, AuditConfig):
        raise TypeError("config must be AuditConfig")
    if set(data.protected_values) != set(config.protected_attributes):
        raise ValueError("protected values must match configured protected attributes")
    for attribute in config.protected_attributes:
        allowed = config.allowed_groups[attribute]
        if any(
            not any(type(observed) is type(value) and observed == value for value in allowed)
            for observed in data.protected_values[attribute]
        ):
            raise ValueError("protected values must belong to configured allowed groups")

    output: list[CalculatedMetric] = []
    scope_results: dict[tuple[str, AuditScope], CalculatedMetric] = {}
    overall = AuditScope.overall()
    output.extend(_calculate_scope(data, config, overall, tuple(range(len(data.favorable_outcome)))))

    for attribute in sorted(config.protected_attributes):
        values = sorted(config.allowed_groups[attribute], key=canonical_typed_token)
        for value in values:
            scope = AuditScope(((attribute, value),))
            indices = tuple(
                index
                for index, observed in enumerate(data.protected_values[attribute])
                if type(observed) is type(value) and observed == value
            )
            metrics = _calculate_scope(data, config, scope, indices)
            output.extend(metrics)
            for item in metrics:
                scope_results[(item.metric.value, scope)] = item

        reference_value = config.reference_groups[attribute]
        reference_scope = AuditScope(((attribute, reference_value),))
        for comparison_value in values:
            if type(comparison_value) is type(reference_value) and comparison_value == reference_value:
                continue
            comparison_scope = AuditScope(((attribute, comparison_value),))
            output.extend(
                _calculate_comparison(scope_results, comparison_scope, reference_scope)
            )
    return tuple(output)


def _calculate_scope(
    data: NormalizedAuditData,
    config: AuditConfig,
    scope: AuditScope,
    indices: tuple[int, ...],
) -> tuple[CalculatedMetric, ...]:
    outcomes = tuple(data.favorable_outcome[index] for index in indices)
    decisions = tuple(data.favorable_decision[index] for index in indices)
    scores = tuple(data.favorable_score[index] for index in indices)
    weights = None if data.weights is None else tuple(data.weights[index] for index in indices)
    values = {
        MetricNameV2.SELECTION_RATE: selection_rate(decisions, weights),
        MetricNameV2.DENIAL_RATE: denial_rate(decisions, weights),
        MetricNameV2.ACCURACY: accuracy(outcomes, decisions, weights),
        MetricNameV2.PRECISION: precision(outcomes, decisions, weights),
        MetricNameV2.TRUE_POSITIVE_RATE: true_positive_rate(outcomes, decisions, weights),
        MetricNameV2.FALSE_POSITIVE_RATE: false_positive_rate(outcomes, decisions, weights),
        MetricNameV2.FALSE_NEGATIVE_RATE: false_negative_rate(outcomes, decisions, weights),
        MetricNameV2.BRIER_SCORE: (
            brier_score(outcomes, scores, weights)
            if config.score_type.value == "probability"
            else MetricValue(None, None, None, "metric_not_applicable")
        ),
        MetricNameV2.ROC_AUC: roc_auc(outcomes, scores, weights),
    }
    return tuple(
        CalculatedMetric(
            key=canonical_metric_key(metric, group=scope),
            metric=metric,
            value=values[metric],
            sample_count=len(indices),
            group=scope,
        )
        for metric in SCOPE_METRIC_ORDER
    )


def _calculate_comparison(
    scope_results: Mapping[
        tuple[str, AuditScope], CalculatedMetric
    ],
    comparison_scope: AuditScope,
    reference_scope: AuditScope,
) -> tuple[CalculatedMetric, ...]:
    def source(metric: MetricNameV2, scope: AuditScope) -> CalculatedMetric:
        return scope_results[(metric.value, scope)]

    comparison_selection = source(MetricNameV2.SELECTION_RATE, comparison_scope)
    reference_selection = source(MetricNameV2.SELECTION_RATE, reference_scope)
    comparison_tpr = source(MetricNameV2.TRUE_POSITIVE_RATE, comparison_scope)
    reference_tpr = source(MetricNameV2.TRUE_POSITIVE_RATE, reference_scope)
    comparison_fpr = source(MetricNameV2.FALSE_POSITIVE_RATE, comparison_scope)
    reference_fpr = source(MetricNameV2.FALSE_POSITIVE_RATE, reference_scope)
    values = {
        MetricNameV2.SELECTION_RATE_DIFFERENCE: selection_rate_difference(
            comparison_selection.value, reference_selection.value
        ),
        MetricNameV2.ADVERSE_IMPACT_RATIO: adverse_impact_ratio(
            comparison_selection.value, reference_selection.value
        ),
        MetricNameV2.DEMOGRAPHIC_PARITY_DIFFERENCE: demographic_parity_difference(
            comparison_selection.value, reference_selection.value
        ),
        MetricNameV2.EQUAL_OPPORTUNITY_DIFFERENCE: equal_opportunity_difference(
            comparison_tpr.value, reference_tpr.value
        ),
        MetricNameV2.EQUALIZED_ODDS_GAP: equalized_odds_gap(
            comparison_tpr.value,
            reference_tpr.value,
            comparison_fpr.value,
            reference_fpr.value,
        ),
    }
    sample_count = comparison_selection.sample_count + reference_selection.sample_count
    return tuple(
        CalculatedMetric(
            key=canonical_metric_key(
                metric,
                comparison_group=comparison_scope,
                reference_group=reference_scope,
            ),
            metric=metric,
            value=values[metric],
            sample_count=sample_count,
            comparison_group=comparison_scope,
            reference_group=reference_scope,
        )
        for metric in COMPARISON_METRIC_ORDER
    )
