"""Public package interface for FairLendKit."""

from fairlendkit.config import AuditConfig, ScoreDirection, ScoreType, ThresholdOperator
from fairlendkit.data import DataValidationError, ValidationSummary, validate_audit_data
from fairlendkit.report import AuditResult

__all__ = [
    "AuditConfig",
    "AuditResult",
    "DataValidationError",
    "ScoreDirection",
    "ScoreType",
    "ThresholdOperator",
    "ValidationSummary",
    "validate_audit_data",
]
