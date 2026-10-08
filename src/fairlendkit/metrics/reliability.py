"""Canonical Milestone 3 reliability policy and AIR screening gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fairlendkit.config import AuditConfig
from fairlendkit.metrics.contracts import (
    BootstrapInterval,
    LimitationCode,
    MetricNameV2,
)
from fairlendkit.metrics.group import (
    AuditScope,
    CalculatedMetric,
    NormalizedAuditData,
    canonical_metric_key,
    scope_key,
)

GATE_ORDER = (
    LimitationCode.SMALL_GROUP,
    LimitationCode.SEVERE_OUTCOME_IMBALANCE,
    LimitationCode.SPARSE_DECISION_SUPPORT,
    LimitationCode.INSUFFICIENT_VALID_RESAMPLES,
)


class ReliabilityState(StrEnum):
    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"
    UNDEFINED = "undefined"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class AssessedMetric:
    calculated: CalculatedMetric
    reliability: ReliabilityState
    limitation_codes: tuple[LimitationCode, ...]


@dataclass(frozen=True)
class MetricLimitation:
    code: LimitationCode
    scope_id: str
    affected_metric_keys: tuple[str, ...]


@dataclass(frozen=True)
class AirScreeningFlag:
    code: str
    metric_key: str
    observed_value: float
    threshold: float
    condition: str = "below"
    requires_practitioner_review: bool = True


_SMALL_ONLY = {MetricNameV2.SELECTION_RATE, MetricNameV2.DENIAL_RATE}
_OUTCOME_GATED = {
    MetricNameV2.ACCURACY,
    MetricNameV2.PRECISION,
    MetricNameV2.TRUE_POSITIVE_RATE,
    MetricNameV2.FALSE_POSITIVE_RATE,
    MetricNameV2.FALSE_NEGATIVE_RATE,
    MetricNameV2.BRIER_SCORE,
    MetricNameV2.ROC_AUC,
}


def assess_reliability(
    metrics: tuple[CalculatedMetric, ...],
    data: NormalizedAuditData,
    config: AuditConfig,
) -> tuple[tuple[AssessedMetric, ...], tuple[MetricLimitation, ...]]:
    """Apply the frozen gate matrix without changing point estimates."""

    assessed_by_key: dict[str, AssessedMetric] = {}
    output: list[AssessedMetric] = []
    for metric in metrics:
        if metric.group is not None:
            codes = _scope_gate_codes(metric, data, config)
        else:
            codes = _comparison_gate_codes(metric, assessed_by_key)
        if not metric.value.is_defined:
            state = (
                ReliabilityState.NOT_APPLICABLE
                if metric.value.undefined_reason == "metric_not_applicable"
                else ReliabilityState.UNDEFINED
            )
            codes = ()
        else:
            state = ReliabilityState.UNRELIABLE if codes else ReliabilityState.RELIABLE
        item = AssessedMetric(metric, state, codes)
        assessed_by_key[metric.key] = item
        output.append(item)

    limitations: list[MetricLimitation] = []
    buckets: dict[tuple[str, LimitationCode], list[str]] = {}
    for item in output:
        scope_id = _scope_id(item.calculated)
        for code in item.limitation_codes:
            buckets.setdefault((scope_id, code), []).append(item.calculated.key)
    scope_order = {scope: index for index, scope in enumerate(dict.fromkeys(_scope_id(item.calculated) for item in output))}
    for (scope_id, code), keys in sorted(
        buckets.items(), key=lambda item: (scope_order[item[0][0]], GATE_ORDER.index(item[0][1]))
    ):
        limitations.append(MetricLimitation(code, scope_id, tuple(dict.fromkeys(keys))))
    return tuple(output), tuple(limitations)


def make_air_flags(
    assessed: tuple[AssessedMetric, ...], config: AuditConfig
) -> tuple[AirScreeningFlag, ...]:
    """Emit AIR flags only for defined, reliable below-threshold evidence."""

    return tuple(
        AirScreeningFlag(
            code="air_below_threshold",
            metric_key=item.calculated.key,
            observed_value=item.calculated.value.value,
            threshold=config.air_screening_threshold,
        )
        for item in assessed
        if item.calculated.metric == MetricNameV2.ADVERSE_IMPACT_RATIO
        and item.reliability == ReliabilityState.RELIABLE
        and item.calculated.value.value < config.air_screening_threshold
    )


def collect_uncertainty(
    assessed: tuple[AssessedMetric, ...],
    attempted: dict[str, BootstrapInterval | None],
) -> tuple[tuple[BootstrapInterval, ...], tuple[MetricLimitation, ...]]:
    """Collect intervals and typed failures without changing point reliability."""

    known = {item.calculated.key: item for item in assessed}
    if unknown := set(attempted) - set(known):
        raise ValueError(f"uncertainty references unknown metric keys: {sorted(unknown)!r}")
    intervals: list[BootstrapInterval] = []
    failed_by_scope: dict[str, list[str]] = {}
    for item in assessed:
        key = item.calculated.key
        if key not in attempted:
            continue
        if item.reliability != ReliabilityState.RELIABLE:
            raise ValueError("uncertainty may be attempted only for reliable metrics")
        interval = attempted[key]
        if interval is None:
            failed_by_scope.setdefault(_scope_id(item.calculated), []).append(key)
        else:
            if interval.metric_key != key:
                raise ValueError("uncertainty interval key must match its metric")
            intervals.append(interval)
    limitations = tuple(
        MetricLimitation(
            code=LimitationCode.INSUFFICIENT_VALID_RESAMPLES,
            scope_id=scope_id,
            affected_metric_keys=tuple(keys),
        )
        for scope_id, keys in failed_by_scope.items()
    )
    return tuple(intervals), limitations


def _scope_gate_codes(
    metric: CalculatedMetric, data: NormalizedAuditData, config: AuditConfig
) -> tuple[LimitationCode, ...]:
    assert metric.group is not None
    indices = _scope_indices(metric.group, data)
    codes: list[LimitationCode] = []
    if len(indices) < config.minimum_group_size:
        codes.append(LimitationCode.SMALL_GROUP)
    if metric.metric in _OUTCOME_GATED:
        favorable = sum(data.favorable_outcome[index] for index in indices)
        unfavorable = len(indices) - favorable
        if min(favorable, unfavorable) < config.minimum_group_size:
            codes.append(LimitationCode.SEVERE_OUTCOME_IMBALANCE)
    if metric.metric == MetricNameV2.PRECISION:
        decisions = sum(data.favorable_decision[index] for index in indices)
        if decisions < config.minimum_group_size:
            codes.append(LimitationCode.SPARSE_DECISION_SUPPORT)
    return tuple(code for code in GATE_ORDER if code in codes)


def _comparison_gate_codes(
    metric: CalculatedMetric, assessed: dict[str, AssessedMetric]
) -> tuple[LimitationCode, ...]:
    assert metric.comparison_group is not None and metric.reference_group is not None
    if metric.metric in {
        MetricNameV2.SELECTION_RATE_DIFFERENCE,
        MetricNameV2.ADVERSE_IMPACT_RATIO,
        MetricNameV2.DEMOGRAPHIC_PARITY_DIFFERENCE,
    }:
        source_metrics = (MetricNameV2.SELECTION_RATE,)
    elif metric.metric == MetricNameV2.EQUAL_OPPORTUNITY_DIFFERENCE:
        source_metrics = (MetricNameV2.TRUE_POSITIVE_RATE,)
    else:
        source_metrics = (MetricNameV2.TRUE_POSITIVE_RATE, MetricNameV2.FALSE_POSITIVE_RATE)
    codes = {
        code
        for source_metric in source_metrics
        for scope in (metric.comparison_group, metric.reference_group)
        for code in assessed[canonical_metric_key(source_metric, group=scope)].limitation_codes
    }
    return tuple(code for code in GATE_ORDER if code in codes)


def _scope_indices(scope: AuditScope, data: NormalizedAuditData) -> tuple[int, ...]:
    if scope.attributes == (("__scope__", "overall"),):
        return tuple(range(len(data.favorable_outcome)))
    attribute, value = scope.attributes[0]
    return tuple(
        index
        for index, observed in enumerate(data.protected_values[attribute])
        if type(observed) is type(value) and observed == value
    )


def _scope_id(metric: CalculatedMetric) -> str:
    if metric.group is not None:
        return repr(scope_key(metric.group))
    assert metric.comparison_group is not None and metric.reference_group is not None
    return f"{scope_key(metric.comparison_group)!r}.vs.{scope_key(metric.reference_group)!r}"
