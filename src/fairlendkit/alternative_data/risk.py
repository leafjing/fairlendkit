"""Deterministic AD-3 credit-risk diagnostics on one entity-level population."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
import math
from typing import Any

from pydantic import Field, field_validator, model_validator

from fairlendkit.alternative_data.contracts import StrictModel
from fairlendkit.alternative_data.suppression import _CountCell, _apply_suppression
from fairlendkit.metrics.bootstrap import bootstrap_index_draws


class ScoreType(StrEnum):
    PROBABILITY = "probability"
    RANKING = "ranking"


class ScoreTarget(StrEnum):
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"


class MetricState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class RiskEvaluationConfig(StrictModel):
    outcome_definition: str = Field(default="explicit observed credit outcome", min_length=1)
    favorable_outcome_labels: tuple[Any, ...] = Field(min_length=1)
    unfavorable_outcome_labels: tuple[Any, ...] = Field(min_length=1)
    score_type: ScoreType
    score_target: ScoreTarget
    score_band_edges: tuple[float, ...]
    top_fractions: tuple[float, ...] = Field(min_length=1)
    calibration_epsilon: float = Field(gt=0, lt=0.5)
    minimum_total_entities: int = Field(default=1, ge=1)
    minimum_bad_entities: int = Field(default=1, ge=1)
    minimum_good_entities: int = Field(default=1, ge=1)
    bootstrap_seed: int = Field(default=0, ge=0, le=2**64 - 1)
    bootstrap_resamples: int = Field(default=100, ge=1)
    minimum_valid_resamples: int = Field(default=50, ge=1)
    minimum_report_cell_count: int = Field(default=10, ge=10)

    @model_validator(mode="after")
    def validate_contract(self) -> "RiskEvaluationConfig":
        labels = self.favorable_outcome_labels + self.unfavorable_outcome_labels
        typed = [(type(value), value) for value in labels]
        if any(type(value) not in (bool, int, str) for value in labels):
            raise ValueError("outcome labels must be bool, int, or str")
        if len(set(typed)) != len(typed):
            raise ValueError("outcome labels must be type-sensitively unique and disjoint")
        if any(not math.isfinite(value) for value in self.score_band_edges):
            raise ValueError("score band edges must be finite")
        if any(a >= b for a, b in zip(self.score_band_edges, self.score_band_edges[1:])):
            raise ValueError("score band edges must be strictly increasing")
        if any(not math.isfinite(value) or not 0 < value <= 1 for value in self.top_fractions):
            raise ValueError("top fractions must be finite and in (0, 1]")
        if any(a >= b for a, b in zip(self.top_fractions, self.top_fractions[1:])):
            raise ValueError("top fractions must be strictly increasing")
        if self.minimum_valid_resamples > self.bootstrap_resamples:
            raise ValueError("minimum valid resamples cannot exceed bootstrap resamples")
        return self


class RiskEntity(StrictModel):
    entity_id: str = Field(min_length=1)
    score: float
    outcome: Any
    weight: float = 1.0
    label_mature: bool = True
    censored: bool = False

    @field_validator("score", "weight")
    @classmethod
    def finite_numbers(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("numeric inputs must be finite")
        return value

    @field_validator("weight")
    @classmethod
    def nonnegative_weight(cls, value: float) -> float:
        if value < 0:
            raise ValueError("weight must be non-negative")
        return value


class MetricValue(StrictModel):
    state: MetricState
    value: float | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "MetricValue":
        if (self.state == MetricState.AVAILABLE) != (self.value is not None):
            raise ValueError("available metrics require a value and other states forbid one")
        if self.state != MetricState.AVAILABLE and self.reason is None:
            raise ValueError("undefined metrics require a reason")
        return self


class RiskBand(StrictModel):
    lower: float | None
    upper: float | None
    entity_count: int
    normalized_weight: float
    bad_count: int
    bad_weight: float
    good_count: int
    good_weight: float
    observed_bad_rate: MetricValue
    score_minimum: float | None
    score_maximum: float | None


class ReleasedRiskBand(StrictModel):
    state: str
    lower: float | None
    upper: float | None
    minimum_report_cell_count: int = Field(ge=10)
    entity_count: int | None = None
    normalized_weight: float | None = None
    bad_count: int | None = None
    bad_weight: float | None = None
    good_count: int | None = None
    good_weight: float | None = None
    observed_bad_rate: MetricValue | None = None
    score_minimum: float | None = None
    score_maximum: float | None = None
    count_bucket: str | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_band_disclosure(self) -> "ReleasedRiskBand":
        exact = (
            self.entity_count, self.normalized_weight, self.bad_count,
            self.bad_weight, self.good_count, self.good_weight,
            self.observed_bad_rate, self.score_minimum, self.score_maximum,
        )
        if self.state == "suppressed":
            if any(value is not None for value in exact):
                raise ValueError("suppressed score band cannot expose exact evidence")
            expected_bucket = (
                f"0..{self.minimum_report_cell_count - 1}"
                if self.reason_code == "ad_sparse_report_cell"
                else "hidden"
            )
            if self.count_bucket != expected_bucket:
                raise ValueError("suppressed score band requires canonical count bucket")
            if self.reason_code not in {
                "ad_sparse_report_cell", "ad_complementary_suppression"
            }:
                raise ValueError("suppressed score band requires canonical reason")
        elif self.state == "published":
            if self.entity_count is None or self.entity_count < self.minimum_report_cell_count:
                raise ValueError("published score band must meet disclosure minimum")
            if self.observed_bad_rate is None or self.count_bucket is not None or self.reason_code is not None:
                raise ValueError("published score band requires exact evidence only")
        else:
            raise ValueError("score band release state must be published or suppressed")
        return self


class LiftCapture(StrictModel):
    requested_fraction: float
    achieved_weight_fraction: float
    entity_count: int
    bad_capture: MetricValue
    selected_bad_rate: MetricValue
    lift: MetricValue


class ReleasedLiftCapture(StrictModel):
    state: str
    requested_fraction: float
    minimum_report_cell_count: int = Field(ge=10)
    achieved_weight_fraction: float | None = None
    entity_count: int | None = None
    bad_capture: MetricValue | None = None
    selected_bad_rate: MetricValue | None = None
    lift: MetricValue | None = None
    count_bucket: str | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_disclosure(self) -> "ReleasedLiftCapture":
        exact = (
            self.achieved_weight_fraction, self.entity_count, self.bad_capture,
            self.selected_bad_rate, self.lift,
        )
        if self.state == "suppressed":
            if any(value is not None for value in exact):
                raise ValueError("suppressed lift evidence cannot expose exact values")
            if self.count_bucket not in {
                f"0..{self.minimum_report_cell_count - 1}", "hidden"
            }:
                raise ValueError("suppressed lift evidence requires canonical bucket")
            if self.reason_code not in {
                "ad_sparse_report_cell", "ad_complementary_suppression"
            }:
                raise ValueError("suppressed lift evidence requires canonical reason")
        elif self.state == "published":
            if self.entity_count is None or self.entity_count < self.minimum_report_cell_count:
                raise ValueError("published lift evidence must meet disclosure minimum")
            if self.count_bucket is not None or self.reason_code is not None:
                raise ValueError("published lift evidence cannot carry suppression metadata")
        else:
            raise ValueError("lift release state must be published or suppressed")
        return self


class RiskDiagnostics(StrictModel):
    raw_entity_count: int
    eligible_entity_count: int
    immature_excluded_count: int
    censored_excluded_count: int
    normalized_weight_total: float
    bad_entity_count: int
    good_entity_count: int
    zero_weight_excluded_count: int
    bands: tuple[RiskBand, ...]
    calibration_in_the_large: MetricValue
    brier_score: MetricValue
    calibration_slope: MetricValue
    ks: MetricValue
    ks_maximizing_scores: tuple[float, ...]
    ks_canonical_threshold: float | None
    risk_auc: MetricValue
    gini: MetricValue
    lift_capture: tuple[LiftCapture, ...]
    trace: "RiskTrace"
    bootstrap: tuple["BootstrapEvidence", ...]
    bootstrap_valid_resamples: int
    reliable: bool


class RiskTrace(StrictModel):
    outcome_definition: str
    favorable_outcome_labels: tuple[Any, ...]
    unfavorable_outcome_labels: tuple[Any, ...]
    score_type: ScoreType
    score_target: ScoreTarget
    score_band_edges: tuple[float, ...]
    top_fractions: tuple[float, ...]
    calibration_epsilon: float


class BootstrapEvidence(StrictModel):
    metric_key: str
    valid_resamples: int
    reliable: bool
    lower: float | None
    upper: float | None


class ReleasedBootstrapEvidence(StrictModel):
    state: str
    metric_key: str
    valid_resamples: int | None = None
    reliable: bool | None = None
    lower: float | None = None
    upper: float | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_bootstrap_disclosure(self) -> "ReleasedBootstrapEvidence":
        exact = (self.valid_resamples, self.reliable, self.lower, self.upper)
        if self.state == "suppressed":
            if any(value is not None for value in exact):
                raise ValueError("suppressed bootstrap evidence cannot expose exact values")
            if self.reason_code != "ad_sparse_report_cell":
                raise ValueError("suppressed bootstrap evidence requires canonical reason")
        elif self.state == "published":
            if self.valid_resamples is None or self.reliable is None or self.reason_code is not None:
                raise ValueError("published bootstrap evidence requires exact metadata only")
        else:
            raise ValueError("bootstrap release state must be published or suppressed")
        return self


class ReleasedRiskDiagnostics(RiskDiagnostics):
    bands: tuple[ReleasedRiskBand, ...]
    lift_capture: tuple[ReleasedLiftCapture, ...]
    bootstrap: tuple[ReleasedBootstrapEvidence, ...]


class RiskDiagnosticRelease(StrictModel):
    state: str
    minimum_report_cell_count: int = Field(ge=10)
    entity_count: int | None = None
    diagnostics: ReleasedRiskDiagnostics | None = None
    count_bucket: str | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_disclosure(self) -> "RiskDiagnosticRelease":
        if self.state == "suppressed":
            if self.entity_count is not None or self.diagnostics is not None:
                raise ValueError("suppressed risk evidence cannot expose exact values")
            if self.count_bucket != f"0..{self.minimum_report_cell_count - 1}":
                raise ValueError("suppressed risk evidence requires canonical count bucket")
            if self.reason_code != "ad_sparse_report_cell":
                raise ValueError("suppressed risk evidence requires canonical reason")
        elif self.state == "published":
            if self.entity_count is None or self.entity_count < self.minimum_report_cell_count:
                raise ValueError("published risk evidence must meet disclosure minimum")
            if self.diagnostics is None or self.count_bucket is not None or self.reason_code is not None:
                raise ValueError("published risk evidence requires diagnostics without suppression metadata")
        else:
            raise ValueError("risk release state must be published or suppressed")
        return self


def build_risk_diagnostic_release(
    entities: tuple[RiskEntity, ...], config: RiskEvaluationConfig
) -> RiskDiagnosticRelease:
    if len({item.entity_id for item in entities}) != len(entities):
        raise ValueError("risk evaluation requires one row per entity")
    diagnostics = _evaluate_risk_diagnostics(entities, config)
    if len(entities) < config.minimum_report_cell_count:
        return RiskDiagnosticRelease(
            state="suppressed",
            minimum_report_cell_count=config.minimum_report_cell_count,
            count_bucket=f"0..{config.minimum_report_cell_count - 1}",
            reason_code="ad_sparse_report_cell",
        )
    band_disclosure, lift_disclosure = _risk_disclosure(entities, config)
    released_bands = tuple(
        _release_band(band, band_disclosure[index], config.minimum_report_cell_count)
        for index, band in enumerate(diagnostics.bands)
    )
    released_lift = tuple(
        _release_lift(item, lift_disclosure[index], config.minimum_report_cell_count)
        for index, item in enumerate(diagnostics.lift_capture)
    )
    released_bootstrap = tuple(
        _release_bootstrap(item, released_bands, released_lift)
        for item in diagnostics.bootstrap
    )
    released = ReleasedRiskDiagnostics(
        **diagnostics.model_dump(exclude={"bands", "lift_capture", "bootstrap"}),
        bands=released_bands,
        lift_capture=released_lift,
        bootstrap=released_bootstrap,
    )
    return RiskDiagnosticRelease(
        state="published",
        minimum_report_cell_count=config.minimum_report_cell_count,
        entity_count=len(entities),
        diagnostics=released,
    )


def _release_band(band: RiskBand, evidence, minimum: int) -> ReleasedRiskBand:
    if evidence.state.value == "suppressed":
        return ReleasedRiskBand(
            state="suppressed", lower=band.lower, upper=band.upper,
            minimum_report_cell_count=minimum,
            count_bucket=evidence.count_bucket, reason_code=evidence.reason_code,
        )
    return ReleasedRiskBand(
        state="published", lower=band.lower, upper=band.upper,
        minimum_report_cell_count=minimum,
        entity_count=band.entity_count, normalized_weight=band.normalized_weight,
        bad_count=band.bad_count, bad_weight=band.bad_weight,
        good_count=band.good_count, good_weight=band.good_weight,
        observed_bad_rate=band.observed_bad_rate,
        score_minimum=band.score_minimum, score_maximum=band.score_maximum,
    )


def _release_lift(item, evidence, minimum):
    if evidence.state.value == "suppressed":
        return ReleasedLiftCapture(
            state="suppressed", requested_fraction=item.requested_fraction,
            minimum_report_cell_count=minimum, count_bucket=evidence.count_bucket,
            reason_code=evidence.reason_code,
        )
    return ReleasedLiftCapture(
        state="published", minimum_report_cell_count=minimum, **item.model_dump()
    )


def _risk_disclosure(entities, config):
    """Reuse AD-1's joint equations across bands and lift/capture views."""

    overall = frozenset(item.entity_id for item in entities)
    buckets = [set() for _ in range(len(config.score_band_edges) + 1)]
    favorable = {(type(value), value) for value in config.favorable_outcome_labels}
    unfavorable = {(type(value), value) for value in config.unfavorable_outcome_labels}
    prepared = []
    for item in entities:
        if not item.label_mature or item.censored:
            continue
        if (type(item.outcome), item.outcome) not in favorable | unfavorable:
            continue
        risk = item.score if config.score_target == ScoreTarget.UNFAVORABLE else (
            1 - item.score if config.score_type == ScoreType.PROBABILITY else -item.score
        )
        index = 0
        while index < len(config.score_band_edges) and risk >= config.score_band_edges[index]:
            index += 1
        buckets[index].add(item.entity_id)
        if item.weight > 0:
            prepared.append((item.entity_id, risk, item.weight))
    lift_members = []
    total_weight = sum(row[2] for row in prepared)
    groups = defaultdict(list)
    for row in prepared:
        groups[row[1]].append(row)
    ordered = [groups[score] for score in sorted(groups, reverse=True)]
    for fraction in config.top_fractions:
        selected = []
        cumulative = 0.0
        for block in ordered:
            selected.extend(block)
            cumulative += sum(row[2] for row in block)
            if cumulative >= fraction * total_weight:
                break
        lift_members.append(frozenset(row[0] for row in selected))
    cells = (_CountCell("risk.population", "overall", overall, True),) + tuple(
        _CountCell("risk.score_band", str(index), frozenset(members))
        for index, members in enumerate(buckets)
    ) + tuple(
        _CountCell("risk.lift_capture", str(index), members)
        for index, members in enumerate(lift_members)
    )
    release = _apply_suppression(
        cells, config.minimum_report_cell_count, frozenset()
    )
    by_identity = {(item.table_id, item.cell_id): item for item in release.cells}
    band_release = tuple(
        by_identity[("risk.score_band", str(index))] for index in range(len(buckets))
    )
    lift_release = tuple(
        by_identity[("risk.lift_capture", str(index))]
        for index in range(len(lift_members))
    )
    return band_release, lift_release


