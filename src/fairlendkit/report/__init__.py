"""Canonical report contract consumed by every output renderer."""

from fairlendkit.report.models import (
    AUDIT_RESULT_SCHEMA_VERSION,
    AuditGroup,
    AuditResult,
    ExclusionRecord,
    Limitation,
    MetricName,
    ObservedMetric,
    PractitionerReviewNote,
    RunMetadata,
    ScreeningFlag,
    StatisticalUncertainty,
    UncertaintyMethod,
    ValidationEvidence,
    WarningRecord,
)

__all__ = [
    "AUDIT_RESULT_SCHEMA_VERSION",
    "AuditGroup",
    "AuditResult",
    "ExclusionRecord",
    "Limitation",
    "MetricName",
    "ObservedMetric",
    "PractitionerReviewNote",
    "RunMetadata",
    "ScreeningFlag",
    "StatisticalUncertainty",
    "UncertaintyMethod",
    "ValidationEvidence",
    "WarningRecord",
]

