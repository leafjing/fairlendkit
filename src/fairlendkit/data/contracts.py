"""Framework-neutral contracts for exclusions and layered validation results."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


ISSUE_REGISTRY: dict[str, IssueDefinition] = {
    "missing_required_column": IssueDefinition(ValidationLayerId.STRUCTURAL, "One or more required columns are missing.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "missing_required_value": IssueDefinition(ValidationLayerId.STRUCTURAL, "Required analysis values are missing.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "non_numeric_score": IssueDefinition(ValidationLayerId.STRUCTURAL, "The score column is not a non-boolean real numeric type.", ValidationSeverity.ERROR, True),
    "non_numeric_weight": IssueDefinition(ValidationLayerId.STRUCTURAL, "The sample-weight column is not a non-boolean real numeric type.", ValidationSeverity.ERROR, True),
    "negative_weight": IssueDefinition(ValidationLayerId.STRUCTURAL, "Sample weights contain negative values.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "non_positive_weight_total": IssueDefinition(ValidationLayerId.STRUCTURAL, "Eligible sample weights do not have a positive total.", ValidationSeverity.ERROR, True, frozenset({"total"})),
    "non_finite_numeric": IssueDefinition(ValidationLayerId.STRUCTURAL, "Numeric analysis values must be finite.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "duplicate_record": IssueDefinition(ValidationLayerId.STRUCTURAL, "Duplicate records were detected.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "non_unique_record_id": IssueDefinition(ValidationLayerId.STRUCTURAL, "Record identifiers are not unique in eligible data.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "unknown_protected_group": IssueDefinition(ValidationLayerId.STRUCTURAL, "Protected-group values outside the declared allowed set were observed.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "unexpected_category": IssueDefinition(ValidationLayerId.STRUCTURAL, "Values outside the declared expected categories were observed.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "no_eligible_rows": IssueDefinition(ValidationLayerId.STRUCTURAL, "No eligible rows remain after configured exclusions.", ValidationSeverity.ERROR, True, frozenset({"count"})),
    "favorable_label_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "The configured favorable outcome label is absent from eligible data.", ValidationSeverity.ERROR, True),
    "favorable_decision_label_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "The configured favorable decision label is absent from eligible data.", ValidationSeverity.ERROR, True),
    "reference_group_absent": IssueDefinition(ValidationLayerId.SEMANTIC, "A configured reference group is absent from eligible data.", ValidationSeverity.ERROR, True),
    "ambiguous_column_role": IssueDefinition(ValidationLayerId.SEMANTIC, "A column has more than one declared semantic role.", ValidationSeverity.ERROR, True),
    "inconsistent_threshold_direction": IssueDefinition(ValidationLayerId.SEMANTIC, "The threshold operator is inconsistent with score direction.", ValidationSeverity.ERROR, True),
    "invalid_category_declaration": IssueDefinition(ValidationLayerId.SEMANTIC, "A category declaration is invalid.", ValidationSeverity.ERROR, True),
    "small_group": IssueDefinition(ValidationLayerId.ANALYTICAL_RELIABILITY, "An eligible protected group is below the configured minimum size.", ValidationSeverity.WARNING, False, frozenset({"count", "minimum"})),
    "comparison_baseline_unavailable": IssueDefinition(ValidationLayerId.DATA_QUALITY, "Comparison baseline evidence is unavailable.", ValidationSeverity.INFO, False),
}


class ValidationContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ValidationIssueEvidence(ValidationContractModel):
    count: int | None = Field(default=None, ge=0)
    total: float | int | None = None
    observed: Label | tuple[Label, ...] | None = None
    expected: Label | tuple[Label, ...] | None = None
    minimum: float | int | None = None
    maximum: float | int | None = None
    reason_counts: dict[str, int] | None = None

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
        present = {name for name, value in self.evidence if value is not None}
        missing = definition.required_evidence - present
        if missing:
            raise ValueError(f"issue {self.code!r} requires evidence: {', '.join(sorted(missing))}")
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

    @model_validator(mode="after")
    def validate_derived_contract(self) -> "LayeredValidationResult":
        if tuple(layer.layer for layer in self.layers) != LAYER_ORDER:
            raise ValueError("layers must contain exactly four entries in canonical order")
        if self.input_rows != self.eligible_rows + self.excluded_rows:
            raise ValueError("input_rows must equal eligible_rows plus excluded_rows")
        if self.reason_counts != tuple(sorted((code, count) for code, count in self.reason_counts if count > 0)):
            raise ValueError("reason_counts must be sorted with zero counts omitted")
        statuses = {layer.layer: layer.status for layer in self.layers}
        technical = _aggregate_status((statuses[ValidationLayerId.STRUCTURAL], statuses[ValidationLayerId.SEMANTIC]))
        overall = _aggregate_status(tuple(statuses.values()))
        if self.technical_validation != technical or self.status != overall:
            raise ValueError("aggregate statuses must be derived from layer statuses")
        if technical == ValidationStatus.FAILED:
            raise ValueError("a successful result cannot contain failed technical validation")
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
    return tuple((key, type(value).__name__, repr(value)) for key, value in group.attributes.items())


def _layer_status(issues: tuple[ValidationIssue, ...]) -> ValidationStatus:
    if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
        return ValidationStatus.FAILED
    if any(issue.severity == ValidationSeverity.WARNING for issue in issues):
        return ValidationStatus.WARNING
    if issues:
        return ValidationStatus.NOT_EVALUATED
    return ValidationStatus.PASSED


def _aggregate_status(statuses: tuple[ValidationStatus, ...]) -> ValidationStatus:
    evaluated = [status for status in statuses if status != ValidationStatus.NOT_EVALUATED]
    if not evaluated:
        return ValidationStatus.NOT_EVALUATED
    if ValidationStatus.FAILED in evaluated:
        return ValidationStatus.FAILED
    if ValidationStatus.WARNING in evaluated:
        return ValidationStatus.WARNING
    return ValidationStatus.PASSED
