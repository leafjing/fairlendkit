"""Exhaustive frozen synthetic scenario registry for Paper 2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class ScenarioFamily(StrEnum):
    SELECTION = "selection"
    PERFORMANCE = "performance"


class Calibration(StrEnum):
    CALIBRATED = "calibrated"
    INTERCEPT_SHIFT = "intercept_shift"
    SLOPE_DISTORTION = "slope_distortion"


class Missingness(StrEnum):
    NONE = "none"
    MCAR = "mcar"
    MAR = "mar"
    MNAR = "mnar"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    family: ScenarioFamily
    comparison_n: int = 250
    reference_n: int = 250
    population_air: float = 1.0
    outcome_prevalence: float = 0.20
    decision_prevalence: float = 0.20
    population_auc: float = 0.70
    calibration: Calibration = Calibration.CALIBRATED
    missing_fraction: float = 0.0
    missingness: Missingness = Missingness.NONE
    minimum_group_size: int = 50
    bootstrap_resamples: int = 1_000
    minimum_valid_resamples: int = 800
    confidence_level: float = 0.95
    air_threshold: float = 0.8
    pair_id: str | None = None

    @property
    def effective_pair_id(self) -> str:
        return self.pair_id or self.scenario_id


def _add(target: dict[str, Scenario], scenario: Scenario) -> None:
    if scenario.scenario_id in target:
        if target[scenario.scenario_id] != scenario:
            raise ValueError(f"Conflicting scenario definition: {scenario.scenario_id}")
        return
    target[scenario.scenario_id] = scenario


def scenario_registry() -> dict[str, Scenario]:
    scenarios: dict[str, Scenario] = {}
    reg = Scenario("REG", ScenarioFamily.PERFORMANCE)
    _add(scenarios, reg)

    sizes = (("025", 25), ("050", 50), ("100", 100), ("250", 250), ("1000", 1000))
    airs = (("060", 0.60), ("079", 0.79), ("080", 0.80), ("081", 0.81), ("100", 1.00))
    for suffix, size in sizes:
        pairing = "PAIR-C1-N" if suffix in {"025", "1000"} else None
        _add(
            scenarios,
            Scenario(
                f"SEL-N{suffix}", ScenarioFamily.SELECTION, size, size, 0.80,
                pair_id=pairing,
            ),
        )
    for air_suffix, air in airs:
        _add(
            scenarios,
            Scenario(
                f"SEL-AIR{air_suffix}",
                ScenarioFamily.SELECTION,
                population_air=air,
            ),
        )
        for n_suffix, size in sizes:
            pairing = None
            if air_suffix == "080" and n_suffix in {"025", "1000"}:
                pairing = "PAIR-C1-N"
            elif air_suffix == "081" and n_suffix in {"050", "1000"}:
                pairing = "PAIR-C6-COVERAGE"
            _add(
                scenarios,
                Scenario(
                    f"SEL-AIR{air_suffix}-N{n_suffix}",
                    ScenarioFamily.SELECTION,
                    size,
                    size,
                    air,
                    pair_id=pairing,
                ),
            )

    for ratio_suffix, ratio in (("010", 0.10), ("025", 0.25), ("050", 0.50), ("100", 1.0)):
        for air_suffix, air in (("060", 0.60), ("080", 0.80), ("100", 1.0)):
            _add(
                scenarios,
                Scenario(
                    f"SEL-RATIO{ratio_suffix}-AIR{air_suffix}",
                    ScenarioFamily.SELECTION,
                    250,
                    int(250 / ratio),
                    air,
                ),
            )

    for suffix, value in (("001", 0.01), ("005", 0.05), ("020", 0.20), ("050", 0.50)):
        _add(scenarios, replace(reg, scenario_id=f"PERF-PREV{suffix}", outcome_prevalence=value))
        pairing = "PAIR-C3-DEC" if suffix in {"001", "050"} else None
        _add(
            scenarios,
            replace(
                reg,
                scenario_id=f"PERF-DEC{suffix}",
                decision_prevalence=value,
                pair_id=pairing,
            ),
        )
        for n_suffix, size in sizes:
            _add(
                scenarios,
                replace(
                    reg,
                    scenario_id=f"PERF-N{n_suffix}-PREV{suffix}",
                    comparison_n=size,
                    reference_n=size,
                    outcome_prevalence=value,
                ),
            )
            _add(
                scenarios,
                replace(
                    reg,
                    scenario_id=f"PERF-N{n_suffix}-DEC{suffix}",
                    comparison_n=size,
                    reference_n=size,
                    decision_prevalence=value,
                ),
            )
    for suffix, value in (("055", 0.55), ("070", 0.70), ("085", 0.85)):
        _add(scenarios, replace(reg, scenario_id=f"PERF-AUC{suffix}", population_auc=value))
        for prev_suffix, prevalence in (
            ("001", 0.01),
            ("005", 0.05),
            ("020", 0.20),
            ("050", 0.50),
        ):
            _add(
                scenarios,
                replace(
                    reg,
                    scenario_id=f"PERF-AUC{suffix}-PREV{prev_suffix}",
                    population_auc=value,
                    outcome_prevalence=prevalence,
                ),
            )
    for suffix, calibration in (
        ("CAL", Calibration.CALIBRATED),
        ("INT", Calibration.INTERCEPT_SHIFT),
        ("SLOPE", Calibration.SLOPE_DISTORTION),
    ):
        _add(scenarios, replace(reg, scenario_id=f"PERF-CAL{suffix}", calibration=calibration))

    _add(scenarios, replace(reg, scenario_id="MISS-NONE"))
    for mechanism, enum_value in (
        ("MCAR", Missingness.MCAR),
        ("MAR", Missingness.MAR),
        ("MNAR", Missingness.MNAR),
    ):
        for suffix, fraction in (("10", 0.10), ("30", 0.30)):
            pairing = (
                "PAIR-C5-MISSING"
                if suffix == "30" and mechanism in {"MCAR", "MNAR"}
                else None
            )
            _add(
                scenarios,
                replace(
                    reg,
                    scenario_id=f"MISS-{mechanism}{suffix}",
                    missing_fraction=fraction,
                    missingness=enum_value,
                    pair_id=pairing,
                ),
            )

    _add(
        scenarios,
        replace(
            reg,
            scenario_id="STRESS-N025-PREV001",
            comparison_n=25,
            reference_n=25,
            outcome_prevalence=0.01,
        ),
    )
    _add(
        scenarios,
        replace(
            reg,
            scenario_id="STRESS-N025-DEC001",
            comparison_n=25,
            reference_n=25,
            decision_prevalence=0.01,
        ),
    )
    _add(
        scenarios,
        replace(
            reg,
            scenario_id="STRESS-N025-MNAR30",
            comparison_n=25,
            reference_n=25,
            missing_fraction=0.30,
            missingness=Missingness.MNAR,
        ),
    )
    return dict(sorted(scenarios.items()))


def h2_scenario_units() -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (
            f"SEL-AIR{air}-N025",
            tuple(f"SEL-AIR{air}-N{size}" for size in ("050", "100", "250", "1000")),
        )
        for air in ("060", "079", "080", "081", "100")
    )