def _release_bootstrap(
    evidence: BootstrapEvidence, bands: tuple[ReleasedRiskBand, ...],
    lift: tuple[ReleasedLiftCapture, ...],
) -> ReleasedBootstrapEvidence:
    parts = evidence.metric_key.split(".")
    if len(parts) >= 3 and parts[0] == "band" and parts[1].isdigit():
        index = int(parts[1])
        if index < len(bands) and bands[index].state == "suppressed":
            return ReleasedBootstrapEvidence(
                state="suppressed",
                metric_key=evidence.metric_key,
                reason_code="ad_sparse_report_cell",
            )
    if len(parts) >= 3 and parts[0] == "top":
        requested = float(parts[1])
        item = next((value for value in lift if value.requested_fraction == requested), None)
        if item is not None and item.state == "suppressed":
            return ReleasedBootstrapEvidence(
                state="suppressed", metric_key=evidence.metric_key,
                reason_code="ad_sparse_report_cell",
            )
    return ReleasedBootstrapEvidence(state="published", **evidence.model_dump())


def _evaluate_risk_diagnostics(
    entities: tuple[RiskEntity, ...], config: RiskEvaluationConfig
) -> RiskDiagnostics:
    if len({item.entity_id for item in entities}) != len(entities):
        raise ValueError("risk evaluation requires one row per entity")
    typed_good = {(type(value), value) for value in config.favorable_outcome_labels}
    typed_bad = {(type(value), value) for value in config.unfavorable_outcome_labels}
    prepared = []
    immature = censored = 0
    for item in entities:
        if not item.label_mature:
            immature += 1
            continue
        if item.censored:
            censored += 1
            continue
        key = (type(item.outcome), item.outcome)
        if key not in typed_good | typed_bad:
            raise ValueError("ad_unrecognized_outcome_label")
        if config.score_type == ScoreType.PROBABILITY and not 0 <= item.score <= 1:
            raise ValueError("probability score must be in [0, 1]")
        bad = int(key in typed_bad)
        risk = item.score if config.score_target == ScoreTarget.UNFAVORABLE else (
            1 - item.score if config.score_type == ScoreType.PROBABILITY else -item.score
        )
        prepared.append((item.entity_id, risk, bad, item.weight))
    prepared.sort(key=lambda row: row[0])
    maximum = max((row[3] for row in prepared), default=0.0)
    weighted = [(entity, score, bad, weight / maximum if maximum else 0.0) for entity, score, bad, weight in prepared]
    positive = [row for row in weighted if row[3] > 0]
    total_weight = sum(row[3] for row in positive)
    bad_weight = sum(row[3] for row in positive if row[2])
    good_weight = total_weight - bad_weight
    bad_count = sum(row[2] for row in positive)
    good_count = len(positive) - bad_count
    class_ready = total_weight > 0 and bad_count > 0 and good_count > 0
    bands = _bands(weighted, config.score_band_edges)
    if config.score_type == ScoreType.PROBABILITY and total_weight:
        mean_p = sum(score * weight for _, score, _, weight in positive) / total_weight
        mean_y = bad_weight / total_weight
        calibration = _available(mean_p - mean_y)
        brier = _available(sum(weight * (score - bad) ** 2 for _, score, bad, weight in positive) / total_weight)
        slope = _calibration_slope(positive, config.calibration_epsilon) if class_ready else _undefined("one_outcome_class")
    elif config.score_type == ScoreType.RANKING:
        calibration = brier = slope = MetricValue(state="not_applicable", reason="ranking_score")
    else:
        calibration = brier = slope = _undefined("zero_total_weight")
    ks_value, thresholds = _ks(positive, bad_weight, good_weight) if class_ready else (None, ())
    auc_value = _auc(positive, bad_weight, good_weight) if class_ready else None
    lifts = _lift_capture(positive, config.top_fractions, total_weight, bad_weight)
    bootstrap = _bootstrap_evidence(positive, config) if class_ready else ()
    core_keys = {"ks", "risk_auc", "gini"}
    if config.score_type == ScoreType.PROBABILITY:
        core_keys |= {"brier_score", "calibration_in_the_large"}
    valid = min(
        (item.valid_resamples for item in bootstrap if item.metric_key in core_keys),
        default=0,
    )
    reliable = (
        len(positive) >= config.minimum_total_entities
        and bad_count >= config.minimum_bad_entities
        and good_count >= config.minimum_good_entities
        and valid >= config.minimum_valid_resamples
    )
    return RiskDiagnostics(
        raw_entity_count=len(entities), eligible_entity_count=len(prepared),
        immature_excluded_count=immature, censored_excluded_count=censored,
        normalized_weight_total=total_weight,
        bad_entity_count=bad_count, good_entity_count=good_count,
        zero_weight_excluded_count=len(weighted) - len(positive), bands=bands,
        calibration_in_the_large=calibration, brier_score=brier,
        calibration_slope=slope,
        ks=_available(ks_value) if ks_value is not None else _undefined("class_support_unavailable"),
        ks_maximizing_scores=thresholds,
        ks_canonical_threshold=min(thresholds) if thresholds else None,
        risk_auc=_available(auc_value) if auc_value is not None else _undefined("class_support_unavailable"),
        gini=_available(2 * auc_value - 1) if auc_value is not None else _undefined("class_support_unavailable"),
        lift_capture=lifts,
        trace=RiskTrace(
            outcome_definition=config.outcome_definition,
            favorable_outcome_labels=config.favorable_outcome_labels,
            unfavorable_outcome_labels=config.unfavorable_outcome_labels,
            score_type=config.score_type, score_target=config.score_target,
            score_band_edges=config.score_band_edges, top_fractions=config.top_fractions,
            calibration_epsilon=config.calibration_epsilon,
        ),
        bootstrap=bootstrap, bootstrap_valid_resamples=valid, reliable=reliable,
    )


