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
RISK_THRESHOLD = 0.20
ASSUMED_AVERAGE_CREDIT = 8_000
RUN_COMMAND = "PYTHONPATH=src python3 scripts/run_simulated_impact_benchmark.py"


@dataclass(frozen=True)
class SimulatedApplicant:
    applicant_id: int
    comparison_group: bool
    credit_score: int
    alternative_score: float
    alternative_data_available: bool
    favorable_outcome: bool
    predicted_bad_probability: float
    outcome_matured_12m: bool
    bad_12m: bool
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
    input_file_sha256: str
    config_sha256: str
    stable_row_ids_sha256: str
    run_command: str
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
    decision_set_digests: dict[str, str | int]
    scenario_expectations: dict[str, int | float | bool]
    publication_gate: dict[str, str | bool]
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
                predicted_bad_probability=round(1 - favorable_probability, 12),
                outcome_matured_12m=True,
                bad_12m=not favorable,
                requested_credit=requested_credit,
            )
        )
    return tuple(rows)


def baseline_decisions(rows: Sequence[SimulatedApplicant]) -> tuple[bool, ...]:
    return tuple(
        row.credit_score >= 680 and row.predicted_bad_probability <= RISK_THRESHOLD
        for row in rows
    )


def tool_decisions(rows: Sequence[SimulatedApplicant]) -> tuple[bool, ...]:
    """Simulated policy: baseline plus a narrow, predeclared second-look rule."""

    return tuple(
        row.predicted_bad_probability <= RISK_THRESHOLD
        and (
            row.credit_score >= 680
            or (
                640 <= row.credit_score < 680
                and row.alternative_data_available
                and row.alternative_score >= 0.72
            )
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


def _decision_set_sha256(
    rows: Sequence[SimulatedApplicant], decisions: Sequence[bool]
) -> str:
    approved_ids = [
        row.applicant_id
        for row, decision in zip(rows, decisions, strict=True)
        if decision
    ]
    payload = json.dumps(approved_ids, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _id_set_sha256(ids: Sequence[int]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def _config_sha256(population_size: int) -> str:
    config = {
        "seed": SEED,
        "population_size": population_size,
        "risk_threshold": RISK_THRESHOLD,
        "assumed_average_credit": ASSUMED_AVERAGE_CREDIT,
        "baseline_credit_score_minimum": 680,
        "second_look_credit_score_minimum": 640,
        "second_look_credit_score_maximum_exclusive": 680,
        "second_look_alternative_score_minimum": 0.72,
    }
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    input_sha256 = _input_sha256(rows)
    baseline_ids = {
        row.applicant_id
        for row, decision in zip(rows, baseline, strict=True)
        if decision
    }
    tool_ids = {
        row.applicant_id
        for row, decision in zip(rows, tool, strict=True)
        if decision
    }
    added_ids = sorted(tool_ids - baseline_ids)
    canceled_ids = sorted(baseline_ids - tool_ids)
    baseline_gap = abs(baseline_metrics.selection_rate_difference)
    tool_gap = abs(tool_metrics.selection_rate_difference)
    expectations_passed = (
        tool_metrics.approvals - baseline_metrics.approvals == 350
        and math.isclose(baseline_gap, 0.12, abs_tol=1e-12)
        and math.isclose(tool_gap, 0.05, abs_tol=1e-12)
    )
    publication_passed = risk_passed and expectations_passed
    publication_reason = (
        "all_publication_gates_passed"
        if publication_passed
        else (
            "impact_risk_noninferiority_failed"
            if not risk_passed
            else "scenario_expectations_not_reproduced"
        )
    )
    approval_increment = tool_metrics.approvals - baseline_metrics.approvals
    credit_increment = approval_increment * ASSUMED_AVERAGE_CREDIT
    return BenchmarkResult(
        benchmark_id=BENCHMARK_ID,
        scenario_id=SCENARIO_ID,
        evidence_class="simulation_not_production_evidence",
        code_commit_basis=CODE_COMMIT_BASIS,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        evidence_status="simulation_not_production_evidence",
        seed=seed,
        population_size=population_size,
        input_sha256=input_sha256,
        input_file_sha256=input_sha256,
        config_sha256=_config_sha256(population_size),
        stable_row_ids_sha256=_id_set_sha256([row.applicant_id for row in rows]),
        run_command=RUN_COMMAND,
        repetitions=repetitions,
        baseline_median_seconds=float(baseline_runtime["median_seconds"]),
        tool_median_seconds=float(tool_runtime["median_seconds"]),
        runtime_statistics={"baseline": baseline_runtime, "tool": tool_runtime},
        covered_applicants=sum(row.alternative_data_available for row in rows),
        baseline=baseline_metrics,
        tool=tool_metrics,
        approval_increment=approval_increment,
        credit_increment=credit_increment,
        average_incremental_credit=float(ASSUMED_AVERAGE_CREDIT),
        policy_assumptions={
            "baseline_credit_score_minimum": 680,
            "second_look_credit_score_minimum": 640,
            "second_look_credit_score_maximum_exclusive": 680,
            "second_look_alternative_score_minimum": 0.72,
            "predicted_12m_bad_probability_maximum": RISK_THRESHOLD,
            "assumed_average_credit": ASSUMED_AVERAGE_CREDIT,
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
            "credit_increment": "approval_increment * assumed_average_credit",
            "average_incremental_credit": "assumed_average_credit",
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
            "rule": "risk_delta <= allowed_absolute_tolerance",
            "decision_risk_threshold": RISK_THRESHOLD,
            "outcome_definition": "bad_12m = 90+ DPD or charge-off within 12 months",
            "observation_window": "12 months after decision; only matured rows enter denominator",
            "formula": "sum(bad_12m for matured approved) / matured approved count",
            "allowed_absolute_tolerance": 0.0,
            "baseline_matured_approved_count": baseline_metrics.approvals,
            "tool_matured_approved_count": tool_metrics.approvals,
            "baseline_approved_bad_rate": baseline_metrics.approved_bad_rate,
            "tool_approved_bad_rate": tool_metrics.approved_bad_rate,
            "risk_delta": (
                tool_metrics.approved_bad_rate - baseline_metrics.approved_bad_rate
            ),
            "reason_code": (
                "impact_risk_noninferiority_passed"
                if risk_passed
                else "impact_risk_noninferiority_failed"
            ),
            "passed": risk_passed,
        },
        decision_set_digests={
            "baseline_approved_count": baseline_metrics.approvals,
            "baseline_approved_ids_sha256": _decision_set_sha256(rows, baseline),
            "tool_approved_count": tool_metrics.approvals,
            "tool_approved_ids_sha256": _decision_set_sha256(rows, tool),
            "added_approved_count": len(added_ids),
            "added_approved_ids_sha256": _id_set_sha256(added_ids),
            "canceled_approved_count": len(canceled_ids),
            "canceled_approved_ids_sha256": _id_set_sha256(canceled_ids),
        },
        scenario_expectations={
            "expected_incremental_approvals": 350,
            "actual_incremental_approvals": approval_increment,
            "expected_baseline_absolute_gap": 0.12,
            "actual_baseline_absolute_gap": baseline_gap,
            "expected_tool_absolute_gap": 0.05,
            "actual_tool_absolute_gap": tool_gap,
            "passed": expectations_passed,
        },
        publication_gate={
            "passed": publication_passed,
            "status": "passed" if publication_passed else "failed",
            "reason_code": publication_reason,
            "candidate_copy_status": (
                "publishable" if publication_passed else "locked_pending_evidence"
            ),
            "external_summary_candidate": (
                "在包含10,000名申请人的固定样本量化评估中，FairLendKit按显式流程"
                "工时假设将后处理工作量由80人时测算为32人时，预计减少60%；评估"
                f"覆盖情景由2,000人扩展至10,000人。固定逐行策略派生出{approval_increment}"
                f"个新增批准，按每笔8,000美元假设对应{credit_increment:,}美元授信机会。"
            ),
            "external_summary_footnote": (
                "结果基于固定样本、流程工时和逐行授信额度，尚未经过客户生产环境"
                "试点验证；当前候选文案因预设期望未复现而锁定，不得发布。"
            ),
        },
        data_provenance={
            "identity": "deterministic synthetic applicants generated in repository",
            "allowed_use": "simulation and test only",
            "customer_data": "none",
        },
        constraint_status="passed" if publication_passed else "failed",
        reason_code=publication_reason,
        disclaimer=(
            "Synthetic simulation only; not a pilot, customer outcome, production "
            "decision, causal estimate, or compliance conclusion."
        ),
    )
