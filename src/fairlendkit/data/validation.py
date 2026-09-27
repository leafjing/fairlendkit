"""Validation of tabular audit inputs against :class:`AuditConfig`."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from numbers import Real

import pandas as pd

from fairlendkit.config import AuditConfig
from fairlendkit.data.contracts import (
    AffectedGroup,
    AnomalyProfile,
    CategoryCount,
    ExclusionEvidence,
    ExclusionReason,
    LAYER_ORDER,
    LayeredValidationResult,
    FreshnessProfile,
    GroupSizeProfile,
    MissingnessProfile,
    NumericDistributionProfile,
    OutlierProfile,
    QuantileValue,
    SingleRunProfile,
    ValidationIssue,
    ValidationIssueEvidence,
    ValidationLayerId,
    ValidationLayerResult,
    ValidationSeverity,
    ValidationStatus,
    aggregate_validation_status,
    issue_sort_key,
    make_issue,
)


class DataValidationError(ValueError):
    """Raised when audit data does not satisfy its declared contract."""

    def __init__(
        self,
        message: str,
        *,
        reason_counts: dict[ExclusionReason, int] | None = None,
        evidence: tuple[ExclusionEvidence, ...] = (),
        issues: tuple[ValidationIssue, ...] = (),
    ) -> None:
        super().__init__(message)
        self.reason_counts = dict(reason_counts or {})
        self.evidence = evidence
        self.issues = tuple(sorted(issues, key=issue_sort_key))


ValidationSummary = LayeredValidationResult


def validate_audit_data(data: pd.DataFrame, config: AuditConfig) -> ValidationSummary:
    """Validate every row condition against the unchanged original frame."""

    required = _required_columns(config)
    missing_columns = sorted(required.difference(data.columns))
    if missing_columns:
        issue = make_issue("missing_required_column", affected_fields=tuple(missing_columns), evidence=ValidationIssueEvidence(count=len(missing_columns)))
        raise DataValidationError(f"missing required columns: {', '.join(missing_columns)}", issues=(issue,))
    if data.empty:
        issue = make_issue("no_eligible_rows", evidence=ValidationIssueEvidence(count=0))
        raise DataValidationError("audit data must contain at least one row", issues=(issue,))

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
    evidence.sort(
        key=lambda item: (
            item.reason.value,
            item.attribute or "",
            type(item.observed_value).__name__,
            repr(item.observed_value),
        )
    )

    masks = {
        ExclusionReason.MISSING_REQUIRED_VALUE: missing_rows,
        ExclusionReason.UNKNOWN_PROTECTED_GROUP: unknown_rows,
        ExclusionReason.DUPLICATE_RECORD: duplicate_rows,
        ExclusionReason.NON_FINITE_NUMERIC: non_finite_rows,
        ExclusionReason.UNEXPECTED_CATEGORY: unexpected_rows,
    }
    counts = {reason: int(mask.sum()) for reason, mask in masks.items() if mask.any()}
    rejected: list[str] = []
    failure_issues: list[ValidationIssue] = []
    if missing_rows.any() and config.missing_value_policy == "error":
        rejected.append(f"{int(missing_rows.sum())} rows contain missing required values")
        failure_issues.append(make_issue("missing_required_value", affected_fields=tuple(sorted(column for column in required if relevant[column].isna().any())), evidence=ValidationIssueEvidence(count=int(missing_rows.sum()))))
    if unknown_rows.any() and config.unknown_group_policy == "error":
        rejected.append(f"{int(unknown_rows.sum())} rows contain unknown protected groups")
        failure_issues.append(make_issue("unknown_protected_group", affected_fields=tuple(sorted(attribute for attribute in config.protected_attributes if _outside_typed_set(data[attribute], config.allowed_groups[attribute]).any())), evidence=ValidationIssueEvidence(count=int(unknown_rows.sum()))))
    if duplicate_rows.any() and config.duplicate_policy == "error":
        rejected.append(f"{int(duplicate_rows.sum())} rows are duplicate records")
        failure_issues.append(make_issue("duplicate_record", affected_fields=((config.record_id_column,) if config.record_id_column else ()), evidence=ValidationIssueEvidence(count=int(duplicate_rows.sum()))))
    if non_finite_rows.any():
        rejected.append(f"{int(non_finite_rows.sum())} rows contain non-finite numeric values")
        failure_issues.append(make_issue("non_finite_numeric", affected_fields=tuple(sorted(column for column in _numeric_columns(config) if data[column].map(_is_infinite_number).any())), evidence=ValidationIssueEvidence(count=int(non_finite_rows.sum()))))
    if unexpected_rows.any():
        rejected.append(f"{int(unexpected_rows.sum())} rows contain unexpected categories")
        failure_issues.append(make_issue("unexpected_category", affected_fields=tuple(sorted(column for column, expected in config.expected_categories.items() if _outside_typed_set(data[column], expected).any())), evidence=ValidationIssueEvidence(count=int(unexpected_rows.sum()))))
    if rejected:
        raise DataValidationError(
            "; ".join(rejected), reason_counts=counts, evidence=tuple(evidence), issues=tuple(failure_issues)
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
        issue = make_issue("no_eligible_rows", evidence=ValidationIssueEvidence(count=0, reason_counts={reason.value: count for reason, count in counts.items()}))
        raise DataValidationError("no eligible rows remain after exclusion handling", reason_counts=counts, evidence=tuple(evidence), issues=(issue,))

    try:
        _validate_numeric_columns(eligible, config)
    except DataValidationError as error:
        error.reason_counts = dict(counts)
        error.evidence = tuple(evidence)
        raise
    if config.record_id_column is not None and _duplicate_mask(eligible, config).any():
        count = int(_duplicate_mask(eligible, config).sum())
        issue = make_issue("non_unique_record_id", affected_fields=(config.record_id_column,), evidence=ValidationIssueEvidence(count=count))
        raise DataValidationError("record_id_column must be unique in eligible data", reason_counts=counts, evidence=tuple(evidence), issues=(issue,))
    if not _contains_typed_value(eligible[config.outcome_column], config.favorable_label):
        issue = make_issue("favorable_label_absent", affected_fields=(config.outcome_column,), evidence=ValidationIssueEvidence(expected=config.favorable_label))
        raise DataValidationError("favorable_label is not present in outcome_column", reason_counts=counts, evidence=tuple(evidence), issues=(issue,))
    if config.decision_column is not None and not _contains_typed_value(
        eligible[config.decision_column], config.favorable_decision_label
    ):
        issue = make_issue("favorable_decision_label_absent", affected_fields=(config.decision_column,), evidence=ValidationIssueEvidence(expected=config.favorable_decision_label))
        raise DataValidationError("favorable_decision_label is not present in decision_column", reason_counts=counts, evidence=tuple(evidence), issues=(issue,))

    small_groups: list[str] = []
    reliability_issues: list[ValidationIssue] = []
    for attribute in config.protected_attributes:
        reference = config.reference_groups[attribute]
        if not _contains_typed_value(eligible[attribute], reference):
            issue = make_issue("reference_group_absent", affected_fields=(attribute,), affected_groups=(AffectedGroup(attributes={attribute: reference}),), evidence=ValidationIssueEvidence(expected=reference))
            raise DataValidationError(f"reference group {reference!r} is not present in {attribute!r}", reason_counts=counts, evidence=tuple(evidence), issues=(issue,))
        for value, count in _typed_value_counts(eligible[attribute]):
            if count < config.minimum_group_size:
                small_groups.append(f"{attribute}={value!r}")
                reliability_issues.append(make_issue("small_group", affected_fields=(attribute,), affected_groups=(AffectedGroup(attributes={attribute: value}),), evidence=ValidationIssueEvidence(count=count, minimum=config.minimum_group_size)))

    ordered_counts = tuple(sorted((reason.value, count) for reason, count in counts.items()))
    structural_issues: list[ValidationIssue] = []
    for code, mask, fields, policy_excludes in (
        ("missing_required_value", missing_rows, tuple(sorted(column for column in required if relevant[column].isna().any())), config.missing_value_policy == "exclude"),
        ("unknown_protected_group", unknown_rows, tuple(sorted(config.protected_attributes)), config.unknown_group_policy == "exclude"),
        ("duplicate_record", duplicate_rows, ((config.record_id_column,) if config.record_id_column else ()), config.duplicate_policy == "exclude"),
    ):
        if mask.any() and policy_excludes:
            structural_issues.append(make_issue(code, affected_fields=fields, evidence=ValidationIssueEvidence(count=int(mask.sum())), severity=ValidationSeverity.WARNING, blocking=False))
    profile = _build_single_run_profile(
        data=data,
        eligible=eligible,
        config=config,
        reason_counts=counts,
        excluded_rows=int(excluded.sum()),
    )
    layers = (
        _make_layer(ValidationLayerId.STRUCTURAL, structural_issues),
        _make_layer(ValidationLayerId.SEMANTIC, []),
        _make_layer(ValidationLayerId.ANALYTICAL_RELIABILITY, reliability_issues),
        _make_layer(ValidationLayerId.DATA_QUALITY, list(profile.issues)),
    )
    statuses = tuple(layer.status for layer in layers)
    overall = aggregate_validation_status(statuses)
    return LayeredValidationResult(
        status=overall,
        technical_validation=ValidationStatus.WARNING if layers[0].status == ValidationStatus.WARNING else ValidationStatus.PASSED,
        input_rows=len(data),
        eligible_rows=len(eligible),
        excluded_rows=int(excluded.sum()),
        small_groups=tuple(sorted(small_groups)),
        exclusion_evidence=tuple(evidence),
        reason_counts=ordered_counts,
        duplicate_rows=int(duplicate_rows.sum()),
        layers=layers,
        profile=profile,
    )


def _make_layer(layer: ValidationLayerId, issues: list[ValidationIssue]) -> ValidationLayerResult:
    ordered = tuple(sorted(issues, key=issue_sort_key))
    if any(issue.severity == ValidationSeverity.ERROR for issue in ordered):
        status = ValidationStatus.FAILED
    elif any(issue.severity == ValidationSeverity.WARNING for issue in ordered):
        status = ValidationStatus.WARNING
    elif ordered and all(issue.code == "data_freshness_unavailable" for issue in ordered):
        status = ValidationStatus.PASSED
    elif ordered:
        status = ValidationStatus.NOT_EVALUATED
    else:
        status = ValidationStatus.PASSED
    return ValidationLayerResult(layer=layer, status=status, issues=ordered)


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
        issue = make_issue("non_numeric_score", affected_fields=(config.score_column,))
        raise DataValidationError("score_column must have a non-boolean real numeric dtype", issues=(issue,))
    if config.sample_weight_column is not None:
        weights = data[config.sample_weight_column]
        if (
            pd.api.types.is_bool_dtype(weights.dtype)
            or pd.api.types.is_complex_dtype(weights.dtype)
            or not pd.api.types.is_numeric_dtype(weights)
        ):
            issue = make_issue("non_numeric_weight", affected_fields=(config.sample_weight_column,))
            raise DataValidationError("sample weights must have a non-boolean real numeric dtype", issues=(issue,))
        if (weights < 0).any():
            issue = make_issue("negative_weight", affected_fields=(config.sample_weight_column,), evidence=ValidationIssueEvidence(count=int((weights < 0).sum())))
            raise DataValidationError("sample weights must be non-negative with a positive sum", issues=(issue,))
        if float(weights.sum()) <= 0:
            issue = make_issue("non_positive_weight_total", affected_fields=(config.sample_weight_column,), evidence=ValidationIssueEvidence(total=float(weights.sum())))
            raise DataValidationError("sample weights must be non-negative with a positive sum", issues=(issue,))


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


def _build_single_run_profile(
    *,
    data: pd.DataFrame,
    eligible: pd.DataFrame,
    config: AuditConfig,
    reason_counts: dict[ExclusionReason, int],
    excluded_rows: int,
) -> SingleRunProfile:
    input_rows = len(data)
    eligible_rows = len(eligible)
    required = tuple(sorted(_required_columns(config)))

    missingness: list[MissingnessProfile] = []
    for field in required:
        missing_count = int(data[field].isna().sum())
        missingness.append(
            MissingnessProfile(
                field=field,
                group=None,
                missing_count=missing_count,
                total_count=input_rows,
                missing_rate=missing_count / input_rows,
            )
        )
        grouped: list[tuple[tuple[object, ...], AffectedGroup, pd.Series]] = []
        for attribute in sorted(config.protected_attributes):
            observed = [
                value
                for value, _ in _typed_value_counts(data[attribute].dropna())
                if any(_typed_values_equal(value, allowed) for allowed in config.allowed_groups[attribute])
            ]
            for value in sorted(observed, key=_typed_value_sort_key):
                mask = data[attribute].map(lambda actual: _typed_values_equal(actual, value))
                group = AffectedGroup(attributes={attribute: _python_label(value)})
                grouped.append(((attribute, *_typed_value_sort_key(value)), group, mask))
        for _, group, mask in sorted(grouped, key=lambda item: item[0]):
            total = int(mask.sum())
            missing = int(data.loc[mask, field].isna().sum())
            missingness.append(
                MissingnessProfile(
                    field=field,
                    group=group,
                    missing_count=missing,
                    total_count=total,
                    missing_rate=missing / total,
                )
            )

    groups: list[GroupSizeProfile] = []
    for attribute in sorted(config.protected_attributes):
        reference = config.reference_groups[attribute]
        for value in sorted(config.allowed_groups[attribute], key=_typed_value_sort_key):
            label = _python_label(value)
            group = AffectedGroup(attributes={attribute: label})
            for population, frame in (("input", data), ("eligible", eligible)):
                count = int(frame[attribute].map(lambda actual: _typed_values_equal(actual, value)).sum())
                total = len(frame)
                groups.append(
                    GroupSizeProfile(
                        group=group,
                        population=population,
                        count=count,
                        total_count=total,
                        proportion=count / total,
                        is_reference=_typed_values_equal(value, reference),
                    )
                )

    anomalies = tuple(
        AnomalyProfile(
            code=reason,
            count=reason_counts.get(reason, 0),
            total_count=input_rows,
            rate=reason_counts.get(reason, 0) / input_rows,
        )
        for reason in sorted(ExclusionReason, key=lambda item: item.value)
    )

    values = sorted(_canonical_binary64(value) for value in eligible[config.score_column].tolist())
    score_distribution = _numeric_distribution(config.score_column, values)
    quantiles = {float(item.probability): float(item.value) for item in score_distribution.quantiles}
    outliers = _outlier_profile(config.score_column, values, quantiles[0.25], quantiles[0.75])

    outcome_distribution = tuple(
        CategoryCount(
            value=_python_label(value),
            count=count,
            total_count=eligible_rows,
            proportion=count / eligible_rows,
        )
        for value, count in sorted(
            _typed_value_counts(eligible[config.outcome_column]),
            key=lambda item: _typed_value_sort_key(item[0]),
        )
    )

    freshness, freshness_issue = _freshness_profile(config)
    issues: list[ValidationIssue] = []
    if outliers.outlier_count:
        issues.append(
            make_issue(
                "score_outliers_observed",
                affected_fields=(config.score_column,),
                evidence=ValidationIssueEvidence(
                    count=outliers.outlier_count,
                    total=outliers.total_count,
                    minimum=outliers.lower_fence,
                    maximum=outliers.upper_fence,
                ),
            )
        )
    if freshness_issue is not None:
        issues.append(freshness_issue)

    return SingleRunProfile(
        input_rows=input_rows,
        eligible_rows=eligible_rows,
        excluded_rows=excluded_rows,
        missingness=tuple(missingness),
        groups=tuple(groups),
        anomalies=anomalies,
        score_distribution=score_distribution,
        outcome_distribution=outcome_distribution,
        outliers=outliers,
        freshness=freshness,
        issues=tuple(sorted(issues, key=issue_sort_key)),
    )


def _canonical_binary64(value: object) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError("profile scores must convert to finite binary64 values")
    return 0.0 if converted == 0.0 else converted


def _finite_derived(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"derived profile {name} must be finite")
    return 0.0 if value == 0.0 else value


def _type7_quantile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return _finite_derived(
        values[lower] + fraction * (values[upper] - values[lower]),
        "quantile",
    )


def _numeric_distribution(field: str, values: list[float]) -> NumericDistributionProfile:
    try:
        mean = _finite_derived(math.fsum(values) / len(values), "mean")
        squared_deviations = []
        for value in values:
            deviation = value - mean
            squared_deviations.append(_finite_derived(deviation**2, "squared deviation"))
        variance = _finite_derived(math.fsum(squared_deviations) / len(values), "variance")
        if variance < 0:
            raise ValueError("derived profile variance must not be negative")
        standard_deviation = _finite_derived(math.sqrt(variance), "standard deviation")
        quantiles = tuple(
            QuantileValue(probability=probability, value=_type7_quantile(values, probability))
            for probability in (0.0, 0.25, 0.5, 0.75, 1.0)
        )
    except (ArithmeticError, OverflowError, ValueError) as error:
        raise ValueError("score distribution invariant failure") from error
    return NumericDistributionProfile(
        field=field,
        count=len(values),
        minimum=values[0],
        maximum=values[-1],
        mean=mean,
        standard_deviation=standard_deviation,
        quantiles=quantiles,
    )


def _outlier_profile(field: str, values: list[float], q1: float, q3: float) -> OutlierProfile:
    try:
        iqr = _finite_derived(q3 - q1, "IQR")
        lower_fence = _finite_derived(q1 - 1.5 * iqr, "lower fence")
        upper_fence = _finite_derived(q3 + 1.5 * iqr, "upper fence")
    except (ArithmeticError, OverflowError, ValueError) as error:
        raise ValueError("score outlier invariant failure") from error
    lower_count = sum(value < lower_fence for value in values)
    upper_count = sum(value > upper_fence for value in values)
    outlier_count = lower_count + upper_count
    return OutlierProfile(
        field=field,
        q1=q1,
        q3=q3,
        iqr=iqr,
        lower_fence=lower_fence,
        upper_fence=upper_fence,
        lower_count=lower_count,
        upper_count=upper_count,
        total_count=len(values),
        outlier_count=outlier_count,
        outlier_rate=outlier_count / len(values),
    )


def _utc_z(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")


def _freshness_profile(config: AuditConfig) -> tuple[FreshnessProfile, ValidationIssue | None]:
    execution = _utc_z(config.execution_timestamp)
    if config.data_as_of is None:
        return (
            FreshnessProfile(
                status="unavailable",
                data_as_of=None,
                execution_timestamp=execution,
                age_seconds=None,
                reason_code="data_freshness_unavailable",
            ),
            make_issue("data_freshness_unavailable"),
        )
    data_as_of = _utc_z(config.data_as_of)
    if config.data_as_of > config.execution_timestamp:
        return (
            FreshnessProfile(
                status="future_dated",
                data_as_of=data_as_of,
                execution_timestamp=execution,
                age_seconds=None,
                reason_code="data_as_of_after_execution",
            ),
            make_issue(
                "data_as_of_after_execution",
                evidence=ValidationIssueEvidence(observed=data_as_of, expected=execution),
            ),
        )
    age_seconds = math.floor((config.execution_timestamp - config.data_as_of).total_seconds())
    return (
        FreshnessProfile(
            status="available",
            data_as_of=data_as_of,
            execution_timestamp=execution,
            age_seconds=age_seconds,
            reason_code=None,
        ),
        None,
    )


def _typed_value_sort_key(value: object) -> tuple[int, object]:
    if pd.api.types.is_bool(value):
        return (0, bool(value))
    if pd.api.types.is_integer(value):
        return (1, int(value))
    if isinstance(value, str):
        return (2, value)
    raise TypeError(f"unsupported typed label {value!r}")


def _python_label(value: object) -> bool | int | str:
    rank, canonical = _typed_value_sort_key(value)
    if rank == 0:
        return bool(canonical)
    if rank == 1:
        return int(canonical)
    return str(canonical)
