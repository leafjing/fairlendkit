"""Reproducible simulated impact benchmark; never customer-impact evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random
import statistics
import time
from typing import Callable, Sequence


BENCHMARK_ID = "fairlendkit-simulated-impact-v1"
SEED = 20261102
POPULATION_SIZE = 10_000
REPETITIONS = 15


@dataclass(frozen=True)
class SimulatedApplicant:
    applicant_id: int
    comparison_group: bool
    credit_score: int
    alternative_score: float
    alternative_data_available: bool
    favorable_outcome: bool
    requested_credit: int


@dataclass(frozen=True)
class PolicyMetrics:
    approvals: int
    approved_credit: int
    approved_bad_rate: float
    true_positive_rate: float
    false_positive_rate: float
    reference_selection_rate: float
    comparison_selection_rate: float
    selection_rate_difference: float
    adverse_impact_ratio: float


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    seed: int
    population_size: int
    input_sha256: str
    repetitions: int
    baseline_median_seconds: float
    tool_median_seconds: float
    covered_applicants: int
    baseline: PolicyMetrics
    tool: PolicyMetrics
    approval_increment: int
    credit_increment: int
    disclaimer: str

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def generate_simulated_applicants(
    *, seed: int = SEED, population_size: int = POPULATION_SIZE
) -> tuple[SimulatedApplicant, ...]:
    """Generate a frozen synthetic population with no customer records."""

    if population_size < 1:
        raise ValueError("population_size must be positive")
    rng = random.Random(seed)
    rows = []
    for applicant_id in range(population_size):
        comparison = rng.random() < 0.4
        credit_score = max(500, min(800, round(rng.gauss(675 - 12 * comparison, 48))))
        latent = (credit_score - 650) / 85 + rng.gauss(0, 0.8) - 0.08 * comparison
        alternative_score = 1 / (1 + math.exp(-latent))
        available = rng.random() < (0.68 if comparison else 0.61)
        favorable_probability = 1 / (1 + math.exp(-(latent - 0.05)))
        favorable = rng.random() < favorable_probability
        requested_credit = 500 * rng.randint(4, 40)
        rows.append(
            SimulatedApplicant(
                applicant_id=applicant_id,
                comparison_group=comparison,
                credit_score=credit_score,
                alternative_score=round(alternative_score, 12),
                alternative_data_available=available,
                favorable_outcome=favorable,
                requested_credit=requested_credit,
            )
        )
    return tuple(rows)


def baseline_decisions(rows: Sequence[SimulatedApplicant]) -> tuple[bool, ...]:
    return tuple(row.credit_score >= 680 for row in rows)


def tool_decisions(rows: Sequence[SimulatedApplicant]) -> tuple[bool, ...]:
    """Simulated policy: baseline plus a narrow, predeclared second-look rule."""

    return tuple(
        row.credit_score >= 680
        or (
            640 <= row.credit_score < 680
            and row.alternative_data_available
            and row.alternative_score >= 0.72
        )
        for row in rows
    )


def _rate(numerator: int, denominator: int, name: str) -> float:
    if denominator == 0:
        raise ValueError(f"{name} is undefined for the simulated population")
    return numerator / denominator


def policy_metrics(
    rows: Sequence[SimulatedApplicant], decisions: Sequence[bool]
) -> PolicyMetrics:
    if len(rows) != len(decisions):
        raise ValueError("rows and decisions must have equal lengths")
    approved = [row for row, decision in zip(rows, decisions, strict=True) if decision]
    good = sum(row.favorable_outcome for row in rows)
    bad = len(rows) - good
    true_positive = sum(
        decision and row.favorable_outcome
        for row, decision in zip(rows, decisions, strict=True)
    )
    false_positive = sum(
        decision and not row.favorable_outcome
        for row, decision in zip(rows, decisions, strict=True)
    )
    reference = [
        decision for row, decision in zip(rows, decisions, strict=True)
        if not row.comparison_group
    ]
    comparison = [
        decision for row, decision in zip(rows, decisions, strict=True)
        if row.comparison_group
    ]
    reference_rate = _rate(sum(reference), len(reference), "reference selection rate")
    comparison_rate = _rate(sum(comparison), len(comparison), "comparison selection rate")
    return PolicyMetrics(
        approvals=len(approved),
        approved_credit=sum(row.requested_credit for row in approved),
        approved_bad_rate=_rate(
            sum(not row.favorable_outcome for row in approved),
            len(approved),
            "approved bad rate",
        ),
        true_positive_rate=_rate(true_positive, good, "true positive rate"),
        false_positive_rate=_rate(false_positive, bad, "false positive rate"),
        reference_selection_rate=reference_rate,
        comparison_selection_rate=comparison_rate,
        selection_rate_difference=comparison_rate - reference_rate,
        adverse_impact_ratio=_rate(comparison_rate, reference_rate, "adverse impact ratio"),
    )


def _input_sha256(rows: Sequence[SimulatedApplicant]) -> str:
    payload = json.dumps(
        [asdict(row) for row in rows], sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _median_runtime(
    function: Callable[[Sequence[SimulatedApplicant]], tuple[bool, ...]],
    rows: Sequence[SimulatedApplicant],
    repetitions: int,
) -> float:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        function(rows)
        samples.append((time.perf_counter_ns() - start) / 1_000_000_000)
    return statistics.median(samples)


def run_benchmark(
    *, seed: int = SEED, population_size: int = POPULATION_SIZE,
    repetitions: int = REPETITIONS,
) -> BenchmarkResult:
    rows = generate_simulated_applicants(seed=seed, population_size=population_size)
    baseline = baseline_decisions(rows)
    tool = tool_decisions(rows)
    baseline_metrics = policy_metrics(rows, baseline)
    tool_metrics = policy_metrics(rows, tool)
    return BenchmarkResult(
        benchmark_id=BENCHMARK_ID,
        seed=seed,
        population_size=population_size,
        input_sha256=_input_sha256(rows),
        repetitions=repetitions,
        baseline_median_seconds=_median_runtime(baseline_decisions, rows, repetitions),
        tool_median_seconds=_median_runtime(tool_decisions, rows, repetitions),
        covered_applicants=sum(row.alternative_data_available for row in rows),
        baseline=baseline_metrics,
        tool=tool_metrics,
        approval_increment=tool_metrics.approvals - baseline_metrics.approvals,
        credit_increment=tool_metrics.approved_credit - baseline_metrics.approved_credit,
        disclaimer=(
            "Synthetic simulation only; not a pilot, customer outcome, production "
            "decision, causal estimate, or compliance conclusion."
        ),
    )
