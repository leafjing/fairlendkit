import pytest
from pydantic import ValidationError

from fairlendkit.alternative_data import (
    AggregateReportRelease,
    RiskEntity,
    RiskEvaluationConfig,
    build_risk_diagnostic_release,
)
from fairlendkit.alternative_data.risk import _calibration_slope, _evaluate_risk_diagnostics
from fairlendkit.metrics.bootstrap import RNG_NAME, bootstrap_index_draws


def configuration(**overrides):
    values = {
        "favorable_outcome_labels": ("good",),
        "unfavorable_outcome_labels": ("bad",),
        "score_type": "probability",
        "score_target": "unfavorable",
        "score_band_edges": (0.25, 0.5, 0.75),
        "top_fractions": (0.5, 0.75, 1.0),
        "calibration_epsilon": 1e-6,
        "bootstrap_seed": 7,
        "bootstrap_resamples": 20,
        "minimum_valid_resamples": 20,
    }
    values.update(overrides)
    return RiskEvaluationConfig(**values)


def entity(identity, score, outcome, weight=1.0):
    return RiskEntity(entity_id=identity, score=score, outcome=outcome, weight=weight)


def test_weighted_oracle_bands_ks_auc_gini_and_lift_ties():
    result = _evaluate_risk_diagnostics(
        (
            entity("a", 0.9, "bad", 2),
            entity("b", 0.8, "good", 1),
            entity("c", 0.8, "bad", 1),
            entity("zero", 0.7, "bad", 0),
        ),
        configuration(),
    )
    assert result.raw_entity_count == 4
    assert result.normalized_weight_total == 2
    assert result.bad_entity_count == 2
    assert result.good_entity_count == 1
    assert result.zero_weight_excluded_count == 1
    assert len(result.bands) == 4
    assert result.bands[0].entity_count == 0
    assert result.bands[0].observed_bad_rate.state == "unavailable"
    assert result.ks.value == 2 / 3
    assert result.ks_maximizing_scores == (0.9,)
    assert result.ks_canonical_threshold == 0.9
    assert result.risk_auc.value == pytest.approx(5 / 6)
    assert result.gini.value == pytest.approx(2 / 3)
    half, crossing, whole = result.lift_capture
    assert half.achieved_weight_fraction == 0.5
    assert half.entity_count == 1
    assert crossing.achieved_weight_fraction == 1
    assert crossing.entity_count == 3
    assert crossing.bad_capture.value == 1
    assert crossing.selected_bad_rate.value == 0.75
    assert crossing.lift.value == 1
    assert whole == crossing.model_copy(update={"requested_fraction": 1.0})
    assert result.bootstrap_valid_resamples == 20
    assert result.reliable is True
    assert result.trace.outcome_definition == "explicit observed credit outcome"
    assert result.trace.score_type == "probability"
    assert result.trace.bootstrap_seed == 7
    assert result.trace.bootstrap_resamples == 20
    assert result.trace.minimum_valid_resamples == 20
    assert result.trace.minimum_total_entities == 1
    assert result.trace.minimum_bad_entities == 1
    assert result.trace.minimum_good_entities == 1
    assert result.trace.minimum_report_cell_count == 10
    assert result.trace.weight_normalization == "divide_by_maximum_positive_weight"
    assert result.trace.rng_identity == RNG_NAME
    assert {item.metric_key for item in result.bootstrap} >= {
        "ks", "risk_auc", "gini", "brier_score", "calibration_in_the_large",
        "band.0.observed_bad_rate", "top.0.5.bad_capture", "top.0.75.lift",
    }
    evidence = {item.metric_key: item for item in result.bootstrap}
    assert evidence["ks"].valid_resamples == 20 and evidence["ks"].reliable
    assert evidence["band.0.observed_bad_rate"].valid_resamples == 0
    assert evidence["band.0.observed_bad_rate"].reliable is False


def test_direction_probability_calibration_and_ranking_applicability():
    rows = (
        entity("g1", 0.9, "good"),
        entity("g2", 0.8, "good"),
        entity("b1", 0.2, "bad"),
        entity("b2", 0.1, "bad"),
    )
    probability = _evaluate_risk_diagnostics(
        rows, configuration(score_target="favorable", score_band_edges=(0.15, 0.5, 0.85))
    )
    assert probability.risk_auc.value == 1
    assert probability.gini.value == 1
    assert probability.brier_score.value == pytest.approx(0.025)
    assert probability.calibration_in_the_large.value == pytest.approx(0)

    ranking = _evaluate_risk_diagnostics(
        rows,
        configuration(score_type="ranking", score_target="favorable"),
    )
    assert ranking.brier_score.state == "not_applicable"
    assert ranking.calibration_in_the_large.state == "not_applicable"
    assert ranking.calibration_slope.state == "not_applicable"
    assert ranking.risk_auc.value == 1


