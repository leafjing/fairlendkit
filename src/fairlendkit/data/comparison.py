"""Deterministic Epic 2.2 baseline profile comparison."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from fairlendkit.config import AuditConfig
from fairlendkit.data.contracts import (
    AffectedGroup,
    BaselineComparisonPolicy,
    BaselineComparisonResult,
    BaselineSelection,
    ChangeFlag,
    ComparisonCheck,
    LayeredValidationResult,
    ValidationIssue,
    ValidationIssueEvidence,
    ValidationLayerId,
    ValidationLayerResult,
    aggregate_validation_status,
    issue_sort_key,
    make_issue,
)


def canonical_profile_digest(profile: object) -> str:
    """Return the lowercase SHA-256 of canonical profile JSON."""
    if hasattr(profile, "model_dump"):
        profile = profile.model_dump(mode="json")
    payload = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _typed(value: object) -> dict[str, object]:
    rank = "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) else "string"
    return {"type": rank, "value": value}


def _typed_key(value: object) -> tuple[int, object]:
    return (0, value) if isinstance(value, bool) else (1, value) if isinstance(value, int) else (2, value)


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _check_id(code: str, scope: dict[str, object]) -> str:
    return f"{code}:{_digest(scope)}"


def _flag_id(code: str, check_id: str) -> str:
    return f'{code}:{_digest({"code": code, "source_check_id": check_id})}'


def _required_fields(profile: object) -> tuple[str, ...]:
    return tuple(item.field for item in profile.missingness if item.group is None)


def _manifest(current: LayeredValidationResult, config: AuditConfig, baseline_categories: tuple[object, ...] = ()) -> list[dict[str, Any]]:
    profile = current.profile
    if profile is None:
        raise ValueError("current validation must contain a complete Epic 2.1 profile")
    entries: list[dict[str, Any]] = []
    for attribute in sorted(config.protected_attributes):
        for value in sorted(config.allowed_groups[attribute], key=_typed_key):
            group = AffectedGroup(attributes={attribute: value})
            entries.append(dict(code="group_proportion_absolute_delta", scope={"field": attribute, "group": {attribute: _typed(value)}}, threshold="group", affected_fields=(attribute,), affected_groups=(group,)))
    for field in _required_fields(profile):
        entries.append(dict(code="missingness_rate_absolute_delta", scope={"field": field}, threshold="missing", affected_fields=(field,), affected_groups=()))
        for attribute in sorted(config.protected_attributes):
            for value in sorted(config.allowed_groups[attribute], key=_typed_key):
                group = AffectedGroup(attributes={attribute: value})
                entries.append(dict(code="missingness_rate_absolute_delta", scope={"field": field, "group": {attribute: _typed(value)}}, threshold="missing", affected_fields=tuple(sorted({field, attribute})), affected_groups=(group,)))
    for probability in (0.0, 0.25, 0.5, 0.75, 1.0):
        entries.append(dict(code="score_quantile_absolute_delta", scope={"field": config.score_column, "quantile_probability": probability}, threshold="score", affected_fields=(config.score_column,), affected_groups=(), quantile_probability=probability))
    categories = {(_typed_key(item.value)): item.value for item in profile.outcome_distribution}
    categories.update({_typed_key(value): value for value in baseline_categories})
    for code, threshold in (("outcome_category_presence_equal", "equal"), ("outcome_proportion_absolute_delta", "outcome")):
        for key in sorted(categories):
            value = categories[key]
            entries.append(dict(code=code, scope={"field": config.outcome_column, "category": _typed(value)}, threshold=threshold, affected_fields=(config.outcome_column,), affected_groups=(), category=value))
    for code, field in (("dataset_version_equal", "dataset_version"), ("model_version_equal", "model_version")):
        entries.append(dict(code=code, scope={}, threshold="equal", affected_fields=(field,), affected_groups=()))
    return entries


def _policy_threshold(policy: BaselineComparisonPolicy, name: str) -> object:
    return {"group": policy.group_proportion_delta, "missing": policy.missingness_rate_delta, "score": policy.score_quantile_delta, "outcome": policy.outcome_proportion_delta, "equal": "equal"}[name]


def _non_evaluated(manifest: list[dict[str, Any]], selection: BaselineSelection, policy: BaselineComparisonPolicy, status: str, reason: str) -> tuple[ComparisonCheck, ...]:
    return tuple(ComparisonCheck(check_id=_check_id(item["code"], item["scope"]), code=item["code"], status=status, statistic=None, threshold=_policy_threshold(policy, item["threshold"]), current_value=None, baseline_value=None, baseline_id=selection.baseline_id, affected_fields=item["affected_fields"], affected_groups=item["affected_groups"], reason_code=reason, quantile_probability=item.get("quantile_probability"), category=item.get("category")) for item in manifest)


def _compatibility_reason(current: LayeredValidationResult, current_config: AuditConfig, baseline: LayeredValidationResult, baseline_config: AuditConfig, selection: BaselineSelection) -> str | None:
    if current.profile is None or baseline.profile is None or current.profile.schema_version != "1.0" or baseline.profile.schema_version != "1.0":
        return "profile_schema_mismatch"
    try:
        current.profile.model_validate(current.profile.model_dump())
        baseline.profile.model_validate(baseline.profile.model_dump())
    except Exception:
        return "profile_invariant_failure"
    if selection.profile_digest != canonical_profile_digest(baseline.profile):
        return "baseline_digest_mismatch"
    semantic = (
        "outcome_column",
        "score_column",
        "favorable_label",
        "favorable_decision_label",
        "score_type",
        "score_direction",
    )
    if any(getattr(current_config, name) != getattr(baseline_config, name) for name in semantic) or _required_fields(current.profile) != _required_fields(baseline.profile):
        return "analysis_semantics_mismatch"
    if current_config.protected_attributes != baseline_config.protected_attributes or current_config.allowed_groups != baseline_config.allowed_groups or current_config.reference_groups != baseline_config.reference_groups:
        return "group_definition_mismatch"
    profile_methods = ("population_definition", "sampling_definition")
    if (
        current.profile.score_distribution.method != baseline.profile.score_distribution.method
        or any(getattr(current_config, name) != getattr(baseline_config, name) for name in profile_methods)
    ):
        return "profile_method_mismatch"
    return None


def compare_profiles(current: LayeredValidationResult, current_config: AuditConfig, baseline: LayeredValidationResult | None, baseline_config: AuditConfig | None, selection: BaselineSelection, policy: BaselineComparisonPolicy) -> BaselineComparisonResult:
    """Compare a current single-run profile with one explicit baseline."""
    if (baseline is None) != (baseline_config is None):
        raise ValueError("baseline and baseline_config must be both present or both absent")
    if current.profile is None:
        raise ValueError("current validation must contain a profile")
    current_digest = canonical_profile_digest(current.profile)
    manifest = _manifest(current, current_config)
    if baseline is None:
        checks = _non_evaluated(manifest, selection, policy, "unavailable", "baseline_unavailable")
        issue = make_issue("comparison_baseline_unavailable", evidence=ValidationIssueEvidence(source_check_ids=tuple(c.check_id for c in checks)))
        return BaselineComparisonResult(baseline=selection, current_profile_digest=current_digest, status="unavailable", policy=policy, checks=checks, flags=(), issues=(issue,))
    reason = _compatibility_reason(current, current_config, baseline, baseline_config, selection)
    if reason:
        checks = _non_evaluated(manifest, selection, policy, "incompatible", reason)
        issue = make_issue("comparison_baseline_incompatible", evidence=ValidationIssueEvidence(source_check_ids=tuple(c.check_id for c in checks)))
        return BaselineComparisonResult(baseline=selection, current_profile_digest=current_digest, status="incompatible", policy=policy, checks=checks, flags=(), issues=(issue,))
    assert baseline.profile is not None and baseline_config is not None
    manifest = _manifest(current, current_config, tuple(item.value for item in baseline.profile.outcome_distribution))
    checks = tuple(_evaluate(item, current, current_config, baseline, baseline_config, selection, policy) for item in manifest)
    flags = tuple(_make_flags(checks))
    issues = _comparison_issues(checks, flags)
    status = "partially_completed" if any(c.status == "not_computable" for c in checks) else "completed"
    return BaselineComparisonResult(baseline=selection, current_profile_digest=current_digest, status=status, policy=policy, checks=checks, flags=flags, issues=issues)


def _evaluate(item: dict[str, Any], current: LayeredValidationResult, current_config: AuditConfig, baseline: LayeredValidationResult, baseline_config: AuditConfig, selection: BaselineSelection, policy: BaselineComparisonPolicy) -> ComparisonCheck:
    code = item["code"]
    cp, bp = current.profile, baseline.profile
    assert cp is not None and bp is not None
    status, reason, statistic = "evaluated", None, "exact_equality"
    current_value: object | None
    baseline_value: object | None
    group = item["affected_groups"][0] if item["affected_groups"] else None
    if code == "group_proportion_absolute_delta":
        def group_value(profile: object) -> float:
            return float(next(x.proportion for x in profile.groups if x.population == "eligible" and x.group == group))
        current_value, baseline_value, statistic = group_value(cp), group_value(bp), "absolute_proportion_delta"
    elif code == "missingness_rate_absolute_delta":
        field = item["scope"]["field"]
        def missing_value(profile: object) -> float | None:
            found = next((x for x in profile.missingness if x.field == field and x.group == group), None)
            return None if found is None else float(found.missing_rate)
        current_value, baseline_value, statistic = missing_value(cp), missing_value(bp), "absolute_rate_delta"
        if current_value is None or baseline_value is None:
            status, reason, current_value, baseline_value, statistic = "not_computable", "zero_group_sample", None, None, None
    elif code == "score_quantile_absolute_delta":
        probability = item["quantile_probability"]
        current_value = float(next(x.value for x in cp.score_distribution.quantiles if float(x.probability) == probability))
        baseline_value = float(next(x.value for x in bp.score_distribution.quantiles if float(x.probability) == probability))
        statistic = "absolute_quantile_delta"
    elif code == "outcome_category_presence_equal":
        category = item["category"]
        current_value = any(type(x.value) is type(category) and x.value == category for x in cp.outcome_distribution)
        baseline_value = any(type(x.value) is type(category) and x.value == category for x in bp.outcome_distribution)
    elif code == "outcome_proportion_absolute_delta":
        category = item["category"]
        def proportion(profile: object) -> float:
            found = next((x for x in profile.outcome_distribution if type(x.value) is type(category) and x.value == category), None)
            return 0.0 if found is None else float(found.proportion)
        current_value, baseline_value, statistic = proportion(cp), proportion(bp), "absolute_proportion_delta"
    else:
        field = "dataset_version" if code.startswith("dataset") else "model_version"
        current_value, baseline_value = getattr(current_config, field), getattr(baseline_config, field)
        if current_value is None or baseline_value is None:
            status, reason, current_value, baseline_value, statistic = "not_computable", "version_unavailable", None, None, None
    return ComparisonCheck(check_id=_check_id(code, item["scope"]), code=code, status=status, statistic=statistic, threshold=_policy_threshold(policy, item["threshold"]), current_value=current_value, baseline_value=baseline_value, baseline_id=selection.baseline_id, affected_fields=item["affected_fields"], affected_groups=item["affected_groups"], reason_code=reason, quantile_probability=item.get("quantile_probability"), category=item.get("category"))


def _make_flags(checks: tuple[ComparisonCheck, ...]):
    for check in checks:
        if check.status != "evaluated":
            continue
        code = None
        if check.threshold == "equal" and check.current_value != check.baseline_value:
            if check.code == "outcome_category_presence_equal": code = "outcome_category_added" if check.current_value else "outcome_category_removed"
            elif check.code == "dataset_version_equal": code = "dataset_version_changed"
            elif check.code == "model_version_equal": code = "model_version_changed"
        elif check.threshold != "equal" and abs(float(check.current_value) - float(check.baseline_value)) >= float(check.threshold):
            code = {"group_proportion_absolute_delta": "group_composition_changed", "missingness_rate_absolute_delta": "missingness_changed", "score_quantile_absolute_delta": "score_distribution_changed", "outcome_proportion_absolute_delta": "outcome_distribution_changed"}[check.code]
        if code:
            yield ChangeFlag(flag_id=_flag_id(code, check.check_id), code=code, source_check_id=check.check_id, statistic=check.statistic, threshold=check.threshold, current_value=check.current_value, baseline_value=check.baseline_value, baseline_id=check.baseline_id, affected_fields=check.affected_fields, affected_groups=check.affected_groups, quantile_probability=check.quantile_probability, category=check.category)


def _comparison_issues(checks: tuple[ComparisonCheck, ...], flags: tuple[ChangeFlag, ...]) -> tuple[ValidationIssue, ...]:
    issues = []
    if any(c.status == "not_computable" for c in checks):
        issues.append(make_issue("comparison_check_not_computable", evidence=ValidationIssueEvidence(source_check_ids=tuple(c.check_id for c in checks if c.status == "not_computable"))))
    for code in sorted({flag.code for flag in flags}):
        source = tuple(flag for flag in flags if flag.code == code)
        issues.append(make_issue(code, affected_fields=tuple(field for flag in source for field in flag.affected_fields), affected_groups=tuple(group for flag in source for group in flag.affected_groups), evidence=ValidationIssueEvidence(source_flag_ids=tuple(flag.flag_id for flag in source))))
    return tuple(sorted(issues, key=issue_sort_key))


def attach_baseline_comparison(current: LayeredValidationResult, comparison: BaselineComparisonResult) -> LayeredValidationResult:
    if current.profile is None or canonical_profile_digest(current.profile) != comparison.current_profile_digest:
        raise ValueError("comparison current profile digest does not match")
    if current.comparison is not None:
        raise ValueError("a baseline comparison is already attached")
    layers = list(current.layers)
    index = next(i for i, layer in enumerate(layers) if layer.layer == ValidationLayerId.DATA_QUALITY)
    issues = tuple(sorted((*current.profile.issues, *comparison.issues), key=issue_sort_key))
    status = "warning" if any(issue.severity == "warning" for issue in issues) else "passed"
    layers[index] = ValidationLayerResult(layer="data_quality", status=status, issues=issues)
    overall = aggregate_validation_status(tuple(layer.status for layer in layers))
    payload = current.model_dump()
    payload.update(comparison=comparison, layers=tuple(layers), status=overall)
    return LayeredValidationResult.model_validate(payload)
