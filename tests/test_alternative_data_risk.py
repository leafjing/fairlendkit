import pytest
from pydantic import ValidationError

from fairlendkit.alternative_data import (
    RiskEntity,
    RiskEvaluationConfig,
    build_risk_diagnostic_release,
)
from fairlendkit.alternative_data.risk import _evaluate_risk_diagnostics


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
    with pytest.raises(ValueError, match="ad_label_immature"):
        _evaluate_risk_diagnostics(
            (RiskEntity(entity_id="x", score=0.5, outcome="bad", label_mature=False),),
            configuration(),
        )


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
    assert first.calibration_slope.reason in {"separation", "singular_or_separated", "non_convergence"}


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

    supported = tuple(
        entity(f"entity-{index}", 0.9 if index % 2 else 0.1, "bad" if index % 2 else "good")
        for index in range(10)
    )
    published = build_risk_diagnostic_release(supported, configuration())
    assert published.state == "published"
    assert published.entity_count == 10
    assert published.diagnostics is not None
