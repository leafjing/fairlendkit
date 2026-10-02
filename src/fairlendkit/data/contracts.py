"""Framework-neutral contracts for exclusions and layered validation results."""

from __future__ import annotations

import math
import re
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

from fairlendkit.config.models import Label

VALIDATION_SCHEMA_VERSION = "1.0"
APPLICABILITY_STATEMENT = (
    "Technical validation does not determine fitness for use; applicability "
    "requires practitioner review."
)


class ExclusionReason(StrEnum):
    """Stable machine-readable reasons why a row is ineligible."""

    MISSING_REQUIRED_VALUE = "missing_required_value"
    UNKNOWN_PROTECTED_GROUP = "unknown_protected_group"
    DUPLICATE_RECORD = "duplicate_record"
    NON_FINITE_NUMERIC = "non_finite_numeric"
    UNEXPECTED_CATEGORY = "unexpected_category"


@dataclass(frozen=True)
class ExclusionEvidence:
    """Legacy aggregate evidence retained through V1."""

    reason: ExclusionReason
    count: int
    attribute: str | None = None
    observed_value: object | None = None


class ValidationStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationLayerId(StrEnum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    ANALYTICAL_RELIABILITY = "analytical_reliability"
    DATA_QUALITY = "data_quality"


LAYER_ORDER = tuple(ValidationLayerId)


@dataclass(frozen=True)
class IssueDefinition:
    layer: ValidationLayerId
    message: str
    severity: ValidationSeverity
    blocking: bool
    required_evidence: frozenset[str] = frozenset()
    allowed_evidence: frozenset[str] = frozenset()


ISSUE_REGISTRY: dict[str, IssueDefinition] = {
    "missing_required_column": IssueDefinition(ValidationLayerId.STRUCTURAL, "One or more required columns are missing.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "missing_required_value": IssueDefinition(ValidationLayerId.STRUCTURAL, "Required analysis values are missing.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "non_numeric_score": IssueDefinition(ValidationLayerId.STRUCTURAL, "The score column is not a non-boolean real numeric type.", ValidationSeverity.ERROR, True),
    "non_numeric_weight": IssueDefinition(ValidationLayerId.STRUCTURAL, "The sample-weight column is not a non-boolean real numeric type.", ValidationSeverity.ERROR, True),
    "negative_weight": IssueDefinition(ValidationLayerId.STRUCTURAL, "Sample weights contain negative values.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "non_positive_weight_total": IssueDefinition(ValidationLayerId.STRUCTURAL, "Eligible sample weights do not have a positive total.", ValidationSeverity.ERROR, True, frozenset({"total"}), frozenset({"total"})),
    "non_finite_numeric": IssueDefinition(ValidationLayerId.STRUCTURAL, "Numeric analysis values must be finite.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "duplicate_record": IssueDefinition(ValidationLayerId.STRUCTURAL, "Duplicate records were detected.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "non_unique_record_id": IssueDefinition(ValidationLayerId.STRUCTURAL, "Record identifiers are not unique in eligible data.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "unknown_protected_group": IssueDefinition(ValidationLayerId.STRUCTURAL, "Protected-group values outside the declared allowed set were observed.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "unexpected_category": IssueDefinition(ValidationLayerId.STRUCTURAL, "Values outside the declared expected categories were observed.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count"})),
    "no_eligible_rows": IssueDefinition(ValidationLayerId.STRUCTURAL, "No eligible rows remain after configured exclusions.", ValidationSeverity.ERROR, True, frozenset({"count"}), frozenset({"count", "reason_counts"})),
    "favorable_label_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "The configured favorable outcome label is absent from eligible data.", ValidationSeverity.ERROR, True, allowed_evidence=frozenset({"expected"})),
    "favorable_decision_label_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "The configured favorable decision label is absent from eligible data.", ValidationSeverity.ERROR, True, allowed_evidence=frozenset({"expected"})),
    "reference_group_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "A configured reference group is absent from eligible data.", ValidationSeverity.ERROR, True, allowed_evidence=frozenset({"expected"})),
    "ambiguous_column_role": IssueDefinition(ValidationLayerId.SEMANTIC, "A column has more than one declared semantic role.", ValidationSeverity.ERROR, True),
    "inconsistent_threshold_direction": IssueDefinition(ValidationLayerId.SEMANTIC, "The threshold operator is inconsistent with score direction.", ValidationSeverity.ERROR, True),
    "invalid_category_declaration": IssueDefinition(ValidationLayerId.SEMANTIC, "A category declaration is invalid.", ValidationSeverity.ERROR, True),
    "small_group": IssueDefinition(ValidationLayerId.ANALYTICAL_RELIABILITY, "An eligible protected group is below the configured minimum size.", ValidationSeverity.WARNING, False, frozenset({"count", "minimum"}), frozenset({"count", "minimum"})),
    "comparison_baseline_unavailable": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Comparison baseline evidence is unavailable.", ValidationSeverity.INFO, False),
    "comparison_baseline_incompatible": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Comparison baseline evidence is incompatible.", ValidationSeverity.INFO, False),
    "comparison_check_not_computable": IssueDefinition(ValidationLayerId.DATA_QUALITY, "One or more comparison checks could not be computed.", ValidationSeverity.INFO, False),
    "group_composition_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Eligible group composition changed by at least the configured threshold.", ValidationSeverity.WARNING, False),
    "missingness_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Missingness changed by at least the configured threshold.", ValidationSeverity.WARNING, False),
    "score_distribution_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Score distribution changed by at least the configured threshold.", ValidationSeverity.WARNING, False),
    "outcome_distribution_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Outcome distribution changed by at least the configured threshold.", ValidationSeverity.WARNING, False),
    "outcome_category_added": IssueDefinition(ValidationLayerId.DATA_QUALITY, "An outcome category is present only in the current profile.", ValidationSeverity.WARNING, False),
    "outcome_category_removed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "An outcome category is present only in the baseline profile.", ValidationSeverity.WARNING, False),
    "dataset_version_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "The dataset version changed from the selected baseline.", ValidationSeverity.INFO, False),
    "model_version_changed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "The model version changed from the selected baseline.", ValidationSeverity.INFO, False),
    "score_outliers_observed": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Eligible scores include values outside the declared Tukey fences.", ValidationSeverity.WARNING, False, frozenset({"count", "total", "minimum", "maximum"}), frozenset({"count", "total", "minimum", "maximum"})),
    "data_freshness_unavailable": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Data freshness was not evaluated because data_as_of is unavailable.", ValidationSeverity.INFO, False),
    "data_as_of_after_execution": IssueDefinition(ValidationLayerId.DATA_QUALITY, "data_as_of is later than execution_timestamp.", ValidationSeverity.WARNING, False, frozenset({"observed", "expected"}), frozenset({"observed", "expected"})),
    "legacy_validation_warning": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Legacy validation warnings are present.", ValidationSeverity.WARNING, False, frozenset({"count"}), frozenset({"count"})),
}


class ValidationContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


StrictCount = Annotated[StrictInt, Field(ge=0)]
FiniteNumber = Annotated[StrictFloat | StrictInt, Field(allow_inf_nan=False)]


class ValidationIssueEvidence(ValidationContractModel):
    count: StrictCount | None = None
    total: FiniteNumber | None = None
    observed: Label | tuple[Label, ...] | None = None
    expected: Label | tuple[Label, ...] | None = None
    minimum: FiniteNumber | None = None
    maximum: FiniteNumber | None = None
    reason_counts: dict[str, StrictCount] | None = None
    source_check_ids: tuple[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")], ...] = ()
    source_flag_ids: tuple[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")], ...] = ()

    @model_validator(mode="after")
    def validate_bounded_json_evidence(self) -> "ValidationIssueEvidence":
        for name in ("total", "minimum", "maximum"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not math.isfinite(value)):
                raise ValueError(f"{name} must be a finite number")
        if self.reason_counts is not None:
            if any(not re.fullmatch(r"[a-z][a-z0-9_]*", code) for code in self.reason_counts):
                raise ValueError("reason_counts must use stable lower-case codes")
            if any(isinstance(count, bool) or count < 0 for count in self.reason_counts.values()):
                raise ValueError("reason_counts values must be non-negative integers")
        if len(set(self.source_check_ids)) != len(self.source_check_ids) or len(set(self.source_flag_ids)) != len(self.source_flag_ids):
            raise ValueError("comparison evidence references must be unique")
        return self


class AffectedGroup(ValidationContractModel):
    attributes: dict[str, Label] = Field(min_length=1)

    @model_validator(mode="after")
    def sorted_attributes(self) -> "AffectedGroup":
        if tuple(self.attributes) != tuple(sorted(self.attributes)):
            raise ValueError("affected group attributes must be sorted")
        return self


class ValidationIssue(ValidationContractModel):
    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    severity: ValidationSeverity
    affected_fields: tuple[str, ...] = ()
    affected_groups: tuple[AffectedGroup, ...] = ()
    evidence: ValidationIssueEvidence
    message: str = Field(min_length=1)
    blocking: bool

    @model_validator(mode="after")
    def validate_registry(self) -> "ValidationIssue":
        definition = ISSUE_REGISTRY.get(self.code)
        if definition is None:
            raise ValueError(f"unregistered validation issue code {self.code!r}")
        policy_controlled = self.code in {"missing_required_value", "unknown_protected_group", "duplicate_record"}
        allowed_policy_state = policy_controlled and (self.severity, self.blocking) == (ValidationSeverity.WARNING, False)
        if self.message != definition.message or ((self.severity, self.blocking) != (definition.severity, definition.blocking) and not allowed_policy_state):
            raise ValueError(f"issue {self.code!r} must use its canonical message, severity, and blocking behavior")
        if self.affected_fields != tuple(sorted(set(self.affected_fields))):
            raise ValueError("affected_fields must be sorted and unique")
        group_keys = tuple(_group_sort_key(group) for group in self.affected_groups)
        if group_keys != tuple(sorted(set(group_keys))):
            raise ValueError("affected_groups must be sorted and unique")
        comparison_code = self.code.startswith("comparison_") or self.code in {
            "group_composition_changed", "missingness_changed", "score_distribution_changed",
            "outcome_distribution_changed", "outcome_category_added", "outcome_category_removed",
            "dataset_version_changed", "model_version_changed",
        }
        if not comparison_code and (self.evidence.source_check_ids or self.evidence.source_flag_ids):
            raise ValueError("non-comparison issues cannot contain comparison references")
        present = {
            name for name, value in self.evidence
            if value is not None and name not in {"source_check_ids", "source_flag_ids"}
        }
        missing = definition.required_evidence - present
        if missing:
            raise ValueError(f"issue {self.code!r} requires evidence: {', '.join(sorted(missing))}")
        unauthorized = present - definition.allowed_evidence
        if unauthorized:
            raise ValueError(f"issue {self.code!r} does not allow evidence: {', '.join(sorted(unauthorized))}")
        return self

    @property
    def layer(self) -> ValidationLayerId:
        return ISSUE_REGISTRY[self.code].layer


class ValidationLayerResult(ValidationContractModel):
    layer: ValidationLayerId
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]

    @model_validator(mode="after")
    def derive_status(self) -> "ValidationLayerResult":
        if any(issue.layer != self.layer for issue in self.issues):
            raise ValueError("an issue cannot be assigned outside its registered layer")
        if self.issues != tuple(sorted(self.issues, key=issue_sort_key)):
            raise ValueError("issues must use deterministic canonical order")
        expected = _layer_status(self.issues)
        if self.status != expected:
            raise ValueError(f"layer status must be derived as {expected.value!r}")
        return self


ProfilePopulation = Literal["input", "eligible"]


class MissingnessProfile(ValidationContractModel):
    field: Annotated[str, Field(min_length=1)]
    population: Literal["input"] = "input"
    group: AffectedGroup | None = None
    missing_count: StrictCount
    total_count: Annotated[StrictInt, Field(gt=0)]
    missing_rate: FiniteNumber = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_counts(self) -> "MissingnessProfile":
        if self.missing_count > self.total_count:
            raise ValueError("missing_count cannot exceed total_count")
        if float(self.missing_rate) != self.missing_count / self.total_count:
            raise ValueError("missing_rate must derive from counts")
        return self


class GroupSizeProfile(ValidationContractModel):
    group: AffectedGroup
    population: ProfilePopulation
    count: StrictCount
    total_count: Annotated[StrictInt, Field(gt=0)]
    proportion: FiniteNumber = Field(ge=0, le=1)
    is_reference: bool

    @model_validator(mode="after")
    def validate_counts(self) -> "GroupSizeProfile":
        if self.count > self.total_count:
            raise ValueError("count cannot exceed total_count")
        if float(self.proportion) != self.count / self.total_count:
            raise ValueError("proportion must derive from counts")
        return self


class AnomalyProfile(ValidationContractModel):
    code: ExclusionReason
    population: Literal["input"] = "input"
    count: StrictCount
    total_count: Annotated[StrictInt, Field(gt=0)]
    rate: FiniteNumber = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_counts(self) -> "AnomalyProfile":
        if self.count > self.total_count:
            raise ValueError("count cannot exceed total_count")
        if float(self.rate) != self.count / self.total_count:
            raise ValueError("rate must derive from counts")
        return self


class QuantileValue(ValidationContractModel):
    probability: FiniteNumber = Field(ge=0, le=1)
    value: FiniteNumber


class NumericDistributionProfile(ValidationContractModel):
    field: Annotated[str, Field(min_length=1)]
    population: Literal["eligible"] = "eligible"
    count: Annotated[StrictInt, Field(gt=0)]
    minimum: FiniteNumber
    maximum: FiniteNumber
    mean: FiniteNumber
    standard_deviation: FiniteNumber = Field(ge=0)
    quantiles: tuple[QuantileValue, ...]
    method: Literal["linear_type7"] = "linear_type7"

    @model_validator(mode="after")
    def validate_distribution(self) -> "NumericDistributionProfile":
        expected = (0.0, 0.25, 0.5, 0.75, 1.0)
        if tuple(float(item.probability) for item in self.quantiles) != expected:
            raise ValueError("quantiles must contain the fixed type-7 probabilities")
        values = tuple(float(item.value) for item in self.quantiles)
        if self.minimum > self.maximum or values != tuple(sorted(values)):
            raise ValueError("distribution values must be ordered")
        if float(self.minimum) != values[0] or float(self.maximum) != values[-1]:
            raise ValueError("minimum and maximum must match endpoint quantiles")
        if not self.minimum <= self.mean <= self.maximum:
            raise ValueError("mean must be within minimum and maximum")
        return self


class CategoryCount(ValidationContractModel):
    value: Label
    count: Annotated[StrictInt, Field(gt=0)]
    total_count: Annotated[StrictInt, Field(gt=0)]
    proportion: FiniteNumber = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_counts(self) -> "CategoryCount":
        if self.count > self.total_count:
            raise ValueError("count cannot exceed total_count")
        if float(self.proportion) != self.count / self.total_count:
            raise ValueError("proportion must derive from counts")
        return self


class OutlierProfile(ValidationContractModel):
    field: Annotated[str, Field(min_length=1)]
    population: Literal["eligible"] = "eligible"
    method: Literal["tukey_1_5_iqr"] = "tukey_1_5_iqr"
    q1: FiniteNumber
    q3: FiniteNumber
    iqr: FiniteNumber = Field(ge=0)
    lower_fence: FiniteNumber
    upper_fence: FiniteNumber
    lower_count: StrictCount
    upper_count: StrictCount
    total_count: Annotated[StrictInt, Field(gt=0)]
    outlier_count: StrictCount
    outlier_rate: FiniteNumber = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_outliers(self) -> "OutlierProfile":
        if float(self.iqr) != float(self.q3) - float(self.q1):
            raise ValueError("iqr must derive from quartiles")
        if float(self.lower_fence) != float(self.q1) - 1.5 * float(self.iqr):
            raise ValueError("lower_fence must derive from quartiles")
        if float(self.upper_fence) != float(self.q3) + 1.5 * float(self.iqr):
            raise ValueError("upper_fence must derive from quartiles")
        if self.outlier_count != self.lower_count + self.upper_count:
            raise ValueError("outlier_count must equal lower_count plus upper_count")
        if self.outlier_count > self.total_count:
            raise ValueError("outlier_count cannot exceed total_count")
        if float(self.outlier_rate) != self.outlier_count / self.total_count:
            raise ValueError("outlier_rate must derive from counts")
        return self


class FreshnessProfile(ValidationContractModel):
    status: Literal["available", "unavailable", "future_dated"]
    data_as_of: str | None
    execution_timestamp: Annotated[str, Field(min_length=1)]
    age_seconds: StrictCount | None
    reason_code: Literal["data_freshness_unavailable", "data_as_of_after_execution"] | None

    @model_validator(mode="after")
    def validate_state(self) -> "FreshnessProfile":
        expected = {
            "available": (False, False, None),
            "unavailable": (True, True, "data_freshness_unavailable"),
            "future_dated": (False, True, "data_as_of_after_execution"),
        }[self.status]
        actual = (self.data_as_of is None, self.age_seconds is None, self.reason_code)
        if actual != expected:
            raise ValueError("freshness fields are inconsistent with status")
        if not self.execution_timestamp.endswith("Z") or (
            self.data_as_of is not None and not self.data_as_of.endswith("Z")
        ):
            raise ValueError("freshness timestamps must use canonical UTC Z form")
        try:
            datetime_values = (self.execution_timestamp,) if self.data_as_of is None else (self.execution_timestamp, self.data_as_of)
            parsed = tuple(
                datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
                for value in datetime_values
            )
        except ValueError as error:
            raise ValueError("freshness timestamps must be valid ISO 8601 values") from error
        execution = parsed[0]
        if self.status == "unavailable":
            return self
        data_as_of = parsed[1]
        if self.status == "future_dated" and data_as_of <= execution:
            raise ValueError("future_dated freshness requires data_as_of after execution_timestamp")
        if self.status == "available":
            if data_as_of > execution:
                raise ValueError("available freshness requires data_as_of at or before execution_timestamp")
            expected_age = math.floor((execution - data_as_of).total_seconds())
            if self.age_seconds != expected_age:
                raise ValueError("age_seconds must derive from freshness timestamps")
        return self


class SingleRunProfile(ValidationContractModel):
    schema_version: Literal["1.0"] = "1.0"
    input_rows: Annotated[StrictInt, Field(gt=0)]
    eligible_rows: Annotated[StrictInt, Field(gt=0)]
    excluded_rows: StrictCount
    missingness: tuple[MissingnessProfile, ...]
    groups: tuple[GroupSizeProfile, ...]
    anomalies: tuple[AnomalyProfile, ...]
    score_distribution: NumericDistributionProfile
    outcome_distribution: tuple[CategoryCount, ...]
    outliers: OutlierProfile
    freshness: FreshnessProfile
    issues: tuple[ValidationIssue, ...]

    @model_validator(mode="after")
    def validate_profile(self) -> "SingleRunProfile":
        if self.input_rows != self.eligible_rows + self.excluded_rows:
            raise ValueError("profile row counts must reconcile")
        if self.score_distribution.count != self.eligible_rows:
            raise ValueError("score distribution count must equal eligible_rows")
        if self.score_distribution.field != self.outliers.field:
            raise ValueError("score distribution and outlier fields must match")
        if self.outliers.total_count != self.eligible_rows:
            raise ValueError("outlier total_count must equal eligible_rows")
        q1 = next(item.value for item in self.score_distribution.quantiles if float(item.probability) == 0.25)
        q3 = next(item.value for item in self.score_distribution.quantiles if float(item.probability) == 0.75)
        if float(self.outliers.q1) != float(q1) or float(self.outliers.q3) != float(q3):
            raise ValueError("outlier quartiles must match score distribution")
        if sum(item.count for item in self.outcome_distribution) != self.eligible_rows:
            raise ValueError("outcome counts must sum to eligible_rows")
        if any(item.total_count != self.eligible_rows for item in self.outcome_distribution):
            raise ValueError("outcome total_count must equal eligible_rows")
        outcome_keys = tuple(_typed_label_key(item.value) for item in self.outcome_distribution)
        if outcome_keys != tuple(sorted(set(outcome_keys))):
            raise ValueError("outcome categories must be sorted and unique")
        expected_codes = tuple(reason.value for reason in ExclusionReason)
        if tuple(item.code.value for item in self.anomalies) != tuple(sorted(expected_codes)):
            raise ValueError("all anomaly categories must appear in code order")
        if any(item.total_count != self.input_rows for item in self.anomalies):
            raise ValueError("anomaly total_count must equal input_rows")
        if self.issues != tuple(sorted(self.issues, key=issue_sort_key)):
            raise ValueError("profile issues must use canonical order")
        if any(issue.layer != ValidationLayerId.DATA_QUALITY for issue in self.issues):
            raise ValueError("profile issues must belong to data_quality")
        group_keys = tuple((_group_sort_key(item.group), 0 if item.population == "input" else 1) for item in self.groups)
        if group_keys != tuple(sorted(set(group_keys))):
            raise ValueError("groups must use canonical order and be unique")
        for item in self.groups:
            expected_total = self.input_rows if item.population == "input" else self.eligible_rows
            if item.total_count != expected_total:
                raise ValueError("group total_count must match its population")
        missingness_keys = tuple(
            (item.field, 0 if item.group is None else 1, () if item.group is None else _group_sort_key(item.group))
            for item in self.missingness
        )
        if missingness_keys != tuple(sorted(set(missingness_keys))):
            raise ValueError("missingness must use canonical order and be unique")
        input_group_counts = {_group_sort_key(item.group): item.count for item in self.groups if item.population == "input"}
        for item in self.missingness:
            expected_total = self.input_rows if item.group is None else input_group_counts.get(_group_sort_key(item.group))
            if item.total_count != expected_total:
                raise ValueError("missingness total_count must match its input population")
        issue_codes = {issue.code for issue in self.issues}
        expected_issue_codes = set()
        if self.outliers.outlier_count > 0:
            expected_issue_codes.add("score_outliers_observed")
        if self.freshness.reason_code is not None:
            expected_issue_codes.add(self.freshness.reason_code)
        if issue_codes != expected_issue_codes:
            raise ValueError("profile issues must exactly match outlier and freshness observations")
        outlier_issue = next((issue for issue in self.issues if issue.code == "score_outliers_observed"), None)
        if outlier_issue is not None and (
            outlier_issue.affected_fields != (self.outliers.field,)
            or outlier_issue.evidence.count != self.outliers.outlier_count
            or float(outlier_issue.evidence.total) != self.outliers.total_count
            or float(outlier_issue.evidence.minimum) != float(self.outliers.lower_fence)
            or float(outlier_issue.evidence.maximum) != float(self.outliers.upper_fence)
        ):
            raise ValueError("outlier issue evidence must match the outlier profile")
        freshness_issue = next(
            (issue for issue in self.issues if issue.code == self.freshness.reason_code),
            None,
        )
        if self.freshness.status == "future_dated" and (
            freshness_issue is None
            or freshness_issue.affected_fields
            or freshness_issue.evidence.observed != self.freshness.data_as_of
            or freshness_issue.evidence.expected != self.freshness.execution_timestamp
        ):
            raise ValueError("future-dated issue evidence must match freshness timestamps")
        return self


ComparisonScalar = StrictBool | StrictInt | StrictFloat | StrictStr
ComparisonThreshold = StrictInt | StrictFloat | Literal["equal"]


class BaselineSelection(ValidationContractModel):
    baseline_id: Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
    selection_method: Literal["run_id", "artifact_uri", "content_digest"]
    selected_value: Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
    profile_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None

    @model_validator(mode="after")
    def validate_selection(self) -> "BaselineSelection":
        if self.selection_method == "content_digest" and (
            self.profile_digest is None or self.selected_value != self.profile_digest
        ):
            raise ValueError("content_digest selection must equal profile_digest")
        if self.selection_method == "artifact_uri":
            from urllib.parse import urlsplit
            parsed = urlsplit(self.selected_value)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("artifact_uri must not contain credentials, query, or fragment")
        return self


class BaselineComparisonPolicy(ValidationContractModel):
    group_proportion_delta: FiniteNumber = Field(gt=0, le=1)
    missingness_rate_delta: FiniteNumber = Field(gt=0, le=1)
    score_quantile_delta: FiniteNumber = Field(gt=0)
    outcome_proportion_delta: FiniteNumber = Field(gt=0, le=1)


class ComparisonCheck(ValidationContractModel):
    check_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")]
    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    status: Literal["evaluated", "not_computable", "unavailable", "incompatible"]
    statistic: Annotated[str, Field(min_length=1)] | None
    threshold: ComparisonThreshold
    current_value: ComparisonScalar | None
    baseline_value: ComparisonScalar | None
    baseline_id: Annotated[str, Field(min_length=1)]
    affected_fields: tuple[str, ...] = ()
    affected_groups: tuple[AffectedGroup, ...] = ()
    reason_code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")] | None = None
    quantile_probability: FiniteNumber | None = Field(default=None, ge=0, le=1)
    category: Label | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "ComparisonCheck":
        if self.affected_fields != tuple(sorted(set(self.affected_fields))):
            raise ValueError("affected_fields must be sorted and unique")
        keys = tuple(_group_sort_key(group) for group in self.affected_groups)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("affected_groups must be sorted and unique")
        if self.status == "evaluated":
            if self.statistic is None or self.current_value is None or self.baseline_value is None or self.reason_code is not None:
                raise ValueError("evaluated checks require statistic and values without a reason")
        elif self.statistic is not None or self.current_value is not None or self.baseline_value is not None or self.reason_code is None:
            raise ValueError("non-evaluated checks require null evidence and a reason")
        return self


class ChangeFlag(ValidationContractModel):
    flag_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")]
    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    source_check_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")]
    statistic: Annotated[str, Field(min_length=1)]
    threshold: ComparisonThreshold
    current_value: ComparisonScalar
    baseline_value: ComparisonScalar
    baseline_id: Annotated[str, Field(min_length=1)]
    affected_fields: tuple[str, ...] = ()
    affected_groups: tuple[AffectedGroup, ...] = ()
    quantile_probability: FiniteNumber | None = Field(default=None, ge=0, le=1)
    category: Label | None = None


class BaselineComparisonResult(ValidationContractModel):
    schema_version: Literal["1.0"] = "1.0"
    baseline: BaselineSelection
    current_profile_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    status: Literal["completed", "partially_completed", "unavailable", "incompatible"]
    policy: BaselineComparisonPolicy
    checks: tuple[ComparisonCheck, ...]
    flags: tuple[ChangeFlag, ...]
    issues: tuple[ValidationIssue, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "BaselineComparisonResult":
        check_ids = [check.check_id for check in self.checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("comparison check IDs must be unique")
        if not self.checks:
            raise ValueError("comparison checks must not be empty")
        if self.checks != tuple(sorted(self.checks, key=_comparison_check_sort_key)):
            raise ValueError("comparison checks must use canonical order")
        check_by_id = {check.check_id: check for check in self.checks}
        for check in self.checks:
            if check.check_id != _expected_check_id(check):
                raise ValueError("check_id must derive from canonical identity dimensions")
            expected_threshold = {
                "group_proportion_absolute_delta": self.policy.group_proportion_delta,
                "missingness_rate_absolute_delta": self.policy.missingness_rate_delta,
                "score_quantile_absolute_delta": self.policy.score_quantile_delta,
                "outcome_category_presence_equal": "equal",
                "outcome_proportion_absolute_delta": self.policy.outcome_proportion_delta,
                "dataset_version_equal": "equal",
                "model_version_equal": "equal",
            }[check.code]
            if check.threshold != expected_threshold:
                raise ValueError("check threshold must match comparison policy")
        pairs = [(flag.code, flag.source_check_id) for flag in self.flags]
        if len(pairs) != len(set(pairs)) or len({flag.flag_id for flag in self.flags}) != len(self.flags):
            raise ValueError("comparison flags must be unique")
        for flag in self.flags:
            expected_flag_id = f'{flag.code}:{hashlib.sha256(json.dumps({"code": flag.code, "source_check_id": flag.source_check_id}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}'
            if flag.flag_id != expected_flag_id:
                raise ValueError("flag_id must derive from code and source_check_id")
            source = check_by_id.get(flag.source_check_id)
            if source is None or source.status != "evaluated":
                raise ValueError("every flag must reference one evaluated check")
            shared = ("statistic", "threshold", "current_value", "baseline_value", "baseline_id", "affected_fields", "affected_groups", "quantile_probability", "category")
            if any(getattr(flag, name) != getattr(source, name) for name in shared):
                raise ValueError("flag evidence must equal its source check")
            expected_code = _expected_flag_code(source)
            if flag.code != expected_code:
                raise ValueError("flag code and threshold condition must match its source check")
        check_positions = {check.check_id: index for index, check in enumerate(self.checks)}
        if self.flags != tuple(sorted(self.flags, key=lambda flag: (check_positions[flag.source_check_id], flag.code))):
            raise ValueError("comparison flags must use canonical order")
        states = {check.status for check in self.checks}
        expected_status = (
            "unavailable" if states == {"unavailable"} else
            "incompatible" if states == {"incompatible"} else
            "partially_completed" if "not_computable" in states else "completed"
        )
        if self.status != expected_status:
            raise ValueError("comparison status must derive from check statuses")
        expected_issue_refs: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        for code in {flag.code for flag in self.flags}:
            expected_issue_refs[code] = ((), tuple(flag.flag_id for flag in self.flags if flag.code == code))
        if "not_computable" in states:
            expected_issue_refs["comparison_check_not_computable"] = (tuple(c.check_id for c in self.checks if c.status == "not_computable"), ())
        if self.status in {"unavailable", "incompatible"}:
            expected_issue_refs[f"comparison_baseline_{self.status}"] = (tuple(check_ids), ())
        if {issue.code for issue in self.issues} != set(expected_issue_refs):
            raise ValueError("comparison issues must exactly cover checks and flags")
        for issue in self.issues:
            expected_checks, expected_flags = expected_issue_refs[issue.code]
            if issue.evidence.source_check_ids != expected_checks or issue.evidence.source_flag_ids != expected_flags:
                raise ValueError("comparison issue references must be complete and canonically ordered")
        if self.issues != tuple(sorted(self.issues, key=issue_sort_key)):
            raise ValueError("comparison issues must use canonical order")
        return self


class LayeredValidationResult(ValidationContractModel):
    schema_version: Literal["1.0"] = VALIDATION_SCHEMA_VERSION
    status: ValidationStatus
    technical_validation: ValidationStatus
    applicability: Literal["not_assessed"] = "not_assessed"
    applicability_statement: Literal[APPLICABILITY_STATEMENT] = APPLICABILITY_STATEMENT
    input_rows: int = Field(ge=0)
    eligible_rows: int = Field(ge=0)
    excluded_rows: int = Field(ge=0)
    reason_counts: tuple[tuple[str, int], ...]
    exclusion_evidence: tuple[ExclusionEvidence, ...] = ()
    duplicate_rows: int = Field(ge=0)
    small_groups: tuple[str, ...]
    layers: tuple[ValidationLayerResult, ...]
    profile: SingleRunProfile | None = None
    comparison: BaselineComparisonResult | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_comparison(cls, value: object) -> object:
        if isinstance(value, dict) and "comparison" not in value:
            return {**value, "comparison": None}
        return value

    @model_validator(mode="after")
    def validate_derived_contract(self) -> "LayeredValidationResult":
        if tuple(layer.layer for layer in self.layers) != LAYER_ORDER:
            raise ValueError("layers must contain exactly four entries in canonical order")
        if self.input_rows != self.eligible_rows + self.excluded_rows:
            raise ValueError("input_rows must equal eligible_rows plus excluded_rows")
        if self.reason_counts != tuple(sorted((code, count) for code, count in self.reason_counts if count > 0)):
            raise ValueError("reason_counts must be sorted with zero counts omitted")
        statuses = {layer.layer: layer.status for layer in self.layers}
        technical = aggregate_validation_status((statuses[ValidationLayerId.STRUCTURAL], statuses[ValidationLayerId.SEMANTIC]))
        overall = aggregate_validation_status(tuple(statuses.values()))
        if self.technical_validation != technical or self.status != overall:
            raise ValueError("aggregate statuses must be derived from layer statuses")
        if technical == ValidationStatus.FAILED:
            raise ValueError("a successful result cannot contain failed technical validation")
        if self.profile is not None:
            if (self.profile.input_rows, self.profile.eligible_rows, self.profile.excluded_rows) != (self.input_rows, self.eligible_rows, self.excluded_rows):
                raise ValueError("profile row counts must match validation result")
            data_quality = next(layer for layer in self.layers if layer.layer == ValidationLayerId.DATA_QUALITY)
            comparison_issues = () if self.comparison is None else self.comparison.issues
            expected_issues = tuple(sorted((*self.profile.issues, *comparison_issues), key=issue_sort_key))
            if data_quality.issues != expected_issues:
                raise ValueError("data-quality layer must contain the canonical profile/comparison issue merge")
            reason_counts = dict(self.reason_counts)
            if any(item.count != reason_counts.get(item.code.value, 0) for item in self.profile.anomalies):
                raise ValueError("profile anomalies must match validation reason_counts")
        comparison_issue_codes = {issue.code for layer in self.layers for issue in layer.issues if _is_comparison_issue(issue.code)}
        if self.comparison is None and comparison_issue_codes:
            raise ValueError("comparison issues require an attached comparison result")
        return self

    @property
    def analyzed_rows(self) -> int:
        return self.eligible_rows

    @property
    def exclusion_reason_counts(self) -> dict[ExclusionReason, int]:
        return {ExclusionReason(code): count for code, count in self.reason_counts}


ValidationSummary = LayeredValidationResult


def make_issue(code: str, *, affected_fields: tuple[str, ...] = (), affected_groups: tuple[AffectedGroup, ...] = (), evidence: ValidationIssueEvidence | None = None, severity: ValidationSeverity | None = None, blocking: bool | None = None) -> ValidationIssue:
    definition = ISSUE_REGISTRY[code]
    unique_groups = { _group_sort_key(group): group for group in affected_groups }
    return ValidationIssue(code=code, severity=severity or definition.severity, affected_fields=tuple(sorted(set(affected_fields))), affected_groups=tuple(unique_groups[key] for key in sorted(unique_groups)), evidence=evidence or ValidationIssueEvidence(), message=definition.message, blocking=definition.blocking if blocking is None else blocking)


def issue_sort_key(issue: ValidationIssue) -> tuple[Any, ...]:
    severity_order = {ValidationSeverity.ERROR: 0, ValidationSeverity.WARNING: 1, ValidationSeverity.INFO: 2}
    return (severity_order[issue.severity], issue.code, issue.affected_fields, tuple(_group_sort_key(group) for group in issue.affected_groups))


def _group_sort_key(group: AffectedGroup) -> tuple[Any, ...]:
    return tuple((key, *_typed_label_key(value)) for key, value in group.attributes.items())


def _typed_label_key(value: Label) -> tuple[int, object]:
    if isinstance(value, bool):
        return (0, value)
    if isinstance(value, int):
        return (1, value)
    return (2, value)


def _comparison_check_sort_key(check: ComparisonCheck) -> tuple[Any, ...]:
    domain = {
        "group_proportion_absolute_delta": 0,
        "missingness_rate_absolute_delta": 1,
        "score_quantile_absolute_delta": 2,
        "outcome_category_presence_equal": 3,
        "outcome_proportion_absolute_delta": 4,
        "dataset_version_equal": 5,
        "model_version_equal": 6,
    }[check.code]
    group = () if not check.affected_groups else _group_sort_key(check.affected_groups[0])
    overall = 0 if not check.affected_groups else 1
    group_fields = set() if not check.affected_groups else set(check.affected_groups[0].attributes)
    profiled = tuple(field for field in check.affected_fields if field not in group_fields)
    if not profiled:
        profiled = check.affected_fields
    category = () if check.category is None else _typed_label_key(check.category)
    probability = -1.0 if check.quantile_probability is None else float(check.quantile_probability)
    return (domain, profiled, overall, group, probability, category)


def _typed_identity(value: Label) -> dict[str, object]:
    kind = "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) else "string"
    return {"type": kind, "value": value}


def _expected_check_id(check: ComparisonCheck) -> str:
    scope: dict[str, object]
    if check.code == "group_proportion_absolute_delta":
        field = check.affected_fields[0]
        group = check.affected_groups[0]
        scope = {"field": field, "group": {key: _typed_identity(value) for key, value in group.attributes.items()}}
    elif check.code == "missingness_rate_absolute_delta":
        group_fields = set() if not check.affected_groups else set(check.affected_groups[0].attributes)
        candidates = [field for field in check.affected_fields if field not in group_fields]
        field = candidates[0] if candidates else check.affected_fields[0]
        scope = {"field": field}
        if check.affected_groups:
            scope["group"] = {key: _typed_identity(value) for key, value in check.affected_groups[0].attributes.items()}
    elif check.code == "score_quantile_absolute_delta":
        scope = {"field": check.affected_fields[0], "quantile_probability": float(check.quantile_probability)}
    elif check.code in {"outcome_category_presence_equal", "outcome_proportion_absolute_delta"}:
        scope = {"field": check.affected_fields[0], "category": _typed_identity(check.category)}
    else:
        scope = {}
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return f"{check.code}:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _expected_flag_code(check: ComparisonCheck) -> str | None:
    if check.status != "evaluated":
        return None
    if check.threshold == "equal":
        if check.current_value == check.baseline_value:
            return None
        if check.code == "outcome_category_presence_equal":
            return "outcome_category_added" if check.current_value else "outcome_category_removed"
        return "dataset_version_changed" if check.code == "dataset_version_equal" else "model_version_changed"
    if abs(float(check.current_value) - float(check.baseline_value)) < float(check.threshold):
        return None
    return {
        "group_proportion_absolute_delta": "group_composition_changed",
        "missingness_rate_absolute_delta": "missingness_changed",
        "score_quantile_absolute_delta": "score_distribution_changed",
        "outcome_proportion_absolute_delta": "outcome_distribution_changed",
    }[check.code]


def _is_comparison_issue(code: str) -> bool:
    return code.startswith("comparison_") or code in {
        "group_composition_changed", "missingness_changed", "score_distribution_changed",
        "outcome_distribution_changed", "outcome_category_added", "outcome_category_removed",
        "dataset_version_changed", "model_version_changed",
    }


def _layer_status(issues: tuple[ValidationIssue, ...]) -> ValidationStatus:
    if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
        return ValidationStatus.FAILED
    if any(issue.severity == ValidationSeverity.WARNING for issue in issues):
        return ValidationStatus.WARNING
    evaluated_subcheck_info = {
        "data_freshness_unavailable",
        "comparison_baseline_unavailable",
        "comparison_baseline_incompatible",
        "comparison_check_not_computable",
        "dataset_version_changed",
        "model_version_changed",
    }
    if issues and all(issue.code in evaluated_subcheck_info for issue in issues):
        return ValidationStatus.PASSED
    if issues:
        return ValidationStatus.NOT_EVALUATED
    return ValidationStatus.PASSED


def aggregate_validation_status(statuses: tuple[ValidationStatus, ...]) -> ValidationStatus:
    evaluated = [status for status in statuses if status != ValidationStatus.NOT_EVALUATED]
    if not evaluated:
        return ValidationStatus.NOT_EVALUATED
    if ValidationStatus.FAILED in evaluated:
        return ValidationStatus.FAILED
    if ValidationStatus.WARNING in evaluated:
        return ValidationStatus.WARNING
    return ValidationStatus.PASSED