def _available(value: float) -> MetricValue:
    return MetricValue(state="available", value=float(value))


def _undefined(reason: str) -> MetricValue:
    return MetricValue(state="unavailable", reason=reason)


def _bands(rows, edges) -> tuple[RiskBand, ...]:
    buckets = [[] for _ in range(len(edges) + 1)]
    for row in rows:
        index = 0
        while index < len(edges) and row[1] >= edges[index]:
            index += 1
        buckets[index].append(row)
    result = []
    for index, bucket in enumerate(buckets):
        weight = sum(row[3] for row in bucket)
        bad_weight = sum(row[3] for row in bucket if row[2])
        result.append(RiskBand(
            lower=None if index == 0 else edges[index - 1],
            upper=None if index == len(edges) else edges[index],
            entity_count=len(bucket), normalized_weight=weight,
            bad_count=sum(row[2] for row in bucket), bad_weight=bad_weight,
            good_count=sum(not row[2] for row in bucket), good_weight=weight - bad_weight,
            observed_bad_rate=_available(bad_weight / weight) if weight else _undefined("empty_band"),
            score_minimum=min((row[1] for row in bucket), default=None),
            score_maximum=max((row[1] for row in bucket), default=None),
        ))
    return tuple(result)


def _ks(rows, total_bad, total_good):
    grouped = defaultdict(lambda: [0.0, 0.0])
    for _, score, bad, weight in rows:
        grouped[score][bad] += weight
    cumulative_bad = cumulative_good = maximum = 0.0
    thresholds = []
    for score in sorted(grouped, reverse=True):
        cumulative_good += grouped[score][0]
        cumulative_bad += grouped[score][1]
        difference = abs(cumulative_bad / total_bad - cumulative_good / total_good)
        if difference > maximum + 1e-15:
            maximum, thresholds = difference, [score]
        elif abs(difference - maximum) <= 1e-15:
            thresholds.append(score)
    return maximum, tuple(thresholds)


