import pytest

from fairlendkit import AuditConfig
from fairlendkit.metrics import (
    AuditScope,
    MetricNameV2,
    NormalizedAuditData,
    calculate_group_metrics,
    canonical_metric_key,
    canonical_typed_token,
    scope_key,
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
        allowed_groups={"group": ("B", "A", "C")},
        favorable_decision_label=1,
        decision_threshold=0.5,
        threshold_operator="ge",
        minimum_group_size=1,
    )
    values.update(changes)
    return AuditConfig(**values)


def data():
    return NormalizedAuditData(
        favorable_outcome=(True, True, False, False),
        favorable_decision=(True, False, True, False),
        favorable_score=(0.9, 0.8, 0.4, 0.1),
        protected_values={"group": ("A", "B", "A", "B")},
    )


def test_canonical_typed_tokens_are_collision_free_and_match_contract_example():
    assert canonical_typed_token("A") == "str-224122"
    assert canonical_typed_token(1) == "int-31"
    assert canonical_typed_token(True) == "bool-74727565"
    assert canonical_typed_token(1) != canonical_typed_token(True)


def test_scope_key_equality_and_hash_are_type_sensitive():
    scopes = {
        scope_key(AuditScope((("group", True),))),
        scope_key(AuditScope((("group", 1),))),
        scope_key(AuditScope((("group", "1"),))),
    }

    assert len(scopes) == 3
    assert scope_key(AuditScope((("group", True),))).attributes == (
        ("group", "bool", "true"),
    )
    assert scope_key(AuditScope((("group", 1),))).attributes == (
        ("group", "int", "1"),
    )
    assert scope_key(AuditScope((("group", "1"),))).attributes == (
        ("group", "str", '"1"'),
    )


def test_canonical_metric_keys_cover_overall_group_and_comparison():
    group_a = AuditScope((("group", "A"),))
    group_b = AuditScope((("group", "B"),))

    assert canonical_metric_key(
        MetricNameV2.SELECTION_RATE, group=AuditScope.overall()
    ) == "overall.selection_rate"
    assert canonical_metric_key(
        MetricNameV2.SELECTION_RATE, group=group_a
    ) == "group.str-2267726f757022.str-224122.selection_rate"
    assert canonical_metric_key(
        MetricNameV2.ADVERSE_IMPACT_RATIO,
        comparison_group=group_b,
        reference_group=group_a,
    ) == (
        "comparison.str-2267726f757022.str-224222.vs.str-224122."
        "adverse_impact_ratio"
    )


def test_group_orchestration_is_canonical_and_emits_configured_empty_groups():
    results = calculate_group_metrics(data(), config())

    assert len(results) == 46  # 9 overall + 3*9 groups + 2*5 comparisons
    assert [item.key for item in results[:9]] == [
        f"overall.{name}"
        for name in (
            "selection_rate",
            "denial_rate",
            "accuracy",
            "precision",
            "true_positive_rate",
            "false_positive_rate",
            "false_negative_rate",
            "brier_score",
            "roc_auc",
        )
    ]
    group_keys = [item.key for item in results[9:36:9]]
    assert ["str-224122" in group_keys[0], "str-224222" in group_keys[1], "str-224322" in group_keys[2]] == [True, True, True]
    empty_key = scope_key(AuditScope((("group", "C"),)))
    empty_group_metrics = [
        item
        for item in results
        if item.group is not None and scope_key(item.group) == empty_key
    ]
    assert len(empty_group_metrics) == 9
    assert {item.sample_count for item in empty_group_metrics} == {0}
    assert {item.value.undefined_reason for item in empty_group_metrics} == {
        "empty_population",
        "no_favorable_decisions",
        "no_favorable_outcomes",
        "no_unfavorable_outcomes",
    }


def test_comparison_direction_alias_and_component_metrics_are_correct():
    results = calculate_group_metrics(data(), config())
    by_key = {item.key: item for item in results}
    prefix = "comparison.str-2267726f757022.str-224222.vs.str-224122"

    assert by_key[f"{prefix}.selection_rate_difference"].value.value == -1.0
    assert by_key[f"{prefix}.demographic_parity_difference"].value == by_key[
        f"{prefix}.selection_rate_difference"
    ].value
    assert by_key[f"{prefix}.adverse_impact_ratio"].value.value == 0.0
    assert by_key[f"{prefix}.equal_opportunity_difference"].value.value == -1.0
    assert by_key[f"{prefix}.equalized_odds_gap"].value.value == 1.0


