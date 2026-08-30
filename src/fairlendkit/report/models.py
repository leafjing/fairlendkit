"""Versioned, renderer-neutral audit result models."""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from fairlendkit.config import AuditConfig
from fairlendkit.config.models import Label
from fairlendkit.metrics import MetricValue

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


class AuditGroup(ResultModel):
    """Explicit attribute values identifying one audit group."""

    attributes: dict[str, Label] = Field(min_length=1)


class ObservedMetric(ResultModel):
    """A final observed value; renderers must not receive raw prediction data."""

    key: Identifier
    metric: MetricName
    value: MetricValue
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
        elif self.comparison_group is not None or self.reference_group is not None:
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

    @model_validator(mode="after")
    def validate_counts(self) -> "ValidationEvidence":
        excluded_rows = sum(record.count for record in self.exclusions)
        if self.analyzed_rows + excluded_rows != self.input_rows:
            raise ValueError(
                "analyzed rows plus exclusion counts must equal input rows"
            )
        return self


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
