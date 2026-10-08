"""Hand-calculated tests for preregistered generic analysis primitives."""

import pytest

from fairlendkit.research.paper2.statistics import (
    h2_joint_bootstrap,
    holm_adjust,
    one_sided_studentized_mean,
)


def test_studentized_mean_reports_registered_direction_and_components():
    result = one_sided_studentized_mean((1.0, 2.0, 3.0, 4.0))

    assert result.n == 4
    assert result.mean_difference == 2.5
    assert result.mcse == pytest.approx(0.6454972243679028)
    assert result.lower_95 < result.mean_difference
    assert 0.0 < result.raw_p_value < 0.05


def test_studentized_mean_fails_closed_for_invalid_denominator_or_variance():
    with pytest.raises(ValueError, match="two"):
        one_sided_studentized_mean((1.0,))
    with pytest.raises(ValueError, match="Zero-variance"):
        one_sided_studentized_mean((1.0, 1.0))
    for non_finite in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            one_sided_studentized_mean((1.0, non_finite))


def test_holm_is_deterministic_for_ties_and_monotone():
    adjusted = holm_adjust({"C2": 0.01, "C1": 0.01, "C3": 0.04})

    assert list(adjusted) == ["C1", "C2", "C3"]
    assert adjusted == {"C1": 0.03, "C2": 0.03, "C3": 0.04}


def test_holm_rejects_empty_or_non_finite_inputs():
    with pytest.raises(ValueError, match="one"):
        holm_adjust({})
    for non_finite in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            holm_adjust({"C1": non_finite})


def test_h2_joint_bootstrap_is_deterministic_and_fails_closed():
    values = {"060": 0.1, "079": 0.2, "080": 0.3, "081": 0.4, "100": 0.5}
    first = h2_joint_bootstrap(values, master_seed=20261008)
    second = h2_joint_bootstrap(values, master_seed=20261008)

    assert first == second
    assert first.status == "estimated"
    assert first.estimate == pytest.approx(0.3)
    unavailable = h2_joint_bootstrap(
        {key: None for key in values}, master_seed=20261008
    )
    assert unavailable.status == "not_estimable"
    assert unavailable.lower is None


def test_h2_rejects_non_finite_values_keys_and_unfrozen_draw_parameters():
    values = {"060": 0.1, "079": 0.2, "080": 0.3, "081": 0.4, "100": 0.5}
    with pytest.raises(ValueError, match="five frozen"):
        h2_joint_bootstrap({**values, "extra": 0.0}, master_seed=20261008)
    with pytest.raises(ValueError, match="five frozen"):
        h2_joint_bootstrap({key: value for key, value in values.items() if key != "060"}, master_seed=20261008)
    with pytest.raises(ValueError, match="finite"):
        h2_joint_bootstrap({**values, "060": float("nan")}, master_seed=20261008)
    with pytest.raises(ValueError, match="frozen"):
        h2_joint_bootstrap(values, master_seed=20261008, draws=1_999)
    with pytest.raises(ValueError, match="frozen"):
        h2_joint_bootstrap(values, master_seed=20261008, minimum_valid_draws=1_899)
