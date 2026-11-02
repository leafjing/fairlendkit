"""Deterministic AD-4 potential-proxy screening.

The public API accepts contracted entity evidence, fits only the frozen internal
protected-group diagnostic estimator, and returns disclosure-controlled
screening evidence. It never accepts caller-supplied predictions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
from html import escape
import io
import json
import math
from struct import pack
from typing import Any, Callable, Iterable, Sequence

from pydantic import Field, ValidationError, field_validator, model_validator

from fairlendkit.alternative_data.contracts import StrictModel
from fairlendkit.alternative_data.suppression import _CountCell, _apply_suppression
from fairlendkit.metrics.bootstrap import RNG_NAME, bootstrap_index_draws, type7_quantile


class ProxyWindow(StrEnum):
    DEVELOPMENT = "development"
    HOLDOUT = "holdout"


class CandidateKind(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


class ProxyReason(StrEnum):
    WEIGHTING_UNSUPPORTED = "ad_proxy_weighting_unsupported"
    CANDIDATE_PROHIBITED = "ad_proxy_candidate_prohibited"
    ENTITY_CONFLICT = "ad_proxy_entity_conflict"
    WINDOW_CONFLICT = "ad_proxy_window_conflict"
    ISOLATION_FAILURE = "ad_proxy_isolation_failure"
    PROTECTED_MISSING = "ad_proxy_protected_missing"
    STATISTIC_UNDEFINED = "ad_proxy_statistic_undefined"
    PAIRED_POPULATION_MISMATCH = "ad_proxy_paired_population_mismatch"
    INSUFFICIENT_FOLD_SUPPORT = "ad_insufficient_fold_support"
    MODEL_NONCONVERGENCE = "ad_proxy_model_nonconvergence"
    HIGH_CARDINALITY = "ad_high_cardinality_unsupported"
    INSUFFICIENT_RESAMPLES = "ad_proxy_insufficient_resamples"
    STRATA_NOT_COMPARABLE = "ad_proxy_strata_not_comparable"
    STRATUM_SUPPORT = "ad_proxy_stratum_support"
    HOLDOUT_UNSTABLE = "ad_proxy_holdout_unstable"
    STRATUM_UNSTABLE = "ad_proxy_stratum_unstable"
    THRESHOLD_NOT_MET = "ad_proxy_threshold_not_met"
    SPARSE = "ad_sparse_report_cell"
    COMPLEMENTARY = "ad_complementary_suppression"


_REASON_CONTRACT = {
    ProxyReason.WEIGHTING_UNSUPPORTED: ("error", "Proxy-screening configuration requests weighted eligibility, fitting, metrics, bootstrap, or suppression."),
    ProxyReason.CANDIDATE_PROHIBITED: ("error", "A candidate or baseline field is protected-derived, outcome, decision, post-decision, identifier, free text, exact geolocation, fold, weight, provider key, leakage-rejected, or otherwise prohibited by the proxy contract."),
    ProxyReason.ENTITY_CONFLICT: ("error", "One proxy-screening entity has conflicting protected, candidate, baseline, provider, coverage, or reducer values after authoritative reduction."),
    ProxyReason.WINDOW_CONFLICT: ("error", "Proxy-screening development and temporal-holdout windows are not strictly forward and non-overlapping."),
    ProxyReason.ISOLATION_FAILURE: ("error", "An entity, fitted transform, category vocabulary, or target-derived value crosses a proxy-screening fold or development/holdout boundary."),
    ProxyReason.PROTECTED_MISSING: ("exclude", "An entity lacks the user-supplied protected attribute required by this proxy screen."),
    ProxyReason.STATISTIC_UNDEFINED: ("unavailable", "A proxy statistic has no defined denominator, required class comparison, finite value, or corrected contingency dimension."),
    ProxyReason.PAIRED_POPULATION_MISMATCH: ("error", "Baseline and baseline-plus-candidate proxy evidence do not contain the exact same canonically ordered entity population."),
    ProxyReason.INSUFFICIENT_FOLD_SUPPORT: ("unavailable", "Proxy-screening folds do not meet configured entity and class support."),
    ProxyReason.HIGH_CARDINALITY: ("unavailable", "Candidate categories exceed the configured supported maximum after rare-level mapping."),
    ProxyReason.MODEL_NONCONVERGENCE: ("unavailable", "The versioned proxy-screening model did not converge."),
    ProxyReason.HOLDOUT_UNSTABLE: ("observe", "Temporal-holdout evidence exceeds the configured stability tolerance."),
    ProxyReason.STRATA_NOT_COMPARABLE: ("unavailable", "Provider or coverage stability lacks at least two nonempty supported strata in both development and holdout."),
    ProxyReason.STRATUM_SUPPORT: ("unavailable", "A required provider or coverage stratum lacks configured entity, class, or bootstrap support."),
    ProxyReason.STRATUM_UNSTABLE: ("observe", "Supported provider or coverage evidence exceeds the configured stability tolerance."),
    ProxyReason.SPARSE: ("unavailable", "Distinct-entity count is below the configured disclosure minimum."),
    ProxyReason.COMPLEMENTARY: ("unavailable", "An additional cell is hidden to prevent recovery of a sparse value."),
}


class ProxyFailure(ValueError):
    """Stable, payload-free contract failure."""

    def __init__(self, reason: ProxyReason):
        self.reason_code = reason.value
        self.disposition, self.canonical_message = _REASON_CONTRACT.get(
            reason, ("unavailable", reason.value)
        )
        super().__init__(self.reason_code)

    def errors(self) -> list[dict[str, object]]:
        """Return only the stable public contract, never rejected input."""

        return [{
            "type": "proxy_contract_error",
            "loc": [],
            "msg": self.canonical_message,
            "reason_code": self.reason_code,
            "disposition": self.disposition,
        }]

    def json(self) -> str:
        """Serialize the payload-free public error contract."""

        return json.dumps(self.errors(), sort_keys=True, separators=(",", ":"))


def _proxy_config_validation_reason(error: ValidationError) -> ProxyReason:
    """Collapse Pydantic configuration failures to stable public reasons."""

    messages = tuple(str(item.get("msg", "")) for item in error.errors(
        include_input=False,
        include_url=False,
    ))
    for reason in (
        ProxyReason.WEIGHTING_UNSUPPORTED,
        ProxyReason.CANDIDATE_PROHIBITED,
        ProxyReason.WINDOW_CONFLICT,
    ):
        if any(reason.value in message for message in messages):
            return reason
    # Structural, type, range, extra-field, and cross-field failures all make
    # the requested screening protocol unusable. Do not expose Pydantic's
    # rejected value or distinguish shapes in a way that can leak payloads.
    return ProxyReason.ISOLATION_FAILURE


def _proxy_entity_validation_reason(error: ValidationError) -> ProxyReason:
    """Collapse public entity validation failures without retaining input."""

    public_errors = error.errors(include_input=False, include_url=False)
    messages = tuple(str(item.get("msg", "")) for item in public_errors)
    if any(ProxyReason.WEIGHTING_UNSUPPORTED.value in message for message in messages):
        return ProxyReason.WEIGHTING_UNSUPPORTED
    locations = {tuple(item.get("loc", ())) for item in public_errors}
    if any(location and location[0] == "weight" for location in locations):
        return ProxyReason.WEIGHTING_UNSUPPORTED
    return ProxyReason.ISOLATION_FAILURE


class _ProxyInputModel(StrictModel):
    """Non-bypassable payload-free boundary for public proxy inputs."""

    @classmethod
    def _validation_reason(cls, error: ValidationError) -> ProxyReason:
        return ProxyReason.ISOLATION_FAILURE

    @classmethod
    def _run_public_validation(cls, validator: Callable[[], object]):
        reason: ProxyReason | None = None
        result: object | None = None
        try:
            result = validator()
        except ValidationError as error:
            reason = cls._validation_reason(error)
        # Raise outside the Pydantic handler so rejected input is not retained
        # by cause/context, regardless of which standard validator was called.
        if reason is not None:
            raise ProxyFailure(reason)
        assert result is not None
        return result

    def __init__(self, **data: object) -> None:
        reason: ProxyReason | None = None
        try:
            super().__init__(**data)
        except ValidationError as error:
            reason = type(self)._validation_reason(error)
        if reason is not None:
            raise ProxyFailure(reason)

    @classmethod
    def model_validate(cls, obj: object, **kwargs: object):
        return cls._run_public_validation(
            lambda: super(_ProxyInputModel, cls).model_validate(obj, **kwargs)
        )

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, **kwargs: object):
        return cls._run_public_validation(
            lambda: super(_ProxyInputModel, cls).model_validate_json(json_data, **kwargs)
        )

    @classmethod
    def model_validate_strings(cls, obj: object, **kwargs: object):
        return cls._run_public_validation(
            lambda: super(_ProxyInputModel, cls).model_validate_strings(obj, **kwargs)
        )


class _CategoryLevel(StrEnum):
    MISSING = "__internal_missing__"
    RARE = "__internal_rare__"
    UNSEEN = "__internal_unseen__"


class ProxyEntity(_ProxyInputModel):
    entity_id: str = Field(min_length=1)
    window: ProxyWindow
    candidate: float | int | str | bool | None
    protected: str | int | bool | None
    provider_stratum: str = Field(min_length=1)
    coverage_stratum: str = Field(min_length=1)
    baseline: tuple[float | int | str | bool | None, ...] = ()
    candidate_source_id: str = Field(min_length=1)
    candidate_derivation_version: str = Field(min_length=1)
    reducer_id: str = Field(min_length=1)
    reducer_version: str = Field(min_length=1)
    as_of_time: datetime
    candidate_available_time: datetime
    protected_observation_time: datetime
    baseline_available_time: datetime | None = None
    population_eligible: bool = True
    weight: float | None = None

    @classmethod
    def _validation_reason(cls, error: ValidationError) -> ProxyReason:
        return _proxy_entity_validation_reason(error)

    @field_validator("weight")
    @classmethod
    def finite_weight(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("ad_proxy_nonfinite_input")
        return value


class ProxyConfig(_ProxyInputModel):
    protocol_version: str = Field(min_length=1)
    population_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    protected_attribute_id: str = Field(min_length=1)
    baseline_id: str | None = None
    candidate_kind: CandidateKind
    candidate_source_id: str = Field(min_length=1)
    candidate_derivation_version: str = Field(min_length=1)
    reducer_id: str = Field(min_length=1)
    reducer_version: str = Field(min_length=1)
    baseline_kinds: tuple[CandidateKind, ...] = ()
    development_window: str = Field(min_length=1)
    holdout_window: str = Field(min_length=1)
    association_threshold: float = Field(ge=0, le=1)
    predictability_auc_threshold: float = Field(ge=.5, le=1)
    incremental_auc_threshold: float = Field(ge=0, le=1)
    stability_tolerance: float = Field(ge=0, le=1)
    fold_seed: int = Field(ge=0, le=2**64 - 1)
    fold_count: int = Field(ge=2)
    minimum_valid_folds: int = Field(ge=2)
    per_fold_class_minimum: int = Field(ge=1)
    provider_strata: tuple[str, ...] = Field(min_length=2)
    coverage_strata: tuple[str, ...] = Field(min_length=2)
    minimum_stratum_entities: int = Field(ge=2)
    maximum_categories: int = Field(ge=2)
    minimum_level_entities: int = Field(ge=1)
    minimum_report_cell_count: int = Field(ge=2)
    bootstrap_seed: int = Field(ge=0, le=2**64 - 1)
    bootstrap_resamples: int = Field(ge=1)
    minimum_valid_resamples: int = Field(ge=1)
    confidence_level: float = Field(gt=0, lt=1)
    weighting: str = "unweighted"

    @classmethod
    def _validation_reason(cls, error: ValidationError) -> ProxyReason:
        return _proxy_config_validation_reason(error)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.weighting != "unweighted":
            raise ValueError(ProxyReason.WEIGHTING_UNSUPPORTED.value)
        if self.minimum_valid_folds > self.fold_count:
            raise ValueError("minimum_valid_folds exceeds fold_count")
        if self.minimum_valid_resamples > self.bootstrap_resamples:
            raise ValueError("minimum_valid_resamples exceeds bootstrap_resamples")
        if self.minimum_stratum_entities < self.minimum_report_cell_count:
            raise ValueError("minimum_stratum_entities is below disclosure minimum")
        if len(set(self.provider_strata)) != len(self.provider_strata):
            raise ValueError("provider_strata must be unique")
        if len(set(self.coverage_strata)) != len(self.coverage_strata):
            raise ValueError("coverage_strata must be unique")
        if "other" not in self.provider_strata or "other" not in self.coverage_strata:
            raise ValueError("provider_strata and coverage_strata require an explicit other stratum")
        if self.development_window >= self.holdout_window:
            raise ValueError(ProxyReason.WINDOW_CONFLICT.value)
        if len(self.baseline_kinds) == 0 and self.baseline_id is not None:
            raise ValueError("baseline_id requires baseline_kinds")
        prohibited = {
            "protected", "protected_attribute", "entity_id", "record_id",
            "account_id", "obligation_id", "meter_id", "address",
            "permission_id", "revision_id", "reversal_id", "outcome",
            "decision", "label_maturity", "fold", "weight",
        }
        if self.candidate_id.casefold() in prohibited:
            raise ValueError(ProxyReason.CANDIDATE_PROHIBITED.value)
        return self


class ProxyEvidenceKey(StrictModel):
    window: ProxyWindow
    metric: str
    class_aggregation: str
    baseline_scope: str
    stratum_dimension: str
    stratum_id: str


class ProxyMetric(StrictModel):
    evidence_key: ProxyEvidenceKey
    state: str
    count_bucket: str | None = None
    reason_code: str | None = None
    eligible_count: int | None = None
    excluded_count: int | None = None
    missing_count: int | None = None
    denominator: int | None = None
    class_support: dict[str, int] | None = None
    point: float | None = None
    lower: float | None = None
    upper: float | None = None
    valid_resamples: int | None = None
    invalid_resamples: int | None = None
    reliable: bool | None = None

    @model_validator(mode="after")
    def disclosure_boundary(self):
        exact = (
            self.eligible_count, self.excluded_count, self.missing_count,
            self.denominator, self.class_support, self.point, self.lower,
            self.upper, self.valid_resamples, self.invalid_resamples,
            self.reliable,
        )
        if self.state != "published" and any(value is not None for value in exact):
            raise ValueError("hidden proxy evidence cannot expose exact values")
        if self.reliable is False and (self.lower is not None or self.upper is not None):
            raise ValueError("unreliable evidence cannot expose intervals")
        return self


class ProxyThresholdEvidence(StrictModel):
    development: ProxyEvidenceKey
    holdout: ProxyEvidenceKey


class ProxyStabilityReference(StrictModel):
    dimension: str
    stratum_id: str
    development_stratum: ProxyEvidenceKey
    development_overall: ProxyEvidenceKey
    holdout_stratum: ProxyEvidenceKey
    holdout_overall: ProxyEvidenceKey
    development_difference: float
    holdout_difference: float
    tolerance: float
    passed: bool


class ProxyTemporalReference(StrictModel):
    development: ProxyEvidenceKey
    holdout: ProxyEvidenceKey
    difference: float
    tolerance: float
    passed: bool


class ProxyScreeningFlag(StrictModel):
    flag_id: str
    rule_id: str = "potential-proxy-screen-v1"
    rule_version: str = "1"
    candidate_id: str
    protected_attribute_id: str
    metric: str
    class_aggregation: str
    baseline_id: str | None
    threshold: float
    stability_tolerance: float
    threshold_evidence: ProxyThresholdEvidence
    temporal: ProxyTemporalReference
    provider: tuple[ProxyStabilityReference, ...]
    coverage_stratum: tuple[ProxyStabilityReference, ...]
    population_contract: str
    fold_contract: str
    bootstrap_contract: str
    review_prompt: str = "Review as potential proxy-risk screening evidence only."


class ProxyTrace(StrictModel):
    protocol_version: str
    population_id: str
    candidate_id: str
    protected_attribute_id: str
    baseline_id: str | None
    candidate_source_id: str
    candidate_derivation_version: str
    reducer_id: str
    reducer_version: str
    candidate_kind: CandidateKind
    baseline_kinds: tuple[CandidateKind, ...]
    association_threshold: float
    predictability_auc_threshold: float
    incremental_auc_threshold: float
    stability_tolerance: float
    provider_strata: tuple[str, ...]
    coverage_strata: tuple[str, ...]
    weighting: str
    development_window: str
    holdout_window: str
    fold_seed_fingerprint: str
    fold_count: int
    minimum_valid_folds: int
    per_fold_class_minimum: int
    optimizer: str
    optimizer_tolerance: float
    optimizer_max_iterations: int
    optimizer_max_halvings: int
    rng_identity: str
    bootstrap_seed_fingerprint: str
    bootstrap_resamples: int
    minimum_valid_resamples: int
    confidence_level: float
    percentile_rule: str
    minimum_report_cell_count: int
    minimum_stratum_entities: int
    maximum_categories: int
    minimum_level_entities: int
    conclusion_boundary: str = "screening_only_noncausal_noncompliance"


class ProxyRelease(StrictModel):
    evidence: tuple[ProxyMetric, ...]
    flag: ProxyScreeningFlag | None
    flag_state: str
    flag_reason_code: str | None
    trace: ProxyTrace


@dataclass(frozen=True)
class _Prepared:
    rows: tuple[ProxyEntity, ...]
    classes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _Scores:
    labels: tuple[int, ...]
    probabilities: tuple[tuple[float, ...], ...]
    entity_ids: tuple[str, ...]


def _typed_token(value: Any) -> tuple[str, str]:
    return type(value).__name__, repr(value)


def proxy_fold(protocol_version: str, entity_id: str, seed: int, fold_count: int) -> int:
    if fold_count < 2 or not 0 <= seed < 2**64:
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)
    protocol = protocol_version.encode()
    entity = entity_id.encode()
    if len(protocol) >= 2**32 or len(entity) >= 2**32:
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)
    payload = (
        b"fairlendkit-proxy-fold-v1"
        + pack(">I", len(protocol)) + protocol
        + pack(">Q", seed)
        + pack(">I", len(entity)) + entity
    )
    return int.from_bytes(hashlib.sha256(payload).digest(), "big") % fold_count


def reduce_entities(rows: Iterable[ProxyEntity]) -> tuple[ProxyEntity, ...]:
    by_id: dict[str, ProxyEntity] = {}
    for row in rows:
        previous = by_id.get(row.entity_id)
        if previous is not None and previous != row:
            reason = ProxyReason.WINDOW_CONFLICT if previous.window != row.window else ProxyReason.ENTITY_CONFLICT
            raise ProxyFailure(reason)
        by_id[row.entity_id] = row
    return tuple(by_id[key] for key in sorted(by_id, key=lambda value: value.encode()))


def eta_squared(values: Iterable[tuple[float, Any]]) -> float | None:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for value, group in values:
        if math.isfinite(value):
            groups[_typed_token(group)].append(value)
    if len(groups) < 2:
        return None
    flat = [value for key in sorted(groups) for value in groups[key]]
    mean = math.fsum(flat) / len(flat)
    total = math.fsum((value - mean) ** 2 for value in flat)
    if total == 0:
        return None
    between = math.fsum(
        len(bucket) * (math.fsum(bucket) / len(bucket) - mean) ** 2
        for bucket in groups.values()
    )
    return between / total


def cramers_v(pairs: Iterable[tuple[Any, Any]]) -> float | None:
    items = tuple((_typed_token(a), _typed_token(b)) for a, b in pairs)
    rows = sorted({a for a, _ in items})
    cols = sorted({b for _, b in items})
    if len(items) <= 1 or len(rows) < 2 or len(cols) < 2:
        return None
    table = Counter(items)
    row_n = Counter(a for a, _ in items)
    col_n = Counter(b for _, b in items)
    n = len(items)
    chi2 = math.fsum(
        (table[(row, col)] - row_n[row] * col_n[col] / n) ** 2
        / (row_n[row] * col_n[col] / n)
        for row in rows for col in cols
    )
    r, k = len(rows), len(cols)
    phi = max(0.0, chi2 / n - ((k - 1) * (r - 1)) / (n - 1))
    rc = r - ((r - 1) ** 2) / (n - 1)
    kc = k - ((k - 1) ** 2) / (n - 1)
    denominator = min(rc - 1, kc - 1)
    return math.sqrt(phi / denominator) if denominator > 0 else None


def auc(labels_scores: Iterable[tuple[bool, float]]) -> float | None:
    items = tuple(labels_scores)
    positive = [score for label, score in items if label]
    negative = [score for label, score in items if not label]
    if not positive or not negative:
        return None
    wins = math.fsum(
        1.0 if p > n else .5 if p == n else 0.0
        for p in positive for n in negative
    )
    return wins / (len(positive) * len(negative))


def _macro_auc(labels: Sequence[int], probabilities: Sequence[Sequence[float]], count: int) -> float | None:
    if count < 2 or not labels:
        return None
    values = []
    for target in range(count):
        value = auc((label == target, score[target]) for label, score in zip(labels, probabilities))
        if value is None:
            return None
        values.append(value)
    return math.fsum(values) / len(values)


def _cholesky_solve(matrix: list[list[float]], rhs: list[float]) -> list[float] | None:
    n = len(rhs)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = matrix[i][j] - math.fsum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if value <= 0 or not math.isfinite(value):
                    return None
                lower[i][j] = math.sqrt(value)
            else:
                lower[i][j] = value / lower[j][j]
    y = [0.0] * n
    for i in range(n):
        y[i] = (rhs[i] - math.fsum(lower[i][j] * y[j] for j in range(i))) / lower[i][i]
    out = [0.0] * n
    for i in range(n - 1, -1, -1):
        out[i] = (y[i] - math.fsum(lower[j][i] * out[j] for j in range(i + 1, n))) / lower[i][i]
    return out


def _probabilities(vector: Sequence[float], coefficients: Sequence[float], classes: int) -> tuple[float, ...]:
    width = len(vector)
    logits = [0.0]
    for target in range(classes - 1):
        offset = target * width
        logits.append(math.fsum(vector[j] * coefficients[offset + j] for j in range(width)))
    maximum = max(logits)
    exp = [math.exp(value - maximum) for value in logits]
    total = math.fsum(exp)
    return tuple(value / total for value in exp)


def _objective(matrix, labels, coefficients, classes):
    loss = 0.0
    for vector, label in zip(matrix, labels):
        probability = _probabilities(vector, coefficients, classes)[label]
        loss -= math.log(max(probability, 1e-300))
    width = len(matrix[0])
    penalty = math.fsum(
        coefficients[target * width + j] ** 2
        for target in range(classes - 1) for j in range(1, width)
    ) * .5
    return loss / len(matrix) + penalty


def _fit_logistic(matrix: Sequence[Sequence[float]], labels: Sequence[int], classes: int):
    if len(set(labels)) != classes or classes < 2:
        raise ProxyFailure(ProxyReason.INSUFFICIENT_FOLD_SUPPORT)
    width = len(matrix[0])
    size = width * (classes - 1)
    coefficients = [0.0] * size
    previous_change = math.inf
    for iteration in range(1, 101):
        gradient = [0.0] * size
        hessian = [[0.0] * size for _ in range(size)]
        for vector, label in zip(matrix, labels):
            probabilities = _probabilities(vector, coefficients, classes)
            for a in range(classes - 1):
                pa = probabilities[a + 1]
                for j in range(width):
                    gradient[a * width + j] += vector[j] * (pa - (label == a + 1))
                for b in range(classes - 1):
                    weight = pa * ((1.0 if a == b else 0.0) - probabilities[b + 1])
                    for j in range(width):
                        for k in range(width):
                            hessian[a * width + j][b * width + k] += vector[j] * vector[k] * weight
        n = len(matrix)
        for a in range(classes - 1):
            for j in range(width):
                index = a * width + j
                gradient[index] /= n
                for other in range(size):
                    hessian[index][other] /= n
                if j:
                    gradient[index] += coefficients[index]
                    hessian[index][index] += 1.0
        if max(abs(value) for value in gradient) <= 1e-10 and previous_change <= 1e-10:
            return tuple(coefficients), iteration
        step = _cholesky_solve(hessian, gradient)
        if step is None or any(not math.isfinite(value) for value in step):
            raise ProxyFailure(ProxyReason.MODEL_NONCONVERGENCE)
        current = _objective(matrix, labels, coefficients, classes)
        accepted = None
        scale = 1.0
        for _ in range(61):
            candidate = [value - scale * delta for value, delta in zip(coefficients, step)]
            if _objective(matrix, labels, candidate, classes) <= current + 1e-15:
                accepted = candidate
                break
            scale /= 2
        if accepted is None:
            raise ProxyFailure(ProxyReason.MODEL_NONCONVERGENCE)
        change = max(abs(a - b) for a, b in zip(accepted, coefficients))
        coefficients = accepted
        previous_change = change
        if max(abs(value) for value in gradient) <= 1e-10 and change <= 1e-10:
            return tuple(coefficients), iteration
    raise ProxyFailure(ProxyReason.MODEL_NONCONVERGENCE)


@dataclass(frozen=True)
class _Encoder:
    numeric: tuple[tuple[float, float, float], ...]
    categorical: tuple[
        tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]], ...
    ]
    kinds: tuple[CandidateKind, ...]

    def transform(self, values: Sequence[Any]) -> tuple[float, ...]:
        output = [1.0]
        numeric_index = categorical_index = 0
        for kind, value in zip(self.kinds, values):
            if kind == CandidateKind.NUMERIC:
                median, mean, std = self.numeric[numeric_index]
                numeric_index += 1
                missing = not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value))
                number = median if missing else float(value)
                output.extend((0.0 if std == 0 else (number - mean) / std, float(missing)))
            else:
                vocabulary, rare_sources = self.categorical[categorical_index]
                categorical_index += 1
                token = _typed_token(_CategoryLevel.MISSING) if value is None else _typed_token(value)
                if token in rare_sources:
                    token = _typed_token(_CategoryLevel.RARE)
                elif token not in vocabulary:
                    token = _typed_token(_CategoryLevel.UNSEEN)
                output.extend(float(token == item) for item in vocabulary)
        return tuple(output)


def _fit_encoder(rows: Sequence[ProxyEntity], kinds: tuple[CandidateKind, ...], getter, config: ProxyConfig):
    numeric = []
    categorical = []
    columns = list(zip(*(getter(row) for row in rows)))
    for kind, values in zip(kinds, columns):
        if kind == CandidateKind.NUMERIC:
            finite = sorted(float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)))
            if not finite:
                raise ProxyFailure(ProxyReason.STATISTIC_UNDEFINED)
            middle = len(finite) // 2
            median = finite[middle] if len(finite) % 2 else math.fsum(finite[middle-1:middle+1]) / 2
            imputed = [median if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) else float(value) for value in values]
            mean = math.fsum(imputed) / len(imputed)
            variance = math.fsum((value - mean) ** 2 for value in imputed) / len(imputed)
            numeric.append((median, mean, math.sqrt(max(0.0, variance))))
        else:
            counts = Counter(
                _typed_token(_CategoryLevel.MISSING) if value is None else _typed_token(value)
                for value in values
            )
            retained = sorted(token for token, count in counts.items() if count >= config.minimum_level_entities)
            rare_sources = tuple(sorted(token for token, count in counts.items() if count < config.minimum_level_entities))
            if rare_sources:
                retained.append(_typed_token(_CategoryLevel.RARE))
            retained.append(_typed_token(_CategoryLevel.MISSING))
            retained.append(_typed_token(_CategoryLevel.UNSEEN))
            retained = sorted(set(retained))
            if len(retained) > config.maximum_categories:
                raise ProxyFailure(ProxyReason.HIGH_CARDINALITY)
            categorical.append((tuple(retained), rare_sources))
    return _Encoder(tuple(numeric), tuple(categorical), kinds)


def _encoded(rows, kinds, getter, config):
    encoder = _fit_encoder(rows, kinds, getter, config)
    matrix = tuple(encoder.transform(getter(row)) for row in rows)
    return encoder, matrix


def _diagnostic_scores(rows: tuple[ProxyEntity, ...], config: ProxyConfig, include_candidate: bool, include_baseline: bool):
    rows = tuple(sorted(rows, key=lambda row: row.entity_id.encode()))
    classes = tuple(sorted({_typed_token(row.protected) for row in rows if row.protected is not None}))
    class_index = {value: index for index, value in enumerate(classes)}
    development = tuple(row for row in rows if row.window == ProxyWindow.DEVELOPMENT)
    holdout = tuple(row for row in rows if row.window == ProxyWindow.HOLDOUT)
    kinds = (() if not include_baseline else config.baseline_kinds) + (() if not include_candidate else (config.candidate_kind,))
    getter = lambda row: (() if not include_baseline else row.baseline) + (() if not include_candidate else (row.candidate,))
    if not kinds:  # intercept-only null baseline
        getter = lambda row: ()
    dev_scores: dict[str, tuple[float, ...]] = {}
    valid_folds = 0
    for fold in range(config.fold_count):
        validation = tuple(row for row in development if proxy_fold(config.protocol_version, row.entity_id, config.fold_seed, config.fold_count) == fold)
        training = tuple(row for row in development if row not in validation)
        if not validation or not training:
            continue
        if any(sum(_typed_token(row.protected) == cls for row in validation) < config.per_fold_class_minimum for cls in classes):
            continue
        try:
            if kinds:
                encoder, matrix = _encoded(training, kinds, getter, config)
                validation_matrix = tuple(encoder.transform(getter(row)) for row in validation)
            else:
                matrix = tuple((1.0,) for _ in training)
                validation_matrix = tuple((1.0,) for _ in validation)
            labels = tuple(class_index[_typed_token(row.protected)] for row in training)
            coefficients, _ = _fit_logistic(matrix, labels, len(classes))
        except ProxyFailure:
            continue
        for row, vector in zip(validation, validation_matrix):
            dev_scores[row.entity_id] = _probabilities(vector, coefficients, len(classes))
        valid_folds += 1
    if valid_folds < config.minimum_valid_folds or len(dev_scores) != len(development):
        raise ProxyFailure(ProxyReason.INSUFFICIENT_FOLD_SUPPORT)
    ordered_dev = tuple(row for row in development if row.entity_id in dev_scores)
    if kinds:
        encoder, matrix = _encoded(development, kinds, getter, config)
        holdout_matrix = tuple(encoder.transform(getter(row)) for row in holdout)
    else:
        matrix = tuple((1.0,) for _ in development)
        holdout_matrix = tuple((1.0,) for _ in holdout)
    labels = tuple(class_index[_typed_token(row.protected)] for row in development)
    coefficients, iterations = _fit_logistic(matrix, labels, len(classes))
    holdout_scores = tuple(_probabilities(vector, coefficients, len(classes)) for vector in holdout_matrix)
    return (
        _Scores(tuple(class_index[_typed_token(row.protected)] for row in ordered_dev), tuple(dev_scores[row.entity_id] for row in ordered_dev), tuple(row.entity_id for row in ordered_dev)),
        _Scores(tuple(class_index[_typed_token(row.protected)] for row in holdout), holdout_scores, tuple(row.entity_id for row in holdout)),
        iterations,
    )


def _stratified_draws(labels, config, metric_key):
    groups = {label: tuple(index for index, value in enumerate(labels) if value == label) for label in sorted(set(labels))}
    output = []
    for resample in range(config.bootstrap_resamples):
        draw = []
        for label, indices in groups.items():
            raw = bootstrap_index_draws(len(indices), config.bootstrap_resamples, seed=config.bootstrap_seed, metric_key=f"{metric_key}|class={label}", stream_role="scope")[resample]
            draw.extend(indices[index] for index in raw)
        output.append(tuple(draw))
    return tuple(output)


def _evidence(key, rows, evaluator, config, *, missing=0, excluded=0):
    point = evaluator(tuple(range(len(rows))))
    if point is None:
        return ProxyMetric(evidence_key=key, state="unavailable", reason_code=ProxyReason.STATISTIC_UNDEFINED.value)
    labels = tuple(_typed_token(row.protected) for row in rows)
    class_ids = {label: f"class_{index:03d}" for index, label in enumerate(sorted(set(labels)))}
    samples = tuple(value for draw in _stratified_draws(labels, config, json.dumps(key.model_dump(mode="json"), sort_keys=True)) if (value := evaluator(draw)) is not None)
    reliable = len(samples) >= config.minimum_valid_resamples
    alpha = (1 - config.confidence_level) / 2
    return ProxyMetric(
        evidence_key=key, state="published", eligible_count=len(rows),
        excluded_count=excluded or None, missing_count=missing or None, denominator=len(rows),
        class_support={class_ids[label]: labels.count(label) for label in sorted(set(labels))},
        point=point,
        lower=type7_quantile(samples, alpha) if reliable else None,
        upper=type7_quantile(samples, 1-alpha) if reliable else None,
        valid_resamples=len(samples), invalid_resamples=config.bootstrap_resamples-len(samples),
        reliable=reliable,
        reason_code=None if reliable else ProxyReason.INSUFFICIENT_RESAMPLES.value,
    )


def _key(window, metric, dimension="overall", stratum="overall", aggregation="overall", baseline="candidate"):
    return ProxyEvidenceKey(window=window, metric=metric, class_aggregation=aggregation, baseline_scope=baseline, stratum_dimension=dimension, stratum_id=stratum)


def _association(rows, config, window, dimension="overall", stratum="overall"):
    selected = tuple(row for row in rows if row.window == window and row.protected is not None and (dimension == "overall" or getattr(row, f"{dimension}_stratum") == stratum))
    metric = "eta_squared" if config.candidate_kind == CandidateKind.NUMERIC else "cramers_v"
    if dimension != "overall" and len(selected) < config.minimum_stratum_entities:
        return ProxyMetric(evidence_key=_key(window, metric, dimension, stratum), state="unavailable", reason_code=ProxyReason.STRATUM_SUPPORT.value)
    if config.candidate_kind == CandidateKind.NUMERIC:
        observed = tuple(row for row in selected if isinstance(row.candidate, (int, float)) and not isinstance(row.candidate, bool) and math.isfinite(float(row.candidate)))
        pairs = tuple((float(row.candidate), row.protected) for row in observed)
        key = _key(window, "eta_squared", dimension, stratum)
        return _evidence(key, observed, lambda draw: eta_squared(pairs[i] for i in draw), config, missing=len(selected)-len(observed))
    pairs = tuple((_CategoryLevel.MISSING if row.candidate is None else row.candidate, row.protected) for row in selected)
    key = _key(window, "cramers_v", dimension, stratum)
    return _evidence(key, selected, lambda draw: cramers_v(pairs[i] for i in draw), config)


def _missingness(rows, config, window):
    selected = tuple(row for row in rows if row.window == window and row.protected is not None)
    pairs = tuple((_CategoryLevel.MISSING if row.candidate is None else "present", row.protected) for row in selected)
    return _evidence(_key(window, "missingness_cramers_v"), selected, lambda draw: cramers_v(pairs[i] for i in draw), config, missing=sum(row.candidate is None for row in selected))


def _auc_evidence(rows, scores, config, window, metric, dimension="overall", stratum="overall", baseline="candidate"):
    by_id = {row.entity_id: row for row in rows}
    indices = tuple(index for index, entity_id in enumerate(scores.entity_ids) if dimension == "overall" or getattr(by_id[entity_id], f"{dimension}_stratum") == stratum)
    selected_rows = tuple(by_id[scores.entity_ids[index]] for index in indices)
    if dimension != "overall" and len(indices) < config.minimum_stratum_entities:
        return ProxyMetric(evidence_key=_key(window, metric, dimension, stratum, "macro_ovr", baseline), state="unavailable", reason_code=ProxyReason.STRATUM_SUPPORT.value)
    labels = tuple(scores.labels[index] for index in indices)
    probabilities = tuple(scores.probabilities[index] for index in indices)
    classes = len(probabilities[0]) if probabilities else 0
    key = _key(window, metric, dimension, stratum, "binary" if classes == 2 else "macro_ovr", baseline)
    return _evidence(
        key, selected_rows,
        lambda draw: _macro_auc(tuple(labels[i] for i in draw), tuple(probabilities[i] for i in draw), classes),
        config,
        missing=sum(row.candidate is None for row in selected_rows),
    )


def _increment_evidence(rows, baseline, augmented, config, window, dimension="overall", stratum="overall"):
    if baseline.entity_ids != augmented.entity_ids or baseline.labels != augmented.labels:
        raise ProxyFailure(ProxyReason.PAIRED_POPULATION_MISMATCH)
    by_id = {row.entity_id: row for row in rows}
    indices = tuple(index for index, entity_id in enumerate(baseline.entity_ids) if dimension == "overall" or getattr(by_id[entity_id], f"{dimension}_stratum") == stratum)
    selected = tuple(by_id[baseline.entity_ids[index]] for index in indices)
    if dimension != "overall" and len(indices) < config.minimum_stratum_entities:
        return ProxyMetric(evidence_key=_key(window, "incremental_auc", dimension, stratum, "macro_ovr", "incremental"), state="unavailable", reason_code=ProxyReason.STRATUM_SUPPORT.value)
    labels = tuple(baseline.labels[i] for i in indices)
    before = tuple(baseline.probabilities[i] for i in indices)
    after = tuple(augmented.probabilities[i] for i in indices)
    classes = len(before[0]) if before else 0
    def evaluate(draw):
        left = _macro_auc(tuple(labels[i] for i in draw), tuple(before[i] for i in draw), classes)
        right = _macro_auc(tuple(labels[i] for i in draw), tuple(after[i] for i in draw), classes)
        return None if left is None or right is None else right-left
    return _evidence(
        _key(window, "incremental_auc", dimension, stratum, "binary" if classes == 2 else "macro_ovr", "incremental"),
        selected, evaluate, config,
        missing=sum(row.candidate is None for row in selected),
    )


def _metric_identity(item):
    key = item.evidence_key
    return f"proxy.{key.window}.{key.metric}.{key.class_aggregation}.{key.baseline_scope}.{key.stratum_dimension}", key.stratum_id


def _apply_release_suppression(evidence, rows, config, previous_release):
    cell_map: dict[tuple[str, str], _CountCell] = {}
    linked: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    direct_hidden: dict[tuple[str, str], str] = {}
    for item in evidence:
        if item.state != "published":
            continue
        direct_counts = [item.eligible_count, item.excluded_count, item.missing_count]
        if item.class_support:
            direct_counts.extend(item.class_support.values())
        if any(count is not None and count < config.minimum_report_cell_count for count in direct_counts):
            direct_hidden[_metric_identity(item)] = ProxyReason.SPARSE.value
            continue
        key = item.evidence_key
        scoped_rows = tuple(
            row for row in rows
            if row.window == key.window
            and (key.stratum_dimension == "overall" or getattr(row, f"{key.stratum_dimension}_stratum") == key.stratum_id)
        )
        metric_rows = tuple(row for row in scoped_rows if row.protected is not None)
        if key.metric == "eta_squared":
            metric_rows = tuple(
                row for row in metric_rows
                if isinstance(row.candidate, (int, float))
                and not isinstance(row.candidate, bool)
                and math.isfinite(float(row.candidate))
            )
        members = frozenset(row.entity_id for row in metric_rows)
        table, cell = _metric_identity(item)
        cell_map[(table, cell)] = _CountCell(table, cell, members, key.stratum_dimension == "overall")
        linked[(table, cell)].append((table, cell))
        units = {
            "eligible": members,
            "missing": frozenset(
                row.entity_id for row in scoped_rows
                if row.protected is not None and row.candidate is None
            ),
            "bootstrap": members,
            "flag_candidate": members,
            "excluded_protected_missing": frozenset(
                row.entity_id for row in scoped_rows if row.protected is None
            ),
            "candidate_observed": frozenset(
                row.entity_id for row in scoped_rows
                if row.protected is not None and row.candidate is not None
            ),
        }
        protected = sorted({_typed_token(row.protected) for row in metric_rows})
        for index, label in enumerate(protected):
            units[f"class_{index:03d}"] = frozenset(
                row.entity_id for row in rows
                if row.entity_id in members and _typed_token(row.protected) == label
            )
        if config.candidate_kind == CandidateKind.CATEGORICAL:
            margins = sorted({
                _typed_token(_CategoryLevel.MISSING) if row.candidate is None else _typed_token(row.candidate)
                for row in scoped_rows if row.protected is not None
            })
            for index, label in enumerate(margins):
                units[f"candidate_margin_{index:03d}"] = frozenset(
                    row.entity_id for row in scoped_rows
                    if row.protected is not None
                    and (
                        _typed_token(_CategoryLevel.MISSING)
                        if row.candidate is None else _typed_token(row.candidate)
                    ) == label
                )
        if key.stratum_dimension == "overall":
            for fold in range(config.fold_count):
                fold_rows = tuple(
                    row for row in scoped_rows
                    if row.protected is not None
                    and proxy_fold(config.protocol_version, row.entity_id, config.fold_seed, config.fold_count) == fold
                )
                units[f"fold_{fold:03d}"] = frozenset(row.entity_id for row in fold_rows)
                for index, label in enumerate(protected):
                    units[f"fold_{fold:03d}_class_{index:03d}"] = frozenset(
                        row.entity_id for row in fold_rows if _typed_token(row.protected) == label
                    )
        for suffix, unit_members in units.items():
            if not unit_members:
                continue
            if len(unit_members) < config.minimum_report_cell_count:
                direct_hidden[(table, cell)] = ProxyReason.SPARSE.value
                continue
            identity = (
                f"proxy.support.{key.window}.{key.metric}.{key.baseline_scope}.{key.stratum_dimension}",
                f"{key.stratum_id}.{suffix}",
            )
            cell_map.setdefault(identity, _CountCell(identity[0], identity[1], unit_members))
            linked[(table, cell)].append(identity)
    cells = tuple(cell_map.values())
    locked = set()
    if previous_release is not None:
        current = {(cell.table_id, cell.cell_id): len(cell.entities) for cell in cells}
        for old in previous_release.evidence:
            if old.state == "published" and old.denominator is not None:
                identity = _metric_identity(old)
                if identity in current and current[identity] != old.denominator:
                    raise ValueError("current proxy cell conflicts with historical exact value")
                if identity in current:
                    locked.add(identity)
                key = old.evidence_key
                support_table = f"proxy.support.{key.window}.{key.metric}.{key.baseline_scope}.{key.stratum_dimension}"
                exact_units: dict[str, int | None] = {
                    "eligible": old.eligible_count,
                    "excluded_protected_missing": old.excluded_count,
                    "missing": old.missing_count,
                    "candidate_observed": (
                        None if old.eligible_count is None
                        else (
                            old.eligible_count
                            if key.metric == "eta_squared"
                            else old.eligible_count - (old.missing_count or 0)
                        )
                    ),
                    "bootstrap": old.eligible_count,
                    "flag_candidate": old.eligible_count,
                }
                for class_id, count in (old.class_support or {}).items():
                    exact_units[class_id] = count
                for suffix, count in exact_units.items():
                    unit_identity = (support_table, f"{key.stratum_id}.{suffix}")
                    if count is None or unit_identity not in current:
                        continue
                    if current[unit_identity] != count:
                        raise ValueError(
                            "current proxy support conflicts with historical exact value"
                        )
                    locked.add(unit_identity)
    release = _apply_suppression(cells, config.minimum_report_cell_count, frozenset(locked))
    states = {(cell.table_id, cell.cell_id): cell for cell in release.cells}
    output = []
    for item in evidence:
        if item.state != "published":
            output.append(item)
            continue
        if _metric_identity(item) in direct_hidden:
            output.append(ProxyMetric(
                evidence_key=item.evidence_key,
                state="suppressed",
                count_bucket=f"0..{config.minimum_report_cell_count - 1}",
                reason_code=direct_hidden[_metric_identity(item)],
            ))
            continue
        related = [states[identity] for identity in linked[_metric_identity(item)]]
        hidden = next((state for state in related if state.state.value == "suppressed"), None)
        if hidden is not None:
            output.append(ProxyMetric(evidence_key=item.evidence_key, state="suppressed", count_bucket=hidden.count_bucket, reason_code=hidden.reason_code))
        else:
            output.append(item)
    return tuple(output)


def _reference(item):
    return item.evidence_key


def _find(evidence, window, metric, dimension="overall", stratum="overall", baseline="candidate"):
    return next(item for item in evidence if item.evidence_key.window == window and item.evidence_key.metric == metric and item.evidence_key.stratum_dimension == dimension and item.evidence_key.stratum_id == stratum and item.evidence_key.baseline_scope == baseline)


def _trace(config):
    fingerprint = lambda value: hashlib.sha256(str(value).encode()).hexdigest()[:16]
    return ProxyTrace(
        protocol_version=config.protocol_version, population_id=config.population_id,
        candidate_id=config.candidate_id, protected_attribute_id=config.protected_attribute_id,
        baseline_id=config.baseline_id,
        candidate_source_id=config.candidate_source_id,
        candidate_derivation_version=config.candidate_derivation_version,
        reducer_id=config.reducer_id, reducer_version=config.reducer_version,
        candidate_kind=config.candidate_kind,
        baseline_kinds=config.baseline_kinds,
        association_threshold=config.association_threshold,
        predictability_auc_threshold=config.predictability_auc_threshold,
        incremental_auc_threshold=config.incremental_auc_threshold,
        stability_tolerance=config.stability_tolerance,
        provider_strata=config.provider_strata,
        coverage_strata=config.coverage_strata,
        weighting="unweighted",
        development_window=config.development_window, holdout_window=config.holdout_window,
        fold_seed_fingerprint=fingerprint(config.fold_seed), fold_count=config.fold_count,
        minimum_valid_folds=config.minimum_valid_folds, per_fold_class_minimum=config.per_fold_class_minimum,
        optimizer="full-batch-l2-logistic-newton-v1", optimizer_tolerance=1e-10,
        optimizer_max_iterations=100, optimizer_max_halvings=60,
        rng_identity=RNG_NAME, bootstrap_seed_fingerprint=fingerprint(config.bootstrap_seed),
        bootstrap_resamples=config.bootstrap_resamples,
        minimum_valid_resamples=config.minimum_valid_resamples,
        confidence_level=config.confidence_level, percentile_rule="Hyndman-Fan-Type-7",
        minimum_report_cell_count=config.minimum_report_cell_count,
        minimum_stratum_entities=config.minimum_stratum_entities,
        maximum_categories=config.maximum_categories,
        minimum_level_entities=config.minimum_level_entities,
    )


def build_proxy_release(rows: Iterable[ProxyEntity], config: ProxyConfig, previous_release: ProxyRelease | None = None) -> ProxyRelease:
    entities = reduce_entities(rows)
    current_trace = _trace(config)
    if previous_release is not None and previous_release.trace != current_trace:
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)
    if any(row.weight not in (None, 1.0) for row in entities):
        raise ProxyFailure(ProxyReason.WEIGHTING_UNSUPPORTED)
    if any(
        not row.population_eligible
        or row.candidate_source_id != config.candidate_source_id
        or row.candidate_derivation_version != config.candidate_derivation_version
        or row.reducer_id != config.reducer_id
        or row.reducer_version != config.reducer_version
        for row in entities
    ):
        raise ProxyFailure(ProxyReason.ENTITY_CONFLICT)
    if any(
        value.tzinfo is None or value.utcoffset() is None
        for row in entities
        for value in (
            row.as_of_time, row.candidate_available_time,
            row.protected_observation_time,
            *( () if row.baseline_available_time is None else (row.baseline_available_time,) ),
        )
    ):
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)
    if any(
        row.candidate_available_time > row.as_of_time
        or row.protected_observation_time > row.as_of_time
        or (
            config.baseline_id is not None
            and (
                row.baseline_available_time is None
                or row.baseline_available_time > row.as_of_time
            )
        )
        for row in entities
    ):
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)
    if any(row.protected is None for row in entities):
        # Missing protected rows are excluded from metrics but made explicit by evidence counts.
        pass
    known = tuple(row for row in entities if row.protected is not None)
    if not known:
        raise ProxyFailure(ProxyReason.PROTECTED_MISSING)
    if {row.provider_stratum for row in known} - set(config.provider_strata) or {row.coverage_stratum for row in known} - set(config.coverage_strata):
        raise ProxyFailure(ProxyReason.ENTITY_CONFLICT)
    if any(len(row.baseline) != len(config.baseline_kinds) for row in known):
        raise ProxyFailure(ProxyReason.PAIRED_POPULATION_MISMATCH)
    if {row.entity_id for row in known if row.window == ProxyWindow.DEVELOPMENT} & {row.entity_id for row in known if row.window == ProxyWindow.HOLDOUT}:
        raise ProxyFailure(ProxyReason.ISOLATION_FAILURE)

    candidate_dev, candidate_hold, _ = _diagnostic_scores(known, config, True, False)
    null_dev, null_hold, _ = _diagnostic_scores(known, config, False, False)
    evidence = [_association(known, config, window) for window in ProxyWindow]
    evidence.extend(_missingness(known, config, window) for window in ProxyWindow)
    evidence.extend((
        _auc_evidence(known, null_dev, config, ProxyWindow.DEVELOPMENT, "null_auc", baseline="null"),
        _auc_evidence(known, null_hold, config, ProxyWindow.HOLDOUT, "null_auc", baseline="null"),
        _auc_evidence(known, candidate_dev, config, ProxyWindow.DEVELOPMENT, "predictability_auc"),
        _auc_evidence(known, candidate_hold, config, ProxyWindow.HOLDOUT, "predictability_auc"),
    ))
    baseline_scores = augmented_scores = None
    if config.baseline_id is not None:
        base_dev, base_hold, _ = _diagnostic_scores(known, config, False, True)
        aug_dev, aug_hold, _ = _diagnostic_scores(known, config, True, True)
        baseline_scores = {ProxyWindow.DEVELOPMENT: base_dev, ProxyWindow.HOLDOUT: base_hold}
        augmented_scores = {ProxyWindow.DEVELOPMENT: aug_dev, ProxyWindow.HOLDOUT: aug_hold}
        for window in ProxyWindow:
            evidence.append(_increment_evidence(known, baseline_scores[window], augmented_scores[window], config, window))

    association_metric = "eta_squared" if config.candidate_kind == CandidateKind.NUMERIC else "cramers_v"
    for window in ProxyWindow:
        for dimension, strata in (("provider", config.provider_strata), ("coverage", config.coverage_strata)):
            for stratum in strata:
                evidence.append(_association(known, config, window, dimension, stratum))
                scores = candidate_dev if window == ProxyWindow.DEVELOPMENT else candidate_hold
                evidence.append(_auc_evidence(known, scores, config, window, "predictability_auc", dimension, stratum))
                if baseline_scores is not None:
                    evidence.append(_increment_evidence(known, baseline_scores[window], augmented_scores[window], config, window, dimension, stratum))

    with_exclusions = []
    for item in evidence:
        key = item.evidence_key
        excluded = sum(
            row.window == key.window
            and row.protected is None
            and (
                key.stratum_dimension == "overall"
                or getattr(row, f"{key.stratum_dimension}_stratum") == key.stratum_id
            )
            for row in entities
        )
        with_exclusions.append(
            item.model_copy(update={"excluded_count": excluded or None})
            if item.state == "published" else item
        )
    evidence = _apply_release_suppression(tuple(with_exclusions), entities, config, previous_release)
    flag = None
    reason = None
    candidates = (
        (association_metric, config.association_threshold, "candidate"),
        ("predictability_auc", config.predictability_auc_threshold, "candidate"),
    ) + ((("incremental_auc", config.incremental_auc_threshold, "incremental"),) if config.baseline_id is not None else ())
    chosen = None
    for metric, threshold, baseline_scope in candidates:
        development = _find(evidence, ProxyWindow.DEVELOPMENT, metric, baseline=baseline_scope)
        holdout = _find(evidence, ProxyWindow.HOLDOUT, metric, baseline=baseline_scope)
        if not all(item.state == "published" and item.reliable for item in (development, holdout)):
            continue
        if development.point >= threshold and development.lower >= threshold and holdout.point >= threshold and holdout.lower >= threshold:
            chosen = metric, threshold, baseline_scope, development, holdout
            break
    if chosen is None:
        reason = ProxyReason.THRESHOLD_NOT_MET.value
    else:
        metric, threshold, baseline_scope, development, holdout = chosen
        temporal_difference = abs(holdout.point-development.point)
        if temporal_difference > config.stability_tolerance:
            reason = ProxyReason.HOLDOUT_UNSTABLE.value
        references = {"provider": [], "coverage": []}
        if reason is None:
            for dimension, strata in (("provider", config.provider_strata), ("coverage", config.coverage_strata)):
                published = 0
                for stratum in strata:
                    stratum_support = sum(
                        row.window == ProxyWindow.DEVELOPMENT
                        and getattr(row, f"{dimension}_stratum") == stratum
                        for row in known
                    )
                    holdout_support = sum(
                        row.window == ProxyWindow.HOLDOUT
                        and getattr(row, f"{dimension}_stratum") == stratum
                        for row in known
                    )
                    if stratum_support == 0 and holdout_support == 0:
                        continue
                    d = _find(evidence, ProxyWindow.DEVELOPMENT, metric, dimension, stratum, baseline_scope)
                    h = _find(evidence, ProxyWindow.HOLDOUT, metric, dimension, stratum, baseline_scope)
                    if d.state != "published" or h.state != "published" or not d.reliable or not h.reliable:
                        reason = ProxyReason.STRATUM_SUPPORT.value
                        break
                    published += 1
                    dd = abs(d.point-development.point)
                    hd = abs(h.point-holdout.point)
                    references[dimension].append(ProxyStabilityReference(
                        dimension=dimension, stratum_id=stratum,
                        development_stratum=_reference(d), development_overall=_reference(development),
                        holdout_stratum=_reference(h), holdout_overall=_reference(holdout),
                        development_difference=dd, holdout_difference=hd,
                        tolerance=config.stability_tolerance,
                        passed=dd <= config.stability_tolerance and hd <= config.stability_tolerance,
                    ))
                if published < 2:
                    reason = ProxyReason.STRATA_NOT_COMPARABLE.value
                if reason is not None:
                    break
                if not all(item.passed for item in references[dimension]):
                    reason = ProxyReason.STRATUM_UNSTABLE.value
                    break
        if reason is None:
            flag_id = hashlib.sha256(f"{config.protocol_version}|{config.population_id}|{config.candidate_id}|{metric}".encode()).hexdigest()[:20]
            flag = ProxyScreeningFlag(
                flag_id=flag_id, candidate_id=config.candidate_id,
                protected_attribute_id=config.protected_attribute_id,
                metric=metric, class_aggregation=development.evidence_key.class_aggregation,
                baseline_id=config.baseline_id if baseline_scope == "incremental" else None,
                threshold=threshold, stability_tolerance=config.stability_tolerance,
                threshold_evidence=ProxyThresholdEvidence(development=_reference(development), holdout=_reference(holdout)),
                temporal=ProxyTemporalReference(development=_reference(development), holdout=_reference(holdout), difference=temporal_difference, tolerance=config.stability_tolerance, passed=True),
                provider=tuple(references["provider"]),
                coverage_stratum=tuple(references["coverage"]),
                population_contract=config.population_id,
                fold_contract="fairlendkit-proxy-fold-v1",
                bootstrap_contract=RNG_NAME,
            )

    # No flag may survive a hidden/unavailable referenced unit.
    if flag is not None:
        published_keys = {json.dumps(item.evidence_key.model_dump(mode="json"), sort_keys=True) for item in evidence if item.state == "published" and item.reliable}
        refs = [flag.threshold_evidence.development, flag.threshold_evidence.holdout, flag.temporal.development, flag.temporal.holdout]
        for item in flag.provider + flag.coverage_stratum:
            refs.extend((item.development_stratum, item.development_overall, item.holdout_stratum, item.holdout_overall))
        if any(json.dumps(ref.model_dump(mode="json"), sort_keys=True) not in published_keys for ref in refs):
            flag = None
            reason = ProxyReason.COMPLEMENTARY.value
    return ProxyRelease(evidence=evidence, flag=flag, flag_state="published" if flag else "unavailable", flag_reason_code=reason, trace=current_trace)


def _normalized_rows(release: ProxyRelease) -> tuple[dict[str, Any], ...]:
    rows = []
    for item in release.evidence:
        row = {"row_type": "proxy_evidence", **item.evidence_key.model_dump(mode="json"), **item.model_dump(mode="json", exclude={"evidence_key"})}
        rows.append(row)
    if release.flag is not None:
        scalar = release.flag.model_dump(mode="json", exclude={"threshold_evidence", "temporal", "provider", "coverage_stratum"})
        rows.append({"row_type": "proxy_flag", **scalar})
        references = [
            ("threshold", "development", release.flag.threshold_evidence.development),
            ("threshold", "holdout", release.flag.threshold_evidence.holdout),
            ("temporal", "development", release.flag.temporal.development),
            ("temporal", "holdout", release.flag.temporal.holdout),
        ]
        for dimension, collection in (("provider", release.flag.provider), ("coverage", release.flag.coverage_stratum)):
            for item in collection:
                references.extend((
                    (dimension, f"{item.stratum_id}:development", item.development_stratum),
                    (dimension, f"{item.stratum_id}:development_overall", item.development_overall),
                    (dimension, f"{item.stratum_id}:holdout", item.holdout_stratum),
                    (dimension, f"{item.stratum_id}:holdout_overall", item.holdout_overall),
                ))
        for dimension, role, key in references:
            rows.append({"row_type": "proxy_flag_evidence", "flag_id": release.flag.flag_id, "dimension": dimension, "role": role, "evidence_key": json.dumps(key.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))})
    return tuple(rows)


def render_proxy_csv(release: ProxyRelease) -> str:
    rows = _normalized_rows(release)
    fields = sorted({key for row in rows for key in row})
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    return output.getvalue()


def render_proxy_json(release: ProxyRelease) -> str:
    """Canonical normalized JSON shared by CSV and HTML renderers."""
    return json.dumps(_normalized_rows(release), sort_keys=True, separators=(",", ":"))


def render_proxy_html(release: ProxyRelease) -> str:
    payload = render_proxy_json(release)
    return f'<section data-report="proxy-screening"><pre>{escape(payload)}</pre></section>'
