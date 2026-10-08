"""Framework-neutral contracts for audit-data eligibility validation."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ExclusionEvidence:
    """Attribute-level evidence attached to a stable condition code."""

    reason_code: str
    attribute: str | None
    observed_value: object | None
    row_count: int


class DataValidationError(ValueError):
    """Raised when data violates policy, retaining machine-readable evidence."""

    def __init__(
        self,
        message: str,
        *,
        reason_counts: Mapping[str, int] | None = None,
        evidence: tuple[ExclusionEvidence, ...] = (),
    ) -> None:
        super().__init__(message)
        self.reason_counts = MappingProxyType(dict(reason_counts or {}))
        self.evidence = evidence


@dataclass(frozen=True)
class ValidationSummary:
    """Eligibility counts produced without retaining a dataframe."""

    input_rows: int
    eligible_rows: int
    excluded_rows: int
    exclusion_reason_counts: Mapping[str, int]
    exclusion_evidence: tuple[ExclusionEvidence, ...]
    small_groups: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exclusion_reason_counts",
            MappingProxyType(dict(self.exclusion_reason_counts)),
        )
