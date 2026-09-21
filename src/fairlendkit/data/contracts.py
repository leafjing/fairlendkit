"""Stable domain contracts for auditable input exclusions.

This module deliberately has no dataframe dependency.  Adapters may discover
missing or unknown values, but the meanings recorded here belong to the domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExclusionReason(StrEnum):
    """Stable machine-readable reasons why a row is ineligible."""

    MISSING_REQUIRED_VALUE = "missing_required_value"
    UNKNOWN_PROTECTED_GROUP = "unknown_protected_group"


@dataclass(frozen=True)
class ExclusionEvidence:
    """Aggregate evidence for one exclusion reason and protected attribute."""

    reason: ExclusionReason
    count: int
    attribute: str | None = None
    observed_value: object | None = None