def _auc(rows, total_bad, total_good):
    value = 0.0
    for _, bad_score, bad, bad_w in rows:
        if not bad:
            continue
        for _, good_score, good_bad, good_w in rows:
            if good_bad:
                continue
            value += bad_w * good_w * (1.0 if bad_score > good_score else 0.5 if bad_score == good_score else 0.0)
    return value / (total_bad * total_good)


def _lift_capture(rows, fractions, total_weight, total_bad):
    if total_weight <= 0:
        return tuple(LiftCapture(requested_fraction=f, achieved_weight_fraction=0, entity_count=0,
            bad_capture=_undefined("zero_total_weight"), selected_bad_rate=_undefined("zero_selected_weight"),
            lift=_undefined("zero_selected_weight")) for f in fractions)
    groups = defaultdict(list)
    for row in rows:
        groups[row[1]].append(row)
    ordered = [groups[score] for score in sorted(groups, reverse=True)]
    overall = total_bad / total_weight if total_bad else 0
    output = []
    for fraction in fractions:
        selected = []
        cumulative = 0.0
        for block in ordered:
            selected.extend(block)
            cumulative += sum(row[3] for row in block)
            if cumulative >= fraction * total_weight:
                break
        selected_bad = sum(row[3] for row in selected if row[2])
        rate = selected_bad / cumulative if cumulative else None
        output.append(LiftCapture(
            requested_fraction=fraction, achieved_weight_fraction=cumulative / total_weight,
            entity_count=len(selected),
            bad_capture=_available(selected_bad / total_bad) if total_bad else _undefined("zero_bad_weight"),
            selected_bad_rate=_available(rate) if rate is not None else _undefined("zero_selected_weight"),
            lift=_available(rate / overall) if rate is not None and overall else _undefined("zero_bad_weight"),
        ))
    return tuple(output)


