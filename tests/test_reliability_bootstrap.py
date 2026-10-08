import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fairlendkit import AuditConfig
from fairlendkit.metrics import (
    MetricNameV2,
    NormalizedAuditData,
    RNG_NAME,
    ReliabilityState,
    assess_reliability,
    bootstrap_index_draws,
    bootstrap_interval,
    comparison_bootstrap_interval,
    calculate_group_metrics,
    collect_uncertainty,
    make_air_flags,
    type7_quantile,
)


def config(**changes):
    values = dict(
        outcome_column="outcome",
        score_column="score",
        population_definition="Completed applications",
        sampling_definition="All records",
        score_type="probability",
        dataset_version="data-v1",
        model_version="model-v1",
        data_as_of="2026-07-01T00:00:00Z",
        execution_timestamp="2026-07-02T00:00:00Z",
        favorable_label=1,
        score_direction="higher_is_more_favorable",
        protected_attributes=("group",),
        reference_groups={"group": "A"},
        allowed_groups={"group": ("A", "B")},
        favorable_decision_label=1,
        decision_threshold=0.5,
        threshold_operator="ge",
        minimum_group_size=1,
    )
    values.update(changes)
    return AuditConfig(**values)


def data():
    return NormalizedAuditData(
        favorable_outcome=(True, False, True, False),
        favorable_decision=(True, True, False, False),
        favorable_score=(0.9, 0.6, 0.4, 0.1),
        protected_values={"group": ("A", "A", "B", "B")},
    )


@pytest.fixture(scope="module")
def bootstrap_golden():
    path = Path(__file__).parent / "fixtures" / "bootstrap_golden.json"
    return json.loads(path.read_text())


def test_milestone_3_configuration_defaults_and_cross_field_validation():
    cfg = config()
    assert (cfg.bootstrap_seed, cfg.bootstrap_resamples) == (0, 1000)
    assert (cfg.minimum_valid_resamples, cfg.air_screening_threshold) == (800, 0.8)
    with pytest.raises(ValidationError, match="cannot exceed"):
        config(bootstrap_resamples=10, minimum_valid_resamples=11)


def test_reliability_matrix_and_comparison_inheritance():
    cfg = config(minimum_group_size=3)
    assessed, limitations = assess_reliability(
        calculate_group_metrics(data(), cfg), data(), cfg
    )
    overall = {item.calculated.metric: item for item in assessed[:9]}
    assert overall[MetricNameV2.SELECTION_RATE].reliability == ReliabilityState.RELIABLE
    assert overall[MetricNameV2.ACCURACY].limitation_codes == (
        "severe_outcome_imbalance",
    )
    precision = overall[MetricNameV2.PRECISION]
    assert precision.limitation_codes == (
        "severe_outcome_imbalance",
        "sparse_decision_support",
    )
    air = next(item for item in assessed if item.calculated.metric == MetricNameV2.ADVERSE_IMPACT_RATIO)
    assert air.reliability == ReliabilityState.UNRELIABLE
    assert air.limitation_codes == ("small_group",)
    assert make_air_flags(assessed, cfg) == ()
    assert all(item.affected_metric_keys for item in limitations)


def test_air_flag_requires_reliable_sources_and_strict_threshold():
    cfg = config(minimum_group_size=1)
    assessed, _ = assess_reliability(calculate_group_metrics(data(), cfg), data(), cfg)
    flags = make_air_flags(assessed, cfg)
    assert len(flags) == 1
    assert flags[0].observed_value == 0.0
    assert flags[0].threshold == 0.8


def test_undefined_metrics_do_not_receive_reliability_limitations():
    empty_group_data = NormalizedAuditData(
        favorable_outcome=(True, False),
        favorable_decision=(True, False),
        favorable_score=(0.9, 0.1),
        protected_values={"group": ("A", "A")},
    )
    cfg = config(minimum_group_size=3)
    assessed, _ = assess_reliability(
        calculate_group_metrics(empty_group_data, cfg), empty_group_data, cfg
    )
    undefined = [item for item in assessed if not item.calculated.value.is_defined]
    assert undefined
    assert all(item.limitation_codes == () for item in undefined)
    assert all(item.reliability in {ReliabilityState.UNDEFINED, ReliabilityState.NOT_APPLICABLE} for item in undefined)


def test_sha256_counter_rng_golden_first_three_draws(bootstrap_golden):
    assert RNG_NAME == bootstrap_golden["rng"]
    for role, draws in bootstrap_golden["first_three_draws"].items():
        assert bootstrap_index_draws(
            4,
            3,
            seed=bootstrap_golden["seed"],
            metric_key=bootstrap_golden["scope_metric_key"],
            stream_role=role,
        ) == tuple(tuple(draw) for draw in draws)


def test_type7_interval_and_insufficient_valid_draws(bootstrap_golden):
    assert type7_quantile((0.0, 10.0, 20.0, 30.0), 0.25) == pytest.approx(7.5)
    interval = bootstrap_interval(
        4,
        lambda indices: sum(indices) / len(indices),
        seed=7,
        metric_key="overall.selection_rate",
        resamples=10,
        minimum_valid_resamples=10,
        confidence_level=0.8,
    )
    assert interval is not None
    expected = bootstrap_golden["scope_interval"]
    assert interval.valid_resamples == expected["valid_resamples"]
    assert interval.lower == pytest.approx(expected["lower"])
    assert interval.upper == pytest.approx(expected["upper"])
    assert bootstrap_interval(
        4,
        lambda indices: None,
        seed=7,
        metric_key="overall.selection_rate",
        resamples=5,
        minimum_valid_resamples=1,
        confidence_level=0.95,
    ) is None


def test_comparison_bootstrap_uses_independent_side_streams(bootstrap_golden):
    expected = bootstrap_golden["comparison_interval"]
    interval = comparison_bootstrap_interval(
        4,
        4,
        lambda comparison, reference: (
            sum(comparison) / len(comparison) - sum(reference) / len(reference)
        ),
        seed=7,
        metric_key=expected["metric_key"],
        resamples=20,
        minimum_valid_resamples=20,
        confidence_level=0.8,
    )

    assert interval is not None
    assert interval.valid_resamples == expected["valid_resamples"]
    assert interval.lower == pytest.approx(expected["lower"])
    assert interval.upper == pytest.approx(expected["upper"])


def test_insufficient_resamples_add_limitation_without_changing_point_reliability():
    cfg = config(minimum_group_size=1)
    assessed, _ = assess_reliability(calculate_group_metrics(data(), cfg), data(), cfg)
    selection = next(
        item
        for item in assessed
        if item.calculated.key == "overall.selection_rate"
    )

    intervals, limitations = collect_uncertainty(
        assessed, {selection.calculated.key: None}
    )

    assert intervals == ()
    assert selection.reliability == ReliabilityState.RELIABLE
    assert limitations[0].code == "insufficient_valid_resamples"
    assert limitations[0].affected_metric_keys == ("overall.selection_rate",)
