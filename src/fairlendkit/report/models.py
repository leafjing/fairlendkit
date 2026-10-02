"""Versioned, renderer-neutral audit result models."""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from fairlendkit.config import AuditConfig
from fairlendkit.config.models import Label
from fairlendkit.data.contracts import (
    APPLICABILITY_STATEMENT,
    BaselineComparisonResult,
    LayeredValidationResult,
    SingleRunProfile,
    ValidationLayerId,
    ValidationLayerResult,
    ValidationIssueEvidence,
    ValidationStatus,
    aggregate_validation_status,
    issue_sort_key,
    make_issue,
)

AUDIT_RESULT_SCHEMA_VERSION = "1.0"
Identifier = Annotated[str, Field(min_length=1, pattern=r"^[a-z][a-z0-9_.-]*$")]


class ResultModel(BaseModel):
    """Strict immutable base for report contract records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricName(StrEnum):
    SELECTION_RATE = "selection_rate"
    ACCURACY = "accuracy"
    TRUE_POSITIVE_RATE = "true_positive_rate"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_NEGATIVE_RATE = "false_negative_rate"
    BRIER_SCORE = "brier_score"
    ADVERSE_IMPACT_RATIO = "adverse_impact_ratio"
    DEMOGRAPHIC_PARITY_DIFFERENCE = "demographic_parity_difference"
    EQUAL_OPPORTUNITY_DIFFERENCE = "equal_opportunity_difference"


class UncertaintyMethod(StrEnum):
    BOOTSTRAP_PERCENTILE = "bootstrap_percentile"


class UndefinedReasonCode(StrEnum):
    EMPTY_POPULATION = "empty_population"
    ZERO_TOTAL_WEIGHT = "zero_total_weight"
    NO_FAVORABLE_OUTCOMES = "no_favorable_outcomes"
    ZERO_FAVORABLE_OUTCOME_WEIGHT = "zero_favorable_outcome_weight"
    NO_UNFAVORABLE_OUTCOMES = "no_unfavorable_outcomes"
    ZERO_UNFAVORABLE_OUTCOME_WEIGHT = "zero_unfavorable_outcome_weight"
    COMPARISON_METRIC_UNDEFINED = "comparison_metric_undefined"
    REFERENCE_METRIC_UNDEFINED = "reference_metric_undefined"
    ZERO_REFERENCE_SELECTION_RATE = "zero_reference_selection_rate"


CANONICAL_UNDEFINED_MESSAGES = {
    UndefinedReasonCode.EMPTY_POPULATION: "No records are available for this metric.",
    UndefinedReasonCode.ZERO_TOTAL_WEIGHT: (
        "The metric population has no positive total weight."
    ),
    UndefinedReasonCode.NO_FAVORABLE_OUTCOMES: (
        "No favorable observed outcomes are available for this metric."
    ),
    UndefinedReasonCode.ZERO_FAVORABLE_OUTCOME_WEIGHT: (
        "Favorable observed outcomes have no positive total weight."
    ),
    UndefinedReasonCode.NO_UNFAVORABLE_OUTCOMES: (
        "No unfavorable observed outcomes are available for this metric."
    ),
    UndefinedReasonCode.ZERO_UNFAVORABLE_OUTCOME_WEIGHT: (
        "Unfavorable observed outcomes have no positive total weight."
    ),
    UndefinedReasonCode.COMPARISON_METRIC_UNDEFINED: (
        "The comparison-group input metric is undefined."
    ),
    UndefinedReasonCode.REFERENCE_METRIC_UNDEFINED: (
        "The reference-group input metric is undefined."
    ),
    UndefinedReasonCode.ZERO_REFERENCE_SELECTION_RATE: (
        "The reference-group selection rate is zero, so the ratio is undefined."
    ),
}


class UndefinedReason(ResultModel):
    """Closed reason code paired with its canonical neutral message."""

    code: UndefinedReasonCode
    message: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_canonical_message(self) -> "UndefinedReason":
        expected = CANONICAL_UNDEFINED_MESSAGES[self.code]
        if self.message != expected:
            raise ValueError(f"message must match canonical text for {self.code.value!r}")
        return self


class ReportedMetricValue(ResultModel):
    """Finite value or structured undefined reason stored in AuditResult."""

    value: float | None
    numerator: float | None
    denominator: float | None
    undefined_reason: UndefinedReason | None

    @model_validator(mode="after")
    def validate_state(self) -> "ReportedMetricValue":
        for name, evidence in (
            ("numerator", self.numerator),
            ("denominator", self.denominator),
        ):
            if evidence is not None and not math.isfinite(evidence):
                raise ValueError(f"{name} must be finite or null")
        if self.value is None:
            if self.undefined_reason is None:
                raise ValueError("an undefined value requires undefined_reason")
        else:
            if not math.isfinite(self.value):
                raise ValueError("a defined value must be finite")
            if self.undefined_reason is not None:
                raise ValueError("a defined value cannot have undefined_reason")
        return self

    @property
    def is_defined(self) -> bool:
        return self.value is not None


class AuditGroup(ResultModel):
    """Explicit attribute values identifying one audit group."""

    attributes: dict[str, Label] = Field(min_length=1)


class ObservedMetric(ResultModel):
    """A final observed value; renderers must not receive raw prediction data."""

    key: Identifier
    metric: MetricName
    value: ReportedMetricValue
    sample_count: int = Field(ge=0)
    group: AuditGroup | None = None
    comparison_group: AuditGroup | None = None
    reference_group: AuditGroup | None = None

    @model_validator(mode="after")
    def validate_group_direction(self) -> "ObservedMetric":
        disparity_metrics = {
            MetricName.ADVERSE_IMPACT_RATIO,
            MetricName.DEMOGRAPHIC_PARITY_DIFFERENCE,
            MetricName.EQUAL_OPPORTUNITY_DIFFERENCE,
        }
        if self.metric in disparity_metrics:
            if self.comparison_group is None or self.reference_group is None:
                raise ValueError(
                    "disparity metrics require comparison_group and reference_group"
                )
            if self.group is not None:
                raise ValueError("disparity metrics cannot also set group")
        else:
            if self.group is None:
                raise ValueError("non-disparity metrics require group")
            if self.comparison_group is not None or self.reference_group is not None:
                raise ValueError(
                    "non-disparity metrics use group, not comparison/reference groups"
                )
        if self.sample_count == 0 and self.value.is_defined:
            raise ValueError("a metric with sample_count zero must be undefined")
        if self.value.value is not None:
            ranges = {
                MetricName.SELECTION_RATE: (0.0, 1.0),
                MetricName.ACCURACY: (0.0, 1.0),
                MetricName.TRUE_POSITIVE_RATE: (0.0, 1.0),
                MetricName.FALSE_POSITIVE_RATE: (0.0, 1.0),
                MetricName.FALSE_NEGATIVE_RATE: (0.0, 1.0),
                MetricName.BRIER_SCORE: (0.0, 1.0),
                MetricName.ADVERSE_IMPACT_RATIO: (0.0, math.inf),
                MetricName.DEMOGRAPHIC_PARITY_DIFFERENCE: (-1.0, 1.0),
                MetricName.EQUAL_OPPORTUNITY_DIFFERENCE: (-1.0, 1.0),
            }
            lower, upper = ranges[self.metric]
            if not lower <= self.value.value <= upper:
                raise ValueError(
                    f"{self.metric.value} must be within [{lower}, {upper}]"
                )
        return self


class ScreeningFlag(ResultModel):
    """A typed review prompt, never an automated compliance conclusion."""

    code: Identifier
    related_metric_key: Identifier | None = None
    observed_value: float
    threshold: float
    condition: Literal["below", "at_or_below", "above", "at_or_above"]
    requires_practitioner_review: Literal[True] = True

    @model_validator(mode="after")
    def validate_finite_values(self) -> "ScreeningFlag":
        for name, value in (
            ("observed_value", self.observed_value),
            ("threshold", self.threshold),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        return self


class StatisticalUncertainty(ResultModel):
    """Uncertainty attached to one observed metric key."""

    metric_key: Identifier
    method: UncertaintyMethod
    confidence_level: float = Field(gt=0.0, lt=1.0)
    lower: float
    upper: float
    resamples: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_interval(self) -> "StatisticalUncertainty":
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("uncertainty bounds must be finite")
        if self.lower > self.upper:
            raise ValueError("uncertainty lower bound cannot exceed upper bound")
        return self


class ExclusionRecord(ResultModel):
    code: Identifier
    count: int = Field(ge=1)


class WarningRecord(ResultModel):
    code: Identifier
    message: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def reject_automated_verdict(self) -> "WarningRecord":
        _reject_automated_verdict(self.message)
        return self


class ValidationEvidence(ResultModel):
    input_rows: int = Field(ge=0)
    analyzed_rows: int = Field(ge=0)
    exclusions: tuple[ExclusionRecord, ...]
    warnings: tuple[WarningRecord, ...]
    status: ValidationStatus
    technical_validation: ValidationStatus
    applicability: Literal["not_assessed"]
    applicability_statement: Literal[APPLICABILITY_STATEMENT]
    reason_counts: tuple[tuple[str, int], ...]
    duplicate_rows: int = Field(ge=0)
    small_groups: tuple[str, ...]
    layers: tuple[ValidationLayerResult, ...]
    profile: SingleRunProfile | None = None
    comparison: BaselineComparisonResult | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_flat_v1_validation(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "layers" in value:
            if "comparison" in value:
                return value
            migrated = {**value, "comparison": None}
            layers = [dict(layer) for layer in migrated["layers"]]
            data_quality = layers[-1]
            data_quality["issues"] = tuple(
                issue for issue in data_quality.get("issues", ())
                if issue.get("code") != "comparison_baseline_unavailable"
            )
            if not data_quality["issues"]:
                data_quality["status"] = "passed"
            migrated["layers"] = tuple(layers)
            return migrated
        migrated = dict(value)
        warnings = migrated.get("warnings", ())
        # Released flat fixtures had no typed mapping from arbitrary warning codes.
        # Preserve their aggregate state under one bounded compatibility issue.
        data_quality_issues = []
        if warnings:
            data_quality_issues.append(
                make_issue(
                    "legacy_validation_warning",
                    evidence=ValidationIssueEvidence(count=len(warnings)),
                )
            )
        data_quality_issues.sort(key=issue_sort_key)
        layers = (
            ValidationLayerResult(layer="structural", status="passed", issues=()),
            ValidationLayerResult(layer="semantic", status="passed", issues=()),
            ValidationLayerResult(layer="analytical_reliability", status="passed", issues=()),
            ValidationLayerResult(
                layer="data_quality",
                status="warning" if warnings else "passed",
                issues=tuple(data_quality_issues),
            ),
        )
        migrated.update(
            status="passed" if not warnings else "warning",
            technical_validation="passed",
            applicability="not_assessed",
            applicability_statement=APPLICABILITY_STATEMENT,
            reason_counts=tuple(sorted((item["code"], item["count"]) for item in migrated.get("exclusions", ()))),
            duplicate_rows=0,
            small_groups=(),
            layers=layers,
            profile=None,
            comparison=None,
        )
        return migrated

    @model_validator(mode="after")
    def validate_counts(self) -> "ValidationEvidence":
        excluded_rows = sum(record.count for record in self.exclusions)
        if self.analyzed_rows + excluded_rows != self.input_rows:
            raise ValueError(
                "analyzed rows plus exclusion counts must equal input rows"
            )
        if tuple(layer.layer for layer in self.layers) != tuple(ValidationLayerId):
            raise ValueError("validation layers must use canonical order")
        layer_status = {layer.layer: layer.status for layer in self.layers}
        expected_technical = aggregate_validation_status(
            (
                layer_status[ValidationLayerId.STRUCTURAL],
                layer_status[ValidationLayerId.SEMANTIC],
            )
        )
        if self.technical_validation != expected_technical:
            raise ValueError("technical_validation must derive from structural and semantic layers")
        if self.technical_validation == ValidationStatus.FAILED:
            raise ValueError("AuditResult cannot contain failed technical validation")
        expected_status = aggregate_validation_status(
            tuple(layer.status for layer in self.layers)
        )
        if self.status != expected_status:
            raise ValueError("validation status must derive from all four layers")
        if self.profile is not None:
            excluded_rows = self.input_rows - self.analyzed_rows
            if (self.profile.input_rows, self.profile.eligible_rows, self.profile.excluded_rows) != (self.input_rows, self.analyzed_rows, excluded_rows):
                raise ValueError("profile row counts must match validation evidence")
            data_quality = next(layer for layer in self.layers if layer.layer == ValidationLayerId.DATA_QUALITY)
            comparison_issues = () if self.comparison is None else self.comparison.issues
            expected_issues = tuple(sorted((*self.profile.issues, *comparison_issues), key=issue_sort_key))
            if data_quality.issues != expected_issues:
                raise ValueError("data-quality layer must contain canonical profile/comparison issues")
            if self.comparison is not None:
                from fairlendkit.data.comparison import canonical_profile_digest
                if canonical_profile_digest(self.profile) != self.comparison.current_profile_digest:
                    raise ValueError("comparison profile digest must match report profile")
        return self

    @property
    def eligible_rows(self) -> int:
        return self.analyzed_rows


def to_validation_evidence(
    validation: LayeredValidationResult,
    *,
    exclusions: tuple[ExclusionRecord, ...],
    warnings: tuple[WarningRecord, ...],
) -> ValidationEvidence:
    """Project domain validation evidence into the report contract."""
    if sum(record.count for record in exclusions) != validation.excluded_rows:
        raise ValueError("report exclusions must reconcile to domain excluded_rows")
    reason_counts = dict(validation.reason_counts)
    if any(record.code not in reason_counts or record.count > reason_counts[record.code] for record in exclusions):
        raise ValueError("report exclusions must be supported by domain reason counts")
    return ValidationEvidence(
        input_rows=validation.input_rows,
        analyzed_rows=validation.eligible_rows,
        exclusions=exclusions,
        warnings=warnings,
        status=validation.status,
        technical_validation=validation.technical_validation,
        applicability=validation.applicability,
        applicability_statement=validation.applicability_statement,
        reason_counts=validation.reason_counts,
        duplicate_rows=validation.duplicate_rows,
        small_groups=validation.small_groups,
        layers=validation.layers,
        profile=validation.profile,
        comparison=validation.comparison,
    )


class Limitation(ResultModel):
    code: Identifier
    detail: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def reject_automated_verdict(self) -> "Limitation":
        _reject_automated_verdict(self.detail)
        return self


class PractitionerReviewNote(ResultModel):
    """Human-authored note kept separate from automated report sections."""

    author: Annotated[str, Field(min_length=1)]
    recorded_at: AwareDatetime
    text: Annotated[str, Field(min_length=1)]
    source: Literal["practitioner"] = "practitioner"


class RunMetadata(ResultModel):
    data_fingerprint: Annotated[
        str, Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ]
    package_version: Annotated[str, Field(min_length=1)]
    generated_at: AwareDatetime
    configuration: AuditConfig


class AuditResult(ResultModel):
    """The only supported input contract for report renderers."""

    schema_version: Literal["1.0"]
    metadata: RunMetadata
    validation: ValidationEvidence
    observed_metrics: tuple[ObservedMetric, ...]
    screening_flags: tuple[ScreeningFlag, ...]
    uncertainty: tuple[StatisticalUncertainty, ...]
    limitations: tuple[Limitation, ...]
    practitioner_review_notes: tuple[PractitionerReviewNote, ...]

    @model_validator(mode="after")
    def validate_references(self) -> "AuditResult":
        metric_keys = [metric.key for metric in self.observed_metrics]
        if len(metric_keys) != len(set(metric_keys)):
            raise ValueError("observed metric keys must be unique")
        known_keys = set(metric_keys)
        for item in self.uncertainty:
            if item.metric_key not in known_keys:
                raise ValueError(
                    f"uncertainty references unknown metric key {item.metric_key!r}"
                )
        for flag in self.screening_flags:
            if (
                flag.related_metric_key is not None
                and flag.related_metric_key not in known_keys
            ):
                raise ValueError(
                    "screening flag references unknown metric key "
                    f"{flag.related_metric_key!r}"
                )
        return self


def _reject_automated_verdict(text: str) -> None:
    verdict_patterns = (
        r"\b(?:is|are|deemed|found)\s+(?:non[- ]?)?compliant\b",
        r"\bnon[- ]compliant\b",
        r"\b(?:is|are|deemed|found)\s+(?:il)?legal\b",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in verdict_patterns):
        raise ValueError(
            "automated warnings and limitations cannot state compliance or legal verdicts"
        )