def _calibration_slope(rows, epsilon, *, max_iterations=100):
    x = [math.log(min(max(score, epsilon), 1 - epsilon) / (1 - min(max(score, epsilon), 1 - epsilon))) for _, score, _, _ in rows]
    if max(x) == min(x):
        return _undefined("constant_probability")
    good_x = [value for value, row in zip(x, rows) if not row[2]]
    bad_x = [value for value, row in zip(x, rows) if row[2]]
    if max(good_x) < min(bad_x) or max(bad_x) < min(good_x):
        return _undefined("separation")
    intercept = slope = 0.0
    for _ in range(max_iterations):
        h00 = h01 = h11 = g0 = g1 = 0.0
        for predictor, (_, _, outcome, weight) in zip(x, rows):
            linear = intercept + slope * predictor
            probability = 1 / (1 + math.exp(-max(min(linear, 700), -700)))
            variance = weight * probability * (1 - probability)
            residual = weight * (outcome - probability)
            h00 += variance; h01 += variance * predictor; h11 += variance * predictor * predictor
            g0 += residual; g1 += residual * predictor
        determinant = h00 * h11 - h01 * h01
        if determinant <= 1e-18:
            return _undefined("singular")
        delta0 = (g0 * h11 - g1 * h01) / determinant
        delta1 = (g1 * h00 - g0 * h01) / determinant
        intercept += delta0; slope += delta1
        if max(abs(delta0), abs(delta1)) <= 1e-10:
            return _available(slope)
        if max(abs(intercept), abs(slope)) > 1e6:
            return _undefined("separation")
    return _undefined("non_convergence")