def test_typed_outcomes_entity_uniqueness_and_input_gates_fail_closed():
    with pytest.raises(ValidationError):
        configuration(favorable_outcome_labels=("same",), unfavorable_outcome_labels=("same",))
    typed = configuration(favorable_outcome_labels=(True,), unfavorable_outcome_labels=(1,))
    assert typed.favorable_outcome_labels == (True,)
    assert typed.unfavorable_outcome_labels == (1,)
    with pytest.raises(ValueError, match="ad_unrecognized_outcome_label"):
        _evaluate_risk_diagnostics((entity("x", 0.5, "third"),), configuration())
    with pytest.raises(ValueError, match="one row per entity"):
        _evaluate_risk_diagnostics(
            (entity("x", 0.2, "good"), entity("x", 0.8, "bad")), configuration()
        )
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        _evaluate_risk_diagnostics((entity("x", 1.1, "bad"),), configuration())
    with pytest.raises(ValidationError):
        RiskEntity(entity_id="x", score=0.5, outcome="bad", weight=-1)
    excluded = _evaluate_risk_diagnostics(
        (
            RiskEntity(entity_id="x", score=0.5, outcome="bad", label_mature=False),
            RiskEntity(entity_id="y", score=0.6, outcome="bad", censored=True),
        ),
        configuration(),
    )
    assert excluded.eligible_entity_count == 0
    assert excluded.immature_excluded_count == 1
    assert excluded.censored_excluded_count == 1
    assert excluded.ks.state == "unavailable"
    assert excluded.brier_score.state == "unavailable"


def test_one_class_separation_empty_bands_and_determinism():
    one_class = _evaluate_risk_diagnostics(
        (entity("a", 0.2, "good"), entity("b", 0.4, "good")), configuration()
    )
    assert one_class.ks.state == "unavailable"
    assert one_class.risk_auc.state == "unavailable"
    assert one_class.calibration_slope.state == "unavailable"
    assert one_class.reliable is False

    separated_rows = (
        entity("a", 0.01, "good"), entity("b", 0.02, "good"),
        entity("c", 0.98, "bad"), entity("d", 0.99, "bad"),
    )
    first = _evaluate_risk_diagnostics(separated_rows, configuration())
    second = _evaluate_risk_diagnostics(tuple(reversed(separated_rows)), configuration())
    assert first == second
    assert first.calibration_slope.state == "unavailable"
    assert first.calibration_slope.reason == "separation"

    singular = _calibration_slope(
        (
            ("a", 0.2, 0, 1e-30),
            ("b", 0.5, 1, 1e-30),
            ("c", 0.8, 0, 1e-30),
        ),
        1e-6,
    )
    assert singular.reason == "singular"
    non_converged = _calibration_slope(
        (
            ("a", 0.2, 0, 1.0),
            ("b", 0.5, 1, 1.0),
            ("c", 0.8, 0, 1.0),
        ),
        1e-6,
        max_iterations=0,
    )
    assert non_converged.reason == "non_convergence"

    zero_weight = _evaluate_risk_diagnostics(
        (entity("z1", 0.2, "good", 0), entity("z2", 0.8, "bad", 0)),
        configuration(),
    )
    assert zero_weight.normalized_weight_total == 0
    assert zero_weight.ks.state == "unavailable"
    assert zero_weight.brier_score.reason == "zero_total_weight"


def test_ks_preserves_all_maximizing_thresholds_and_canonical_smallest():
    result = _evaluate_risk_diagnostics(
        (
            entity("bad-high", 0.9, "bad"),
            entity("bad-mid", 0.8, "bad"),
            entity("good-mid", 0.8, "good"),
            entity("good-low", 0.7, "good"),
        ),
        configuration(),
    )
    assert result.ks.value == 0.5
    assert result.ks_maximizing_scores == (0.9, 0.8)
    assert result.ks_canonical_threshold == 0.8


