"""Public package interface for FairLendKit."""

from fairlendkit.config import (
    AuditConfig,
    DuplicatePolicy,
    ScoreDirection,
    ScoreType,
    ThresholdOperator,
)
from fairlendkit.data import (
    DataValidationError,
    ExclusionEvidence,
    ExclusionReason,
    ValidationSummary,
    validate_audit_data,
)
from fairlendkit.report import AuditResult

__all__ = [
    "AuditConfig",
    "AuditResult",
    "DataValidationError",
    "DuplicatePolicy",
    "ExclusionEvidence",
    "ExclusionReason",
    "ScoreDirection",
    "ScoreType",
    "ThresholdOperator",
    "ValidationSummary",
    "validate_audit_data",
]