def _bootstrap_evidence(rows, config):
    bad = [row for row in rows if row[2]]
    good = [row for row in rows if not row[2]]
    values: dict[str, list[float]] = defaultdict(list)
    for key in ("ks", "risk_auc", "gini"):
        values[key]
    if config.score_type == ScoreType.PROBABILITY:
        for key in ("brier_score", "calibration_in_the_large", "calibration_slope"):
            values[key]
    for index in range(len(config.score_band_edges) + 1):
        values[f"band.{index}.observed_bad_rate"]
    for fraction in config.top_fractions:
        for suffix in ("bad_capture", "selected_bad_rate", "lift"):
            values[f"top.{fraction:g}.{suffix}"]
    bad_draws = bootstrap_index_draws(
        len(bad), config.bootstrap_resamples, seed=config.bootstrap_seed,
        metric_key="ad3.entity_stratified", stream_role="comparison",
    )
    good_draws = bootstrap_index_draws(
        len(good), config.bootstrap_resamples, seed=config.bootstrap_seed,
        metric_key="ad3.entity_stratified", stream_role="reference",
    )
    for replicate in range(config.bootstrap_resamples):
        sample = (
            [bad[index] for index in bad_draws[replicate]]
            + [good[index] for index in good_draws[replicate]]
        )
        sample_bad = sum(row[3] for row in sample if row[2])
        sample_good = sum(row[3] for row in sample if not row[2])
        if not sample or sample_bad <= 0 or sample_good <= 0:
            continue
        total = sample_bad + sample_good
        ks, _ = _ks(sample, sample_bad, sample_good)
        auc = _auc(sample, sample_bad, sample_good)
        values["ks"].append(ks); values["risk_auc"].append(auc); values["gini"].append(2 * auc - 1)
        if config.score_type == ScoreType.PROBABILITY:
            values["brier_score"].append(sum(w * (s - y) ** 2 for _, s, y, w in sample) / total)
            values["calibration_in_the_large"].append(
                sum(w * s for _, s, _, w in sample) / total - sample_bad / total
            )
            slope = _calibration_slope(sample, config.calibration_epsilon)
            if slope.state == MetricState.AVAILABLE:
                values["calibration_slope"].append(slope.value)
        for index, band in enumerate(_bands(sample, config.score_band_edges)):
            if band.observed_bad_rate.state == MetricState.AVAILABLE:
                values[f"band.{index}.observed_bad_rate"].append(band.observed_bad_rate.value)
        for item in _lift_capture(sample, config.top_fractions, total, sample_bad):
            prefix = f"top.{item.requested_fraction:g}"
            for suffix, metric in (("bad_capture", item.bad_capture), ("selected_bad_rate", item.selected_bad_rate), ("lift", item.lift)):
                if metric.state == MetricState.AVAILABLE:
                    values[f"{prefix}.{suffix}"].append(metric.value)
    output = []
    for key in sorted(values):
        samples = sorted(values[key])
        output.append(BootstrapEvidence(
            metric_key=key, valid_resamples=len(samples),
            reliable=len(samples) >= config.minimum_valid_resamples,
            lower=_type7(samples, 0.025), upper=_type7(samples, 0.975),
        ))
    return tuple(output)


def _type7(values, probability):
    if not values:
        return None
    position = (len(values) - 1) * probability
    lower = math.floor(position); upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] + fraction * (values[upper] - values[lower])
