"""Validation of tabular audit inputs against :class:`AuditConfig`."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fairlendkit.config import AuditConfig


class DataValidationError(ValueError):
    """Raised when audit data does not satisfy its declared contract."""


@dataclass(frozen=True)
class ValidationSummary:
    """Counts produced by successful validation without mutating input data."""

    input_rows: int
    eligible_rows: int
    excluded_rows: int
    small_groups: tuple[str, ...]


def validate_audit_data(data: pd.DataFrame, config: AuditConfig) -> ValidationSummary:
    """Validate required columns, semantics, values, and configured groups.

    Missing rows are counted when ``missing_value_policy`` is ``exclude``;
    actual filtering remains an orchestration responsibility so it is explicit
    and traceable in the eventual audit result.
    """

    required = _required_columns(config)
    missing_columns = sorted(required.difference(data.columns))
    if missing_columns:
        raise DataValidationError(f"missing required columns: {', '.join(missing_columns)}")

    if data.empty:
        raise DataValidationError("audit data must contain at least one row")

    relevant = data[list(sorted(required))]
    missing_rows = relevant.isna().any(axis=1)
    if missing_rows.any() and config.missing_value_policy == "error":
        raise DataValidationError(
            f"{int(missing_rows.sum())} rows contain missing required values"
        )

    eligible = data.loc[~missing_rows]
    if eligible.empty:
        raise DataValidationError("no eligible rows remain after missing-value handling")

    if config.favorable_label not in set(eligible[config.outcome_column].unique()):
        raise DataValidationError("favorable_label is not present in outcome_column")

    if config.decision_column is not None:
        decision_values = set(eligible[config.decision_column].unique())
        if config.favorable_decision_label not in decision_values:
            raise DataValidationError(
                "favorable_decision_label is not present in decision_column"
            )

    if not pd.api.types.is_numeric_dtype(eligible[config.score_column]):
        raise DataValidationError("score_column must be numeric")
    if not pd.Series(eligible[config.score_column]).map(_is_finite_number).all():
        raise DataValidationError("score_column must contain only finite numeric values")

    if config.sample_weight_column is not None:
        weights = eligible[config.sample_weight_column]
        if not pd.api.types.is_numeric_dtype(weights) or not weights.map(_is_finite_number).all():
            raise DataValidationError("sample weights must be finite numeric values")
        if (weights < 0).any() or float(weights.sum()) <= 0:
            raise DataValidationError("sample weights must be non-negative with a positive sum")

    small_groups: list[str] = []
    for attribute in config.protected_attributes:
        values = set(eligible[attribute].unique())
        reference = config.reference_groups[attribute]
        if reference not in values:
            raise DataValidationError(
                f"reference group {reference!r} is not present in {attribute!r}"
            )
        counts = eligible.groupby(attribute, dropna=False).size()
        small_groups.extend(
            f"{attribute}={value!r}" for value, count in counts.items()
            if count < config.minimum_group_size
        )

    return ValidationSummary(
        input_rows=len(data),
        eligible_rows=len(eligible),
        excluded_rows=int(missing_rows.sum()),
        small_groups=tuple(sorted(small_groups)),
    )


def _required_columns(config: AuditConfig) -> set[str]:
    columns = {
        config.outcome_column,
        config.score_column,
        *config.protected_attributes,
        *config.candidate_proxy_features,
    }
    for optional in (config.decision_column, config.sample_weight_column):
        if optional is not None:
            columns.add(optional)
    return columns


def _is_finite_number(value: object) -> bool:
    try:
        return bool(pd.notna(value) and float(value) not in (float("inf"), float("-inf")))
    except (TypeError, ValueError):
        return False