def test_mapping_and_row_order_do_not_change_order_or_values():
    first = calculate_group_metrics(data(), config())
    reversed_data = NormalizedAuditData(
        favorable_outcome=tuple(reversed(data().favorable_outcome)),
        favorable_decision=tuple(reversed(data().favorable_decision)),
        favorable_score=tuple(reversed(data().favorable_score)),
        protected_values={"group": tuple(reversed(data().protected_values["group"]))},
    )
    second = calculate_group_metrics(
        reversed_data,
        config(allowed_groups={"group": ("C", "A", "B")}),
    )

    assert [item.key for item in first] == [item.key for item in second]
    assert [item.value for item in first] == [item.value for item in second]


def test_multiple_attributes_are_independent_and_sorted_by_attribute():
    cfg = config(
        protected_attributes=("zeta", "alpha"),
        allowed_groups={"zeta": ("x", "y"), "alpha": (0, 1)},
        reference_groups={"zeta": "x", "alpha": 0},
    )
    normalized = NormalizedAuditData(
        favorable_outcome=(True, False),
        favorable_decision=(True, False),
        favorable_score=(0.8, 0.2),
        protected_values={"zeta": ("x", "y"), "alpha": (0, 1)},
    )

    results = calculate_group_metrics(normalized, cfg)
    first_group = results[9].group

    assert first_group is not None
    assert scope_key(first_group) == scope_key(
        AuditScope((("alpha", 0),))
    )
    assert len(results) == 55  # 9 overall + 4*9 groups + 2*5 comparisons


def test_ranking_score_marks_brier_not_applicable_without_affecting_auc():
    results = calculate_group_metrics(data(), config(score_type="ranking"))
    overall = {item.metric: item for item in results[:9]}

    assert overall[MetricNameV2.BRIER_SCORE].value.undefined_reason == "metric_not_applicable"
    assert overall[MetricNameV2.ROC_AUC].value.value == 1.0


def test_group_orchestration_rejects_mismatched_protected_inputs():
    with pytest.raises(ValueError, match="must match configured"):
        calculate_group_metrics(
            NormalizedAuditData(
                favorable_outcome=(True,),
                favorable_decision=(True,),
                favorable_score=(0.9,),
                protected_values={"other": ("A",)},
            ),
            config(),
        )


def test_group_orchestration_rejects_unknown_typed_group_values():
    with pytest.raises(ValueError, match="must belong to configured allowed groups"):
        calculate_group_metrics(
            NormalizedAuditData(
                favorable_outcome=(True,),
                favorable_decision=(True,),
                favorable_score=(0.9,),
                protected_values={"group": ("unknown",)},
            ),
            config(),
        )


def test_boolean_and_integer_groups_do_not_overwrite_comparison_sources():
    cfg = config(
        allowed_groups={"group": (True, 1, "1")},
        reference_groups={"group": True},
    )
    normalized = NormalizedAuditData(
        favorable_outcome=(True, False, True),
        favorable_decision=(True, False, True),
        favorable_score=(0.9, 0.1, 0.8),
        protected_values={"group": (True, 1, "1")},
    )

    results = calculate_group_metrics(normalized, cfg)
    differences = [
        item
        for item in results
        if item.metric == MetricNameV2.SELECTION_RATE_DIFFERENCE
    ]
    integer_key = scope_key(AuditScope((("group", 1),)))
    difference = next(
        item
        for item in differences
        if item.comparison_group is not None
        and scope_key(item.comparison_group) == integer_key
    )

    assert len(differences) == 2
    assert len({item.key for item in differences}) == 2
    group_selection_rates = [
        item
        for item in results
        if item.metric == MetricNameV2.SELECTION_RATE and item.group is not None
        and item.group.attributes != (("__scope__", "overall"),)
    ]
    assert len(group_selection_rates) == 3
    assert len({scope_key(item.group) for item in group_selection_rates}) == 3
    assert len({item.key for item in group_selection_rates}) == 3
    assert {item.key for item in group_selection_rates} == {
        "group.str-2267726f757022.bool-74727565.selection_rate",
        "group.str-2267726f757022.int-31.selection_rate",
        "group.str-2267726f757022.str-223122.selection_rate",
    }
    comparison_values = {
        scope_key(item.comparison_group): item.value.value
        for item in differences
        if item.comparison_group is not None
    }
    assert comparison_values == {
        scope_key(AuditScope((("group", 1),))): -1.0,
        scope_key(AuditScope((("group", "1"),))): 0.0,
    }
    assert difference.value.value == -1.0
    assert difference.comparison_group is not None
    assert difference.reference_group is not None
    assert scope_key(difference.comparison_group) == integer_key
    assert scope_key(difference.reference_group) == scope_key(
        AuditScope((("group", True),))
    )
