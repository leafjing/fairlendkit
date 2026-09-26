"""Public package interface for FairLendKit."""

from fairlendkit.config import (
    AuditConfig,
    DuplicatePolicy,
    ScoreDirection,
    ScoreType,
    ThresholdOperator,
)
from fairlendkit.data import (
    APPLICABILITY_STATEMENT,
    AffectedGroup,
    DataValidationError,
    ExclusionEvidence,
    ExclusionReason,
    LayeredValidationResult,
    ValidationIssue,
    ValidationIssueEvidence,
    ValidationLayerId,
    ValidationLayerResult,
    ValidationSeverity,
    ValidationStatus,
    ValidationSummary,
    validate_audit_data,
)
from fairlendkit.report import AuditResult

__all__ = [
    "APPLICABILITY_STATEMENT",
    "AffectedGroup",
    "AuditConfig",
    "AuditResult",
    "DataValidationError",
    "DuplicatePolicy",
    "ExclusionEvidence",
    "ExclusionReason",
    "LayeredValidationResult",
    "ScoreDirection",
    "ScoreType",
    "ThresholdOperator",
    "ValidationSummary",
    "ValidationIssue",
    "ValidationIssueEvidence",
    "ValidationLayerId",
    "ValidationLayerResult",
    "ValidationSeverity",
    "ValidationStatus",
    "validate_audit_data",
]
