"""Reproducible simulated impact benchmark; never customer-impact evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from typing import Callable, Sequence


BENCHMARK_ID = "fairlendkit-simulated-impact-v1"
SCENARIO_ID = "fairlendkit-sim-impact-v1"
CODE_COMMIT_BASIS = "81891a8"
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
    scenario_id: str
    evidence_class: str
    code_commit_basis: str
    generated_at_utc: str
    evidence_status: str
    seed: int
    population_size: int
    input_sha256: str
    repetitions: int
    baseline_median_seconds: float
    tool_median_seconds: float
    runtime_statistics: dict[str, dict[str, float | int]]
    covered_applicants: int
    baseline: PolicyMetrics
    tool: PolicyMetrics
    approval_increment: int
    credit_increment: int
    average_incremental_credit: float
    policy_assumptions: dict[str, int | float | str]
    config_summary: dict[str, int | str]
    formulas: dict[str, str]
    runtime_environment: dict[str, str]
    analyst_effort_scenario: dict[str, int | float | str]
    review_coverage_scenario: dict[str, int | float | str]
    group_evidence: dict[str, object]
    risk_constraint: dict[str, bool | float | str]
    data_provenance: dict[str, str]
    constraint_status: str
    reason_code: str
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


def _runtime_statistics(
    function: Callable[[Sequence[SimulatedApplicant]], tuple[bool, ...]],
    rows: Sequence[SimulatedApplicant],
    repetitions: int,
) -> dict[str, float | int]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        function(rows)
        samples.append((time.perf_counter_ns() - start) / 1_000_000_000)
    return {
        "repetitions": repetitions,
        "mean_seconds": statistics.mean(samples),
        "median_seconds": statistics.median(samples),
        "stdev_seconds": statistics.stdev(samples) if repetitions > 1 else 0.0,
    }


def _wilson_interval(successes: int, total: int) -> list[float]:
    """Return a deterministic 95% Wilson interval for a binomial rate."""

    if total < 1:
        raise ValueError("Wilson interval requires a non-empty group")
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total**2))
    margin /= denominator
    return [centre - margin, centre + margin]


def _group_evidence(
    rows: Sequence[SimulatedApplicant], decisions: Sequence[bool]
) -> dict[str, dict[str, int | float | list[float]]]:
    evidence = {}
    for name, comparison in (("reference", False), ("comparison", True)):
        selected = [
            decision
            for row, decision in zip(rows, decisions, strict=True)
            if row.comparison_group is comparison
        ]
        approvals = sum(selected)
        evidence[name] = {
            "sample_size": len(selected),
            "approvals": approvals,
            "selection_rate": approvals / len(selected),
            "selection_rate_wilson_95": _wilson_interval(approvals, len(selected)),
        }
    return evidence


def run_benchmark(
    *, seed: int = SEED, population_size: int = POPULATION_SIZE,
    repetitions: int = REPETITIONS,
) -> BenchmarkResult:
    rows = generate_simulated_applicants(seed=seed, population_size=population_size)
    baseline = baseline_decisions(rows)
    tool = tool_decisions(rows)
    baseline_metrics = policy_metrics(rows, baseline)
    tool_metrics = policy_metrics(rows, tool)
    baseline_runtime = _runtime_statistics(baseline_decisions, rows, repetitions)
    tool_runtime = _runtime_statistics(tool_decisions, rows, repetitions)
    risk_passed = tool_metrics.approved_bad_rate <= baseline_metrics.approved_bad_rate
    return BenchmarkResult(
        benchmark_id=BENCHMARK_ID,
        scenario_id=SCENARIO_ID,
        evidence_class="simulation_not_production_evidence",
        code_commit_basis=CODE_COMMIT_BASIS,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        evidence_status="simulation_not_production_evidence",
        seed=seed,
        population_size=population_size,
        input_sha256=_input_sha256(rows),
        repetitions=repetitions,
        baseline_median_seconds=float(baseline_runtime["median_seconds"]),
        tool_median_seconds=float(tool_runtime["median_seconds"]),
        runtime_statistics={"baseline": baseline_runtime, "tool": tool_runtime},
        covered_applicants=sum(row.alternative_data_available for row in rows),
        baseline=baseline_metrics,
        tool=tool_metrics,
        approval_increment=tool_metrics.approvals - baseline_metrics.approvals,
        credit_increment=tool_metrics.approved_credit - baseline_metrics.approved_credit,
        average_incremental_credit=(
            (tool_metrics.approved_credit - baseline_metrics.approved_credit)
            / (tool_metrics.approvals - baseline_metrics.approvals)
        ),
        policy_assumptions={
            "baseline_credit_score_minimum": 680,
            "second_look_credit_score_minimum": 640,
            "second_look_credit_score_maximum_exclusive": 680,
            "second_look_alternative_score_minimum": 0.72,
            "requested_credit_minimum": 2000,
            "requested_credit_maximum": 20000,
            "requested_credit_increment": 500,
            "comparison_group": "fixed synthetic group; not a protected-class claim",
        },
        config_summary={
            "evaluation_sample": "same deterministic input_sha256 for baseline and tool",
            "outcome_label": "same synthetic favorable_outcome for baseline and tool",
            "time_window": "same single generated cross-section; no temporal split",
            "risk_rule": "tool approved bad rate <= baseline approved bad rate",
            "credit_amounts": "same pre-decision requested_credit for baseline and tool",
            "group_definition": "same fixed synthetic comparison_group for baseline and tool",
            "population_size": population_size,
        },
        formulas={
            "approval_increment": "tool.approvals - baseline.approvals",
            "credit_increment": "tool.approved_credit - baseline.approved_credit",
            "average_incremental_credit": "credit_increment / approval_increment",
            "approved_bad_rate": "approved unfavorable outcomes / approvals",
            "true_positive_rate": "approved favorable outcomes / favorable outcomes",
            "false_positive_rate": "approved unfavorable outcomes / unfavorable outcomes",
            "selection_rate_difference": "comparison selection rate - reference selection rate",
            "adverse_impact_ratio": "comparison selection rate / reference selection rate",
        },
        runtime_environment={
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "executable": sys.executable,
            "timer": "time.perf_counter_ns",
        },
        analyst_effort_scenario={
            "status": "scenario_assumption_not_wall_clock_derived",
            "analysts": 2,
            "hours_per_workday": 8,
            "baseline_workdays": 5,
            "tool_assisted_workdays": 2,
            "baseline_person_hours": 80,
            "tool_assisted_person_hours": 32,
            "person_hours_saved": 48,
            "time_reduction_rate": 0.6,
        },
        review_coverage_scenario={
            "status": "scenario_assumption_not_observed_customer_coverage",
            "population": population_size,
            "baseline_people": 2000,
            "tool_people": population_size,
            "additional_people": population_size - 2000,
            "baseline_rate": 2000 / population_size,
            "tool_rate": 1.0,
        },
        group_evidence={
            "baseline": _group_evidence(rows, baseline),
            "tool": _group_evidence(rows, tool),
        },
        risk_constraint={
            "rule": "tool approved bad rate <= baseline approved bad rate",
            "baseline_approved_bad_rate": baseline_metrics.approved_bad_rate,
            "tool_approved_bad_rate": tool_metrics.approved_bad_rate,
            "passed": risk_passed,
        },
        data_provenance={
            "identity": "deterministic synthetic applicants generated in repository",
            "allowed_use": "simulation and test only",
            "customer_data": "none",
        },
        constraint_status="passed" if risk_passed else "failed",
        reason_code="constraints_passed" if risk_passed else "risk_constraint_failed",
        disclaimer=(
            "Synthetic simulation only; not a pilot, customer outcome, production "
            "decision, causal estimate, or compliance conclusion."
        ),
    )
