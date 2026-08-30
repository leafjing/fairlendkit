import json
from pathlib import Path

import pytest

from fairlendkit.metrics import (
    MetricValue,
    accuracy,
    adverse_impact_ratio,
    brier_score,
    demographic_parity_difference,
    equal_opportunity_difference,
    false_negative_rate,
    false_positive_rate,
    selection_rate,
    true_positive_rate,
)


@pytest.fixture(scope="module")
def hand_fixture():
    path = Path(__file__).parent / "fixtures" / "hand_calculated_metrics.json"
    return json.loads(path.read_text())


def test_hand_calculated_group_metrics(hand_fixture):
    results = {}
    for group_name in ("reference", "comparison"):
        group = hand_fixture[group_name]
        outcome = group["favorable_outcome"]
        decision = group["favorable_decision"]
        results[group_name] = {
            "selection_rate": selection_rate(decision),
            "true_positive_rate": true_positive_rate(outcome, decision),
            "false_positive_rate": false_positive_rate(outcome, decision),
            "false_negative_rate": false_negative_rate(outcome, decision),
        }
        for metric_name, result in results[group_name].items():
            assert result.value == group[metric_name]

    expected = hand_fixture["comparison_to_reference"]
    assert adverse_impact_ratio(
        results["comparison"]["selection_rate"],
        results["reference"]["selection_rate"],
    ).value == expected["adverse_impact_ratio"]
    assert demographic_parity_difference(
        results["comparison"]["selection_rate"],
        results["reference"]["selection_rate"],
    ).value == expected["demographic_parity_difference"]
    assert equal_opportunity_difference(
        results["comparison"]["true_positive_rate"],
        results["reference"]["true_positive_rate"],
    ).value == expected["equal_opportunity_difference"]


def test_approval_rate_is_selection_rate_when_approval_is_favorable_decision():
    result = selection_rate([True, False, True, False])

    assert result.value == 0.5
    assert result.numerator == 2
    assert result.denominator == 4


def test_zero_denominator_is_undefined_not_zero():
    undefined = true_positive_rate([False, False], [False, False])
    defined_zero = false_positive_rate([False, False], [False, False])

    assert undefined.value is None
    assert undefined.undefined_reason == "no favorable outcomes or positive weight"
    assert defined_zero.value == 0.0
    assert defined_zero.undefined_reason is None


def test_air_is_undefined_when_reference_selection_rate_is_zero():
    comparison = selection_rate([True, False])
    reference = selection_rate([False, False])

    result = adverse_impact_ratio(comparison, reference)

    assert result.value is None
    assert result.denominator == 0.0
    assert result.undefined_reason == "reference selection rate is zero"


def test_reference_group_reversal_changes_direction():
    comparison = selection_rate([True, False])
    reference = selection_rate([True, True])

    assert adverse_impact_ratio(comparison, reference).value == 0.5
    assert adverse_impact_ratio(reference, comparison).value == 2.0
    assert demographic_parity_difference(comparison, reference).value == -0.5
    assert demographic_parity_difference(reference, comparison).value == 0.5


def test_favorable_label_reversal_changes_normalized_metrics():
    outcome = [True, True, False, False]
    decision = [True, True, True, False]

    original = true_positive_rate(outcome, decision)
    reversed_result = true_positive_rate(
        [not value for value in outcome], decision
    )

    assert original.value == 1.0
    assert reversed_result.value == 0.5


def test_performance_and_calibration_contracts():
    assert accuracy([True, False], [True, True]).value == 0.5
    assert brier_score([True, False], [0.8, 0.3]).value == pytest.approx(0.065)


def test_metric_inputs_require_normalized_booleans():
    with pytest.raises(TypeError, match="normalized boolean"):
        selection_rate([1, 0])


def test_hand_calculated_weighted_selection_rate(hand_fixture):
    weighted = hand_fixture["weighted"]

    result = selection_rate(weighted["favorable_decision"], weighted["weights"])

    assert result.value == weighted["selection_rate"]
    assert result.numerator == pytest.approx(1 / 3)
    assert result.denominator == pytest.approx(4 / 3)


def test_extreme_finite_weights_are_scaled_without_overflow():
    result = selection_rate([True, False], [1e308, 1e308])

    assert result.value == 0.5
    assert result.numerator == 1.0
    assert result.denominator == 2.0


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
def test_metric_value_rejects_non_finite_values(invalid):
    with pytest.raises(ValueError, match="defined metric value must be finite"):
        MetricValue(invalid, 1.0, 1.0)


def test_metric_value_rejects_non_finite_evidence():
    with pytest.raises(ValueError, match="metric evidence must be finite"):
        MetricValue(0.5, 1.0, float("inf"))


def test_metric_value_rejects_undefined_state_without_reason():
    with pytest.raises(ValueError, match="requires undefined_reason"):
        MetricValue(None, None, None)


@pytest.mark.parametrize(
    "disparity",
    [adverse_impact_ratio, demographic_parity_difference],
)
@pytest.mark.parametrize("invalid_rate", [-0.01, 1.01, 2.0])
def test_selection_disparities_reject_out_of_range_rates(disparity, invalid_rate):
    invalid = MetricValue(invalid_rate, invalid_rate, 1.0)
    valid = MetricValue(0.5, 0.5, 1.0)

    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        disparity(invalid, valid)


def test_equal_opportunity_difference_rejects_out_of_range_rate():
    invalid = MetricValue(1.1, 1.1, 1.0)
    valid = MetricValue(0.5, 0.5, 1.0)

    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        equal_opportunity_difference(invalid, valid)
