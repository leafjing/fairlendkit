"""Generic preregistered statistical primitives without experiment execution."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping, Sequence

from scipy.stats import t as student_t

from fairlendkit.research.paper2.rng import analysis_rng


@dataclass(frozen=True)
class StudentizedMeanResult:
    n: int
    mean_difference: float
    mcse: float
    lower_95: float
    raw_p_value: float


def one_sided_studentized_mean(differences: Sequence[float]) -> StudentizedMeanResult:
    values = tuple(float(value) for value in differences)
    if len(values) < 2:
        raise ValueError("At least two paired differences are required.")
    if not all(isfinite(value) for value in values):
        raise ValueError("Paired differences must be finite.")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance == 0.0:
        raise ValueError("Zero-variance contrasts fail closed.")
    mcse = sqrt(variance / len(values))
    degrees = len(values) - 1
    statistic = mean / mcse
    return StudentizedMeanResult(
        n=len(values),
        mean_difference=mean,
        mcse=mcse,
        lower_95=mean - float(student_t.ppf(0.95, degrees)) * mcse,
        raw_p_value=float(student_t.sf(statistic, degrees)),
    )


def holm_adjust(raw_p_values: Mapping[str, float]) -> dict[str, float]:
    if not raw_p_values:
        raise ValueError("At least one p-value is required.")
    ordered = sorted(raw_p_values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (test_id, p_value) in enumerate(ordered):
        if not isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            raise ValueError("p-values must be finite and in [0, 1].")
        running = max(running, min(1.0, (count - index) * p_value))
        adjusted[test_id] = running
    return adjusted


@dataclass(frozen=True)
class H2Estimate:
    estimate: float | None
    lower: float | None
    upper: float | None
    valid_draws: int
    status: str


def h2_joint_bootstrap(
    deltas_by_air: Mapping[str, float | None],
    *,
    master_seed: int,
    draws: int = 2_000,
    minimum_valid_draws: int = 1_900,
) -> H2Estimate:
    expected_keys = ("060", "079", "080", "081", "100")
    if set(deltas_by_air) != set(expected_keys):
        raise ValueError("H2 input must contain exactly the five frozen AIR keys.")
    if draws != 2_000 or minimum_valid_draws != 1_900:
        raise ValueError("H2 draw count and minimum-valid threshold are frozen.")
    ordered = tuple((key, deltas_by_air[key]) for key in expected_keys)
    if any(value is not None and not isfinite(float(value)) for _, value in ordered):
        raise ValueError("H2 deltas must be finite or None.")
    available = tuple(value for _, value in ordered if value is not None)
    if not available:
        return H2Estimate(None, None, None, 0, "not_estimable")
    estimates: list[float] = []
    for draw_id in range(draws):
        rng = analysis_rng("h2_bootstrap", "H2", master_seed, draw_id)
        sampled: list[float] = []
        for _ in range(5):
            index = rng.randbelow(5)
            value = ordered[index][1]
            if value is not None:
                sampled.append(value)
        if sampled:
            estimates.append(sum(sampled) / len(sampled))
    if len(estimates) < minimum_valid_draws:
        return H2Estimate(None, None, None, len(estimates), "not_estimable")
    estimates.sort()
    return H2Estimate(
        estimate=sum(available) / len(available),
        lower=_type7(estimates, 0.025),
        upper=_type7(estimates, 0.975),
        valid_draws=len(estimates),
        status="estimated",
    )


def _type7(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Quantile input cannot be empty.")
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("Quantile values must be finite.")
    if not isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("Quantile probability must be finite and in [0, 1].")
    h = (len(values) - 1) * probability
    lower = int(h)
    upper = min(lower + 1, len(values) - 1)
    fraction = h - lower
    return values[lower] + fraction * (values[upper] - values[lower])
