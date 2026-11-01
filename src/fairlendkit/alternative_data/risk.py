"""Deterministic AD-3 credit-risk diagnostics on one entity-level population."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
import hashlib
import math
import random
from typing import Any

from pydantic import Field, field_validator, model_validator

from fairlendkit.alternative_data.contracts import StrictModel


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


class LiftCapture(StrictModel):
    requested_fraction: float
    achieved_weight_fraction: float
    entity_count: int
    bad_capture: MetricValue
    selected_bad_rate: MetricValue
    lift: MetricValue


class RiskDiagnostics(StrictModel):
    raw_entity_count: int
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
    bootstrap_valid_resamples: int
    reliable: bool


def evaluate_risk_diagnostics(
    entities: tuple[RiskEntity, ...], config: RiskEvaluationConfig
) -> RiskDiagnostics:
    if len({item.entity_id for item in entities}) != len(entities):
        raise ValueError("risk evaluation requires one row per entity")
    typed_good = {(type(value), value) for value in config.favorable_outcome_labels}
    typed_bad = {(type(value), value) for value in config.unfavorable_outcome_labels}
    prepared = []
    for item in entities:
        if not item.label_mature or item.censored:
            raise ValueError("ad_label_immature" if not item.label_mature else "ad_unrecognized_outcome_label")
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
    else:
        calibration = brier = slope = MetricValue(state="not_applicable", reason="ranking_score")
    ks_value, thresholds = _ks(positive, bad_weight, good_weight) if class_ready else (None, ())
    auc_value = _auc(positive, bad_weight, good_weight) if class_ready else None
    lifts = _lift_capture(positive, config.top_fractions, total_weight, bad_weight)
    valid = _bootstrap_valid_count(positive, config) if class_ready else 0
    reliable = (
        len(positive) >= config.minimum_total_entities
        and bad_count >= config.minimum_bad_entities
        and good_count >= config.minimum_good_entities
        and valid >= config.minimum_valid_resamples
    )
    return RiskDiagnostics(
        raw_entity_count=len(entities), normalized_weight_total=total_weight,
        bad_entity_count=bad_count, good_entity_count=good_count,
        zero_weight_excluded_count=len(weighted) - len(positive), bands=bands,
        calibration_in_the_large=calibration, brier_score=brier,
        calibration_slope=slope,
        ks=_available(ks_value) if ks_value is not None else _undefined("class_support_unavailable"),
        ks_maximizing_scores=thresholds,
        ks_canonical_threshold=min(thresholds) if thresholds else None,
        risk_auc=_available(auc_value) if auc_value is not None else _undefined("class_support_unavailable"),
        gini=_available(2 * auc_value - 1) if auc_value is not None else _undefined("class_support_unavailable"),
        lift_capture=lifts, bootstrap_valid_resamples=valid, reliable=reliable,
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


def _calibration_slope(rows, epsilon):
    x = [math.log(min(max(score, epsilon), 1 - epsilon) / (1 - min(max(score, epsilon), 1 - epsilon))) for _, score, _, _ in rows]
    if max(x) == min(x):
        return _undefined("constant_probability")
    intercept = slope = 0.0
    for _ in range(100):
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
            return _undefined("singular_or_separated")
        delta0 = (g0 * h11 - g1 * h01) / determinant
        delta1 = (g1 * h00 - g0 * h01) / determinant
        intercept += delta0; slope += delta1
        if max(abs(delta0), abs(delta1)) <= 1e-10:
            return _available(slope)
        if max(abs(intercept), abs(slope)) > 1e6:
            return _undefined("separation")
    return _undefined("non_convergence")


def _bootstrap_valid_count(rows, config):
    bad = [row for row in rows if row[2]]
    good = [row for row in rows if not row[2]]
    valid = 0
    for replicate in range(config.bootstrap_resamples):
        digest = hashlib.sha256(f"ad3|{config.bootstrap_seed}|{replicate}".encode()).digest()
        rng = random.Random(int.from_bytes(digest, "big"))
        sample = [rng.choice(bad) for _ in bad] + [rng.choice(good) for _ in good]
        if sample and sum(row[3] for row in sample if row[2]) > 0 and sum(row[3] for row in sample if not row[2]) > 0:
            valid += 1
    return valid
