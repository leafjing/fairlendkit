import json
from pathlib import Path

import pytest

from fairlendkit.metrics import (
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
