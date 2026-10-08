"""Frozen Paper 2 synthetic data-generating equations."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import ndtr

from fairlendkit.research.paper2.registry import (
    Calibration,
    Missingness,
    Scenario,
    ScenarioFamily,
    scenario_registry,
)
from fairlendkit.research.paper2.rng import generator_rng, generator_scope


@dataclass(frozen=True)
class GeneratedRow:
    group: int
    outcome: int | None
    score: float | None
    decision: int | None


@dataclass(frozen=True)
class GeneratedAudit:
    scenario_id: str
    pair_id: str
    replicate_id: int
    rows: tuple[GeneratedRow, ...]


def _logistic(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + exp(-value))
    exp_value = exp(value)
    return exp_value / (1.0 + exp_value)


def _bisect(function, *, lower: float, upper: float, tolerance: float = 1e-10) -> float:
    f_lower = function(lower)
    f_upper = function(upper)
    if f_lower == 0:
        return lower
    if f_upper == 0:
        return upper
    if f_lower * f_upper > 0:
        raise ValueError("Frozen solver bracket does not contain a root.")
    for _ in range(200):
        midpoint = (lower + upper) / 2.0
        f_midpoint = function(midpoint)
        if abs(f_midpoint) <= tolerance or (upper - lower) / 2.0 <= tolerance:
            return midpoint
        if f_lower * f_midpoint <= 0:
            upper = midpoint
        else:
            lower = midpoint
            f_lower = f_midpoint
    raise RuntimeError("Frozen bisection solver failed to converge.")


def _quadrature() -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(64)
    return nodes * sqrt(2.0), weights / sqrt(np.pi)


def solve_alpha(prevalence: float, beta: float) -> float:
    nodes, weights = _quadrature()

    def residual(alpha: float) -> float:
        probabilities = np.array([_logistic(alpha + beta * x) for x in nodes])
        return float(np.dot(weights, probabilities)) - prevalence

    return _bisect(residual, lower=-30.0, upper=30.0)


def population_auc(alpha: float, beta: float) -> float:
    nodes, weights = _quadrature()
    probabilities = np.array([_logistic(alpha + beta * x) for x in nodes])
    prevalence = float(np.dot(weights, probabilities))
    numerator = 0.0
    for i, x_positive in enumerate(nodes):
        for j, x_negative in enumerate(nodes):
            if x_positive > x_negative:
                numerator += (
                    weights[i]
                    * weights[j]
                    * probabilities[i]
                    * (1.0 - probabilities[j])
                )
            elif x_positive == x_negative:
                numerator += 0.5 * (
                    weights[i]
                    * weights[j]
                    * probabilities[i]
                    * (1.0 - probabilities[j])
                )
    return numerator / (prevalence * (1.0 - prevalence))


def solve_performance_parameters(prevalence: float, target_auc: float) -> tuple[float, float]:
    if target_auc == 0.5:
        return log(prevalence / (1.0 - prevalence)), 0.0

    def residual(beta: float) -> float:
        alpha = solve_alpha(prevalence, beta)
        return population_auc(alpha, beta) - target_auc

    beta = _bisect(residual, lower=1e-8, upper=12.0)
    return solve_alpha(prevalence, beta), beta


def _decision_prevalence(
    threshold: float, alpha: float, beta: float, calibration: Calibration
) -> float:
    threshold_logit = log(threshold / (1.0 - threshold))
    if calibration is Calibration.INTERCEPT_SHIFT:
        threshold_logit -= 0.75
    elif calibration is Calibration.SLOPE_DISTORTION:
        threshold_logit /= 0.60
    x_threshold = (threshold_logit - alpha) / beta
    return 1.0 - float(ndtr(x_threshold))


def solve_score_threshold(
    alpha: float, beta: float, calibration: Calibration, target: float
) -> float:
    if not 0.0 < target < 1.0:
        raise ValueError("Decision prevalence target must be strictly between 0 and 1.")
    if beta <= 0.0:
        raise ValueError("Decision-threshold solver requires positive beta.")
    epsilon = 2.0**-52
    return _bisect(
        lambda threshold: _decision_prevalence(threshold, alpha, beta, calibration)
        - target,
        lower=epsilon,
        upper=1.0 - epsilon,
    )


def _calibrated_score(probability: float, calibration: Calibration) -> float:
    logit = log(probability / (1.0 - probability))
    if calibration is Calibration.CALIBRATED:
        return probability
    if calibration is Calibration.INTERCEPT_SHIFT:
        return _logistic(logit + 0.75)
    return _logistic(0.60 * logit)


def _missing_probability(
    scenario: Scenario, intercept: float, group: int, score: float, outcome: int
) -> float:
    if scenario.missingness is Missingness.NONE:
        return 0.0
    if scenario.missingness is Missingness.MCAR:
        return scenario.missing_fraction

    if scenario.missingness is Missingness.MAR:
        return _logistic(intercept + 0.75 * group + 0.50 * int(score < 0.2))
    return _logistic(
        intercept
        + 0.75 * group
        + 1.00 * int(outcome == 0)
        + 0.50 * group * int(outcome == 0)
    )


def solve_missing_intercept(
    scenario: Scenario, performance_parameters: tuple[float, float] | None
) -> float:
    if scenario.missingness in {Missingness.NONE, Missingness.MCAR}:
        return 0.0
    group_weights = (
        scenario.reference_n / (scenario.reference_n + scenario.comparison_n),
        scenario.comparison_n / (scenario.reference_n + scenario.comparison_n),
    )
    nodes, weights = _quadrature()

    def expected(intercept: float) -> float:
        total = 0.0
        for group, group_weight in enumerate(group_weights):
            if scenario.family is ScenarioFamily.SELECTION:
                selection_rate = 0.50 if group == 0 else 0.50 * scenario.population_air
                score_outcomes = ((0.25, 1.0 - selection_rate), (0.75, selection_rate))
                for score, score_weight in score_outcomes:
                    if scenario.missingness is Missingness.MAR:
                        total += group_weight * score_weight * _missing_probability(
                            scenario, intercept, group, score, 0
                        )
                    else:
                        for outcome, outcome_weight in ((0, 0.80), (1, 0.20)):
                            total += (
                                group_weight
                                * score_weight
                                * outcome_weight
                                * _missing_probability(
                                    scenario, intercept, group, score, outcome
                                )
                            )
            else:
                assert performance_parameters is not None
                alpha, beta = performance_parameters
                for node, node_weight in zip(nodes, weights, strict=True):
                    probability = _logistic(alpha + beta * node)
                    score = _calibrated_score(probability, scenario.calibration)
                    if scenario.missingness is Missingness.MAR:
                        total += group_weight * node_weight * _missing_probability(
                            scenario, intercept, group, score, 0
                        )
                    else:
                        for outcome, outcome_weight in ((0, 1.0 - probability), (1, probability)):
                            total += (
                                group_weight
                                * node_weight
                                * outcome_weight
                                * _missing_probability(
                                    scenario, intercept, group, score, outcome
                                )
                            )
        return total

    return _bisect(
        lambda intercept: expected(intercept) - scenario.missing_fraction,
        lower=-30.0,
        upper=30.0,
    )


def generate_audit(scenario: Scenario, replicate_id: int, master_seed: int) -> GeneratedAudit:
    pair_id = scenario.effective_pair_id
    paired = tuple(
        item for item in scenario_registry().values() if item.effective_pair_id == pair_id
    )
    max_reference_n = max(item.reference_n for item in paired)
    max_comparison_n = max(item.comparison_n for item in paired)

    def stream(role: str):
        return generator_rng(
            master_seed=master_seed,
            pair_id=pair_id,
            replicate_id=replicate_id,
            scope=generator_scope(pair_id, scenario.scenario_id, role),
            role=role,
        )

    decision_rng = stream("selection_decision_uniform") if scenario.family is ScenarioFamily.SELECTION else None
    selection_outcome_rng = stream("selection_outcome_uniform") if scenario.family is ScenarioFamily.SELECTION else None
    performance_x_rng = stream("performance_x_normal") if scenario.family is ScenarioFamily.PERFORMANCE else None
    performance_outcome_rng = stream("performance_outcome_uniform") if scenario.family is ScenarioFamily.PERFORMANCE else None
    missing_rng = stream("missingness_uniform")
    performance_parameters = None
    threshold = 0.5
    if scenario.family is ScenarioFamily.PERFORMANCE:
        performance_parameters = solve_performance_parameters(
            scenario.outcome_prevalence, scenario.population_auc
        )
        threshold = solve_score_threshold(
            *performance_parameters, scenario.calibration, scenario.decision_prevalence
        )
    missing_intercept = solve_missing_intercept(scenario, performance_parameters)

    rows: list[GeneratedRow] = []
    for group, count, generation_count in (
        (0, scenario.reference_n, max_reference_n),
        (1, scenario.comparison_n, max_comparison_n),
    ):
        for row_index in range(generation_count):
            if scenario.family is ScenarioFamily.SELECTION:
                assert decision_rng is not None and selection_outcome_rng is not None
                selection_rate = 0.50 if group == 0 else 0.50 * scenario.population_air
                decision = decision_rng.bernoulli(selection_rate)
                score = 0.75 if decision else 0.25
                outcome = selection_outcome_rng.bernoulli(0.20)
            else:
                assert performance_parameters is not None
                assert performance_x_rng is not None and performance_outcome_rng is not None
                alpha, beta = performance_parameters
                x_value = performance_x_rng.normal()
                probability = _logistic(alpha + beta * x_value)
                outcome = performance_outcome_rng.bernoulli(probability)
                score = _calibrated_score(probability, scenario.calibration)
                decision = int(score >= threshold)
            missing = missing_rng.bernoulli(
                _missing_probability(scenario, missing_intercept, group, score, outcome)
            )
            if row_index < count:
                rows.append(
                    GeneratedRow(
                        group,
                        None if missing else outcome,
                        None if missing else score,
                        None if missing else decision,
                    )
                )
    return GeneratedAudit(
        scenario.scenario_id,
        scenario.effective_pair_id,
        replicate_id,
        tuple(rows),
    )