def test_ad3_bootstrap_counter_stream_golden_draws():
    assert bootstrap_index_draws(
        3, 4, seed=7, metric_key="ad3.entity_stratified",
        stream_role="comparison",
    ) == ((0, 1, 2), (2, 0, 0), (0, 2, 2), (1, 2, 0))
    assert bootstrap_index_draws(
        2, 4, seed=7, metric_key="ad3.entity_stratified",
        stream_role="reference",
    ) == ((1, 0), (0, 0), (1, 1), (1, 1))


def test_public_risk_release_suppresses_sparse_diagnostics_and_publishes_supported():
    sparse = build_risk_diagnostic_release(
        (entity("secret-a", 0.8, "bad"), entity("secret-b", 0.2, "good")),
        configuration(),
    )
    assert sparse.state == "suppressed"
    assert sparse.entity_count is None
    assert sparse.diagnostics is None
    assert sparse.count_bucket == "0..9"
    serialized = sparse.model_dump_json()
    assert "secret-a" not in serialized and "secret-b" not in serialized
    with pytest.raises(ValidationError):
        AggregateReportRelease.model_validate(sparse.model_dump())

    supported = tuple(
        entity(
            f"entity-{index}",
            0.1 if index == 0 else 0.9,
            "bad" if index % 2 else "good",
        )
        for index in range(20)
    )
    protected = build_risk_diagnostic_release(supported, configuration())
    assert protected.state == "published" and protected.entity_count == 20
    assert protected.diagnostics is not None
    diagnostics = protected.diagnostics
    low, _, _, high = diagnostics.bands
    assert low.state == "suppressed" and low.count_bucket == "0..9"
    assert high.state == "suppressed" and high.count_bucket == "hidden"
    assert high.reason_code == "ad_complementary_suppression"
    assert diagnostics.bad_entity_count is None
    assert diagnostics.good_entity_count is None
    assert diagnostics.ks.reason == "ad_complementary_suppression"
    assert all(item.state == "suppressed" for item in diagnostics.lift_capture)
    assert all(item.state == "suppressed" for item in diagnostics.bootstrap)
    assert next(
        item for item in diagnostics.bootstrap
        if item.metric_key == "band.3.observed_bad_rate"
    ).reason_code == "ad_complementary_suppression"
    serialized = protected.model_dump_json()
    for exact in ('"entity_count":19', '"normalized_weight":19.0'):
        assert exact not in serialized

    repeated = build_risk_diagnostic_release(
        supported, configuration(), previous_release=protected
    )
    assert repeated == protected
    assert repeated.diagnostics is not None
    assert all(item.state == "suppressed" for item in repeated.diagnostics.bands)
    assert all(item.state == "suppressed" for item in repeated.diagnostics.lift_capture)

    changed = list(supported)
    changed[0] = changed[0].model_copy(update={"censored": True})
    with pytest.raises(ValueError, match="previously published exact value"):
        build_risk_diagnostic_release(
            tuple(changed), configuration(), previous_release=protected
        )


def test_previous_release_locks_overall_outcomes_bands_and_lift_counts():
    rows = tuple(
        entity(
            f"band-{band}-{index}", score,
            "bad" if index % 2 else "good",
        )
        for band, score in enumerate((0.1, 0.35, 0.6, 0.9))
        for index in range(10)
    )
    previous = build_risk_diagnostic_release(rows, configuration())
    assert previous.state == "published" and previous.diagnostics is not None
    assert previous.entity_count == 40
    assert previous.diagnostics.bad_entity_count == 20
    assert previous.diagnostics.good_entity_count == 20
    assert [item.entity_count for item in previous.diagnostics.bands] == [10] * 4
    assert [item.entity_count for item in previous.diagnostics.lift_capture] == [20, 30, 40]

    mutations = []
    mutations.append(rows + (entity("added", 0.1, "good"),))

    outcome_changed = list(rows)
    outcome_changed[0] = outcome_changed[0].model_copy(update={"outcome": "bad"})
    mutations.append(tuple(outcome_changed))

    band_changed = list(rows)
    band_changed[0] = band_changed[0].model_copy(update={"score": 0.35})
    mutations.append(tuple(band_changed))

    lift_changed = list(rows)
    lift_changed[-1] = lift_changed[-1].model_copy(update={"weight": 100.0})
    mutations.append(tuple(lift_changed))

    for current in mutations:
        with pytest.raises(ValueError, match="previously published exact value"):
            build_risk_diagnostic_release(
                current, configuration(), previous_release=previous
            )
