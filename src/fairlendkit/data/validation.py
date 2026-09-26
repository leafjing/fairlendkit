"""Validation of tabular audit inputs against :class:`AuditConfig`."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real

import pandas as pd

from fairlendkit.config import AuditConfig
from fairlendkit.data.contracts import ExclusionEvidence, ExclusionReason


class DataValidationError(ValueError):
    """Raised when audit data does not satisfy its declared contract."""

    def __init__(
        self,
        message: str,
        *,
        reason_counts: dict[ExclusionReason, int] | None = None,
        evidence: tuple[ExclusionEvidence, ...] = (),
    ) -> None:
        super().__init__(message)
        self.reason_counts = dict(reason_counts or {})
        self.evidence = evidence


@dataclass(frozen=True)
class ValidationSummary:
    """Counts produced by successful validation without mutating input data."""

    input_rows: int
    eligible_rows: int
    excluded_rows: int
    small_groups: tuple[str, ...]
    exclusion_reason_counts: dict[ExclusionReason, int]
    exclusion_evidence: tuple[ExclusionEvidence, ...]
    reason_counts: tuple[tuple[str, int], ...]
    duplicate_rows: int


def validate_audit_data(data: pd.DataFrame, config: AuditConfig) -> ValidationSummary:
    """Validate every row condition against the unchanged original frame."""

    required = _required_columns(config)
    missing_columns = sorted(required.difference(data.columns))
    if missing_columns:
        raise DataValidationError(f"missing required columns: {', '.join(missing_columns)}")
    if data.empty:
        raise DataValidationError("audit data must contain at least one row")

    relevant = data[list(sorted(required))]
    missing_rows = relevant.isna().any(axis=1)
    duplicate_rows = _duplicate_mask(data, config)
    non_finite_rows = pd.Series(False, index=data.index)
    for column in _numeric_columns(config):
        non_finite_rows |= data[column].map(_is_infinite_number)

    unknown_rows = pd.Series(False, index=data.index)
    unexpected_rows = pd.Series(False, index=data.index)
    evidence = [
        ExclusionEvidence(
            reason=ExclusionReason.MISSING_REQUIRED_VALUE,
            attribute=column,
            observed_value=None,
            count=int(relevant[column].isna().sum()),
        )
        for column in sorted(required)
        if relevant[column].isna().any()
    ]
    for attribute in config.protected_attributes:
        attribute_unknown = _outside_typed_set(data[attribute], config.allowed_groups[attribute])
        if attribute_unknown.any():
            for value, count in _typed_value_counts(data.loc[attribute_unknown, attribute]):
                evidence.append(
                    ExclusionEvidence(
                        reason=ExclusionReason.UNKNOWN_PROTECTED_GROUP,
                        attribute=attribute,
                        observed_value=value,
                        count=count,
                    )
                )
            unknown_rows |= attribute_unknown
    for column, expected in config.expected_categories.items():
        unexpected_rows |= _outside_typed_set(data[column], expected)

    masks = {
        ExclusionReason.MISSING_REQUIRED_VALUE: missing_rows,
        ExclusionReason.UNKNOWN_PROTECTED_GROUP: unknown_rows,
        ExclusionReason.DUPLICATE_RECORD: duplicate_rows,
        ExclusionReason.NON_FINITE_NUMERIC: non_finite_rows,
        ExclusionReason.UNEXPECTED_CATEGORY: unexpected_rows,
    }
    counts = {reason: int(mask.sum()) for reason, mask in masks.items() if mask.any()}
    rejected: list[str] = []
    if missing_rows.any() and config.missing_value_policy == "error":
        rejected.append(f"{int(missing_rows.sum())} rows contain missing required values")
    if unknown_rows.any() and config.unknown_group_policy == "error":
        rejected.append(f"{int(unknown_rows.sum())} rows contain unknown protected groups")
    if duplicate_rows.any() and config.duplicate_policy == "error":
        rejected.append(f"{int(duplicate_rows.sum())} rows are duplicate records")
    if non_finite_rows.any():
        rejected.append(f"{int(non_finite_rows.sum())} rows contain non-finite numeric values")
    if unexpected_rows.any():
        rejected.append(f"{int(unexpected_rows.sum())} rows contain unexpected categories")
    if rejected:
        raise DataValidationError(
            "; ".join(rejected), reason_counts=counts, evidence=tuple(evidence)
        )

    excluded = pd.Series(False, index=data.index)
    if config.missing_value_policy == "exclude":
        excluded |= missing_rows
    if config.unknown_group_policy == "exclude":
        excluded |= unknown_rows
    if config.duplicate_policy == "exclude":
        excluded |= duplicate_rows
    eligible = data.loc[~excluded]
    if eligible.empty:
        raise DataValidationError("no eligible rows remain after exclusion handling")

    _validate_numeric_columns(eligible, config)
    if config.record_id_column is not None and _duplicate_mask(eligible, config).any():
        raise DataValidationError("record_id_column must be unique in eligible data")
    if not _contains_typed_value(eligible[config.outcome_column], config.favorable_label):
        raise DataValidationError("favorable_label is not present in outcome_column")
    if config.decision_column is not None and not _contains_typed_value(
        eligible[config.decision_column], config.favorable_decision_label
    ):
        raise DataValidationError("favorable_decision_label is not present in decision_column")

    small_groups: list[str] = []
    for attribute in config.protected_attributes:
        reference = config.reference_groups[attribute]
        if not _contains_typed_value(eligible[attribute], reference):
            raise DataValidationError(
                f"reference group {reference!r} is not present in {attribute!r}"
            )
        small_groups.extend(
            f"{attribute}={value!r}"
            for value, count in _typed_value_counts(eligible[attribute])
            if count < config.minimum_group_size
        )

    ordered_counts = tuple(sorted((reason.value, count) for reason, count in counts.items()))
    return ValidationSummary(
        input_rows=len(data),
        eligible_rows=len(eligible),
        excluded_rows=int(excluded.sum()),
        small_groups=tuple(sorted(small_groups)),
        exclusion_reason_counts=counts,
        exclusion_evidence=tuple(evidence),
        reason_counts=ordered_counts,
        duplicate_rows=int(duplicate_rows.sum()),
    )


def _required_columns(config: AuditConfig) -> set[str]:
    columns = {
        config.outcome_column,
        config.score_column,
        *config.protected_attributes,
        *config.candidate_proxy_features,
    }
    for optional in (
        config.decision_column,
        config.sample_weight_column,
        config.record_id_column,
    ):
        if optional is not None:
            columns.add(optional)
    return columns


def _numeric_columns(config: AuditConfig) -> tuple[str, ...]:
    if config.sample_weight_column is None:
        return (config.score_column,)
    return (config.score_column, config.sample_weight_column)


def _validate_numeric_columns(data: pd.DataFrame, config: AuditConfig) -> None:
    scores = data[config.score_column]
    if (
        pd.api.types.is_bool_dtype(scores.dtype)
        or pd.api.types.is_complex_dtype(scores.dtype)
        or not pd.api.types.is_numeric_dtype(scores)
    ):
        raise DataValidationError("score_column must have a non-boolean real numeric dtype")
    if config.sample_weight_column is not None:
        weights = data[config.sample_weight_column]
        if (
            pd.api.types.is_bool_dtype(weights.dtype)
            or pd.api.types.is_complex_dtype(weights.dtype)
            or not pd.api.types.is_numeric_dtype(weights)
        ):
            raise DataValidationError(
                "sample weights must have a non-boolean real numeric dtype"
            )
        if (weights < 0).any() or float(weights.sum()) <= 0:
            raise DataValidationError("sample weights must be non-negative with a positive sum")


def _duplicate_mask(data: pd.DataFrame, config: AuditConfig) -> pd.Series:
    if config.record_id_column is None:
        return data.duplicated(keep=False)
    identifiers = data[config.record_id_column]
    counts = _typed_value_counts(identifiers[identifiers.notna()])
    repeated = tuple(value for value, count in counts if count > 1)
    return identifiers.map(
        lambda value: bool(pd.notna(value))
        and any(_typed_values_equal(value, item) for item in repeated)
    )


def _outside_typed_set(series: pd.Series, allowed: tuple[object, ...]) -> pd.Series:
    return series.map(
        lambda value: bool(pd.notna(value))
        and not any(_typed_values_equal(value, item) for item in allowed)
    )


def _is_infinite_number(value: object) -> bool:
    if not isinstance(value, Real) or pd.api.types.is_bool(value):
        return False
    return math.isinf(float(value))


def _contains_typed_value(series: pd.Series, expected: object) -> bool:
    return any(_typed_values_equal(actual, expected) for actual in series.unique())


def _typed_values_equal(actual: object, expected: object) -> bool:
    if pd.api.types.is_bool(actual) or pd.api.types.is_bool(expected):
        return (
            pd.api.types.is_bool(actual)
            and pd.api.types.is_bool(expected)
            and bool(actual) is bool(expected)
        )
    if pd.api.types.is_integer(actual) or pd.api.types.is_integer(expected):
        return (
            pd.api.types.is_integer(actual)
            and pd.api.types.is_integer(expected)
            and int(actual) == int(expected)
        )
    return type(actual) is type(expected) and bool(actual == expected)


def _typed_value_counts(series: pd.Series) -> list[tuple[object, int]]:
    counts: list[list[object | int]] = []
    for value in series.tolist():
        for entry in counts:
            if _typed_values_equal(value, entry[0]):
                entry[1] = int(entry[1]) + 1
                break
        else:
            counts.append([value, 1])
    return [(entry[0], int(entry[1])) for entry in counts]
