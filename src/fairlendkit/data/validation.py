"""Pandas adapter for the framework-neutral audit validation contract."""

from __future__ import annotations

import math

import pandas as pd

from fairlendkit.config import AuditConfig
from fairlendkit.data.contracts import (
    DataValidationError,
    ExclusionEvidence,
    ValidationSummary,
)

MISSING_REQUIRED_VALUE = "missing_required_value"
UNKNOWN_PROTECTED_GROUP = "unknown_protected_group"


def validate_audit_data(data: pd.DataFrame, config: AuditConfig) -> ValidationSummary:
    """Validate a dataframe and compose explicit missing/unknown eligibility rules."""

    required = _required_columns(config)
    missing_columns = sorted(required.difference(data.columns))
    if missing_columns:
        raise DataValidationError(f"missing required columns: {', '.join(missing_columns)}")
    if data.empty:
        raise DataValidationError("audit data must contain at least one row")

    missing_mask = data[list(sorted(required))].isna().any(axis=1)
    unknown_mask = pd.Series(False, index=data.index)
    evidence: list[ExclusionEvidence] = []
    for attribute in config.protected_attributes:
        attribute_unknown = data[attribute].map(
            lambda value: pd.notna(value)
            and not any(
                _typed_values_equal(value, allowed)
                for allowed in config.allowed_groups[attribute]
            )
        )
        unknown_mask |= attribute_unknown
        for value, count in _typed_value_counts(data.loc[attribute_unknown, attribute]):
            evidence.append(
                ExclusionEvidence(UNKNOWN_PROTECTED_GROUP, attribute, value, count)
            )

    reason_counts = {
        code: count
        for code, count in (
            (MISSING_REQUIRED_VALUE, int(missing_mask.sum())),
            (UNKNOWN_PROTECTED_GROUP, int(unknown_mask.sum())),
        )
        if count
    }
    if missing_mask.any():
        evidence.insert(
            0,
            ExclusionEvidence(MISSING_REQUIRED_VALUE, None, None, int(missing_mask.sum())),
        )
    if missing_mask.any() and config.missing_value_policy == "error":
        raise DataValidationError(
            f"{int(missing_mask.sum())} rows contain missing required values",
            reason_counts=reason_counts,
            evidence=tuple(evidence),
        )
    if unknown_mask.any() and config.unknown_group_policy == "error":
        details = ", ".join(
            repr(item.observed_value)
            for item in evidence
            if item.reason_code == UNKNOWN_PROTECTED_GROUP
        )
        raise DataValidationError(
            f"unknown group values are present: {details}",
            reason_counts=reason_counts,
            evidence=tuple(evidence),
        )

    excluded_mask = missing_mask | unknown_mask
    eligible = data.loc[~excluded_mask]
    if eligible.empty:
        raise DataValidationError("no eligible rows remain after eligibility rules")

    if not _contains_typed_value(eligible[config.outcome_column], config.favorable_label):
        raise DataValidationError("favorable_label is not present in eligible outcome data")
    if config.decision_column is not None and not _contains_typed_value(
        eligible[config.decision_column], config.favorable_decision_label
    ):
        raise DataValidationError("favorable_decision_label is not present in eligible decision data")
    if not pd.api.types.is_numeric_dtype(eligible[config.score_column]):
        raise DataValidationError("score_column must be numeric")
    if not eligible[config.score_column].map(_is_finite_number).all():
        raise DataValidationError("score_column must contain only finite numeric values")
    if config.sample_weight_column is not None:
        weights = eligible[config.sample_weight_column]
        if not pd.api.types.is_numeric_dtype(weights) or not weights.map(_is_finite_number).all():
            raise DataValidationError("sample weights must be finite numeric values")
        if (weights < 0).any() or float(weights.sum()) <= 0:
            raise DataValidationError("sample weights must be non-negative with a positive sum")

    small_groups: list[str] = []
    for attribute in config.protected_attributes:
        reference = config.reference_groups[attribute]
        if not _contains_typed_value(eligible[attribute], reference):
            raise DataValidationError(
                f"reference group {reference!r} is not present in eligible data for {attribute!r}"
            )
        small_groups.extend(
            f"{attribute}={value!r}"
            for value, count in _typed_value_counts(eligible[attribute])
            if count < config.minimum_group_size
        )

    return ValidationSummary(
        input_rows=len(data),
        eligible_rows=len(eligible),
        excluded_rows=int(excluded_mask.sum()),
        exclusion_reason_counts=reason_counts,
        exclusion_evidence=tuple(evidence),
        small_groups=tuple(sorted(small_groups)),
    )


def _required_columns(config: AuditConfig) -> set[str]:
    columns = {config.outcome_column, config.score_column, *config.protected_attributes,
               *config.candidate_proxy_features}
    columns.update(c for c in (config.decision_column, config.sample_weight_column) if c)
    return columns


def _is_finite_number(value: object) -> bool:
    try:
        return bool(pd.notna(value) and math.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _contains_typed_value(series: pd.Series, expected: object) -> bool:
    return any(_typed_values_equal(actual, expected) for actual in series.unique())


def _typed_value_counts(series: pd.Series) -> list[tuple[object, int]]:
    counts: list[tuple[object, int]] = []
    for value in series:
        for index, (known, count) in enumerate(counts):
            if _typed_values_equal(value, known):
                counts[index] = (known, count + 1)
                break
        else:
            counts.append((value, 1))
    return counts


def _typed_values_equal(actual: object, expected: object) -> bool:
    if pd.api.types.is_bool(actual) or pd.api.types.is_bool(expected):
        return pd.api.types.is_bool(actual) and pd.api.types.is_bool(expected) and bool(actual) is bool(expected)
    if pd.api.types.is_integer(actual) or pd.api.types.is_integer(expected):
        return pd.api.types.is_integer(actual) and pd.api.types.is_integer(expected) and int(actual) == int(expected)
    return type(actual) is type(expected) and bool(actual == expected)
