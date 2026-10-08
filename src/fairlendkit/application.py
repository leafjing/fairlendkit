"""Public audit use case and default composition root."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Protocol

from fairlendkit.config import AuditConfig
from fairlendkit.data.contracts import LayeredValidationResult
from fairlendkit.metrics.contracts import (
    CANONICAL_UNDEFINED_MESSAGES_V2,
    ComparisonUncertaintyRequest,
    MetricNameV2,
    UncertaintyEstimator,
    UncertaintyRequest,
    UndefinedReasonCodeV2,
)
from fairlendkit.metrics.group import (
    AuditScope,
    CalculatedMetric,
    NormalizedAuditData,
    calculate_group_metrics,
)
from fairlendkit.metrics.reliability import (
    AssessedMetric,
    MetricLimitation,
    assess_reliability,
    estimate_uncertainty,
    make_air_flags,
)
from fairlendkit.report.models import (
    AUDIT_RESULT_SCHEMA_VERSION_V2,
    AuditGroup,
    AuditResultV2,
    ExclusionRecord,
    LimitationV2,
    ObservedMetricV2,
    ReliabilityStateV2,
    ReportedMetricValueV2,
    RunMetadataV2,
    ScreeningFlag,
    StatisticalUncertainty,
    UndefinedReasonV2,
    to_validation_evidence,
)


class AuditDataAdapter(Protocol):
    def prepare(self, data: object, config: AuditConfig) -> "PreparedAuditData": ...


@dataclass(frozen=True)
class PreparedAuditData:
    validation: LayeredValidationResult
    normalized: NormalizedAuditData
    fingerprint: str


@dataclass(frozen=True)
class RunAudit:
    adapter: AuditDataAdapter
    uncertainty_estimator: UncertaintyEstimator

    def __call__(self, data: object, config: AuditConfig) -> AuditResultV2:
        if not isinstance(config, AuditConfig):
            raise TypeError("config must be AuditConfig")
        prepared = self.adapter.prepare(data, config)
        validation = prepared.validation
        normalized = prepared.normalized
        calculated = calculate_group_metrics(normalized, config)
        assessed, point_limitations = assess_reliability(calculated, normalized, config)
        requests = _uncertainty_requests(assessed, normalized, config)
        intervals, interval_limitations = estimate_uncertainty(assessed, requests, self.uncertainty_estimator)
        limitations = (*point_limitations, *interval_limitations)
        result = AuditResultV2(
            schema_version=AUDIT_RESULT_SCHEMA_VERSION_V2,
            metadata=RunMetadataV2(
                data_fingerprint=prepared.fingerprint,
                package_version=_package_version(),
                generated_at=config.execution_timestamp,
                configuration=config,
                migrated_from_schema_version=None,
            ),
            validation=to_validation_evidence(
                validation,
                exclusions=_exclusions(validation.reason_counts, validation.excluded_rows),
                warnings=(),
            ),
            observed_metrics=tuple(_observed(item) for item in assessed),
            screening_flags=tuple(
                ScreeningFlag(
                    code=flag.code,
                    related_metric_key=flag.metric_key,
                    observed_value=flag.observed_value,
                    threshold=flag.threshold,
                    condition=flag.condition,
                ) for flag in make_air_flags(assessed, config)
            ),
            uncertainty=tuple(
                StatisticalUncertainty(
                    metric_key=item.metric_key,
                    method="bootstrap_percentile",
                    confidence_level=item.confidence_level,
                    lower=item.lower,
                    upper=item.upper,
                    resamples=item.valid_resamples,
                ) for item in intervals
            ),
            limitations=tuple(_limitation(item) for item in limitations),
            practitioner_review_notes=(),
        )
        if any(item.reliability == ReliabilityStateV2.NOT_ASSESSED for item in result.observed_metrics):
            raise ValueError("native results cannot contain not_assessed reliability")
        if any(not item.affected_metric_keys for item in result.limitations):
            raise ValueError("native limitations require affected metric keys")
        return result


def _observed(item: AssessedMetric) -> ObservedMetricV2:
    metric = item.calculated
    reason = metric.value.undefined_reason
    value = ReportedMetricValueV2(
        value=metric.value.value,
        numerator=metric.value.numerator,
        denominator=metric.value.denominator,
        undefined_reason=None if reason is None else UndefinedReasonV2(
            code=UndefinedReasonCodeV2(reason),
            message=CANONICAL_UNDEFINED_MESSAGES_V2[UndefinedReasonCodeV2(reason)],
        ),
    )
    return ObservedMetricV2(
        key=metric.key, metric=metric.metric, value=value,
        sample_count=metric.sample_count, reliability=ReliabilityStateV2(item.reliability.value),
        group=_group(metric.group), comparison_group=_group(metric.comparison_group), reference_group=_group(metric.reference_group),
    )


def _group(scope: AuditScope | None) -> AuditGroup | None:
    return None if scope is None else AuditGroup(attributes=dict(scope.attributes))


def _limitation(item: MetricLimitation) -> LimitationV2:
    messages = {
        "small_group": "The evaluated group has fewer records than the configured minimum.",
        "severe_outcome_imbalance": "At least one outcome class has fewer records than the configured minimum.",
        "sparse_decision_support": "Favorable-decision support is below the configured minimum.",
        "insufficient_valid_resamples": "Too few valid bootstrap resamples were available for an interval.",
    }
    return LimitationV2(code=item.code, detail=messages[item.code.value], affected_metric_keys=item.affected_metric_keys)


def _uncertainty_requests(assessed: tuple[AssessedMetric, ...], data: NormalizedAuditData, config: AuditConfig):
    requests = []
    for item in assessed:
        if item.reliability.value != "reliable" or item.calculated.metric == MetricNameV2.DEMOGRAPHIC_PARITY_DIFFERENCE:
            continue
        metric = item.calculated
        if metric.group is not None:
            indices = _indices(metric.group, data)
            requests.append(UncertaintyRequest(
                metric_key=metric.key, population_size=len(indices), seed=config.bootstrap_seed,
                resamples=config.bootstrap_resamples, minimum_valid_resamples=config.minimum_valid_resamples,
                confidence_level=config.confidence_level, stream_role="scope",
                evaluator=_scope_evaluator(metric, data, config, indices),
            ))
        else:
            comparison = _indices(metric.comparison_group, data)
            reference = _indices(metric.reference_group, data)
            requests.append(ComparisonUncertaintyRequest(
                metric_key=metric.key, comparison_size=len(comparison), reference_size=len(reference),
                seed=config.bootstrap_seed, resamples=config.bootstrap_resamples,
                minimum_valid_resamples=config.minimum_valid_resamples, confidence_level=config.confidence_level,
                evaluator=_comparison_evaluator(metric, data, config, comparison, reference),
            ))
    return tuple(requests)


def _scope_evaluator(metric: CalculatedMetric, data: NormalizedAuditData, config: AuditConfig, source: tuple[int, ...]):
    def evaluate(draw: tuple[int, ...]) -> float | None:
        sampled = _take(data, tuple(source[index] for index in draw))
        found = calculate_group_metrics(sampled, config)
        return next(item.value.value for item in found if item.group is not None and item.group.attributes == (("__scope__", "overall"),) and item.metric == metric.metric)
    return evaluate


def _comparison_evaluator(metric: CalculatedMetric, data: NormalizedAuditData, config: AuditConfig, left: tuple[int, ...], right: tuple[int, ...]):
    def evaluate(left_draw: tuple[int, ...], right_draw: tuple[int, ...]) -> float | None:
        sampled = _take(data, tuple(left[index] for index in left_draw) + tuple(right[index] for index in right_draw))
        found = calculate_group_metrics(sampled, config)
        return next(item.value.value for item in found if item.metric == metric.metric and item.comparison_group is not None and item.reference_group is not None and item.comparison_group.attributes == metric.comparison_group.attributes and item.reference_group.attributes == metric.reference_group.attributes)
    return evaluate


def _take(data: NormalizedAuditData, indices: tuple[int, ...]) -> NormalizedAuditData:
    return NormalizedAuditData(
        favorable_outcome=tuple(data.favorable_outcome[i] for i in indices), favorable_decision=tuple(data.favorable_decision[i] for i in indices),
        favorable_score=tuple(data.favorable_score[i] for i in indices), protected_values={k: tuple(v[i] for i in indices) for k, v in data.protected_values.items()},
        weights=None if data.weights is None else tuple(data.weights[i] for i in indices),
    )


def _indices(scope: AuditScope | None, data: NormalizedAuditData) -> tuple[int, ...]:
    assert scope is not None
    if scope.attributes == (("__scope__", "overall"),):
        return tuple(range(len(data.favorable_outcome)))
    attribute, value = scope.attributes[0]
    return tuple(i for i, observed in enumerate(data.protected_values[attribute]) if _typed_equal(observed, value))


def _typed_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _exclusions(reason_counts: tuple[tuple[str, int], ...], excluded_rows: int) -> tuple[ExclusionRecord, ...]:
    """Project overlapping reason hits onto deterministic de-duplicated records."""

    remaining = excluded_rows
    records = []
    for code, hits in reason_counts:
        count = min(hits, remaining)
        if count:
            records.append(ExclusionRecord(code=code, count=count))
            remaining -= count
    if remaining:
        raise ValueError("validation reason counts do not cover excluded rows")
    return tuple(records)


def _package_version() -> str:
    try: return version("fairlendkit")
    except PackageNotFoundError: return "0+unknown"
