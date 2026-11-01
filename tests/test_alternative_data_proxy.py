import csv
from datetime import datetime, timezone
import io
import json
import re

import pytest
from pydantic import ValidationError

from fairlendkit.alternative_data import (
    ProxyConfig,
    ProxyEntity,
    build_proxy_release,
    proxy_fold,
    render_proxy_csv,
    render_proxy_html,
)
from fairlendkit.alternative_data.proxy import (
    CandidateKind,
    ProxyFailure,
    ProxyReason,
    ProxyWindow,
    _diagnostic_scores,
    _fit_encoder,
    _fit_logistic,
    _normalized_rows,
    auc,
    cramers_v,
    eta_squared,
    reduce_entities,
)


def config(**updates):
    values = dict(
        protocol_version="ad4-v1",
        population_id="synthetic-v1",
        candidate_id="cash-flow-volatility-v1",
        protected_attribute_id="audit-target-v1",
        candidate_kind="numeric",
        candidate_source_id="source-v1",
        candidate_derivation_version="derivation-v1",
        reducer_id="reducer-v1",
        reducer_version="1",
        development_window="2025-01/2025-06",
        holdout_window="2025-07/2025-12",
        association_threshold=.5,
        predictability_auc_threshold=.7,
        incremental_auc_threshold=.05,
        stability_tolerance=.2,
        fold_seed=7,
        fold_count=3,
        minimum_valid_folds=2,
        per_fold_class_minimum=1,
        provider_strata=("provider-a", "provider-b", "other"),
        coverage_strata=("coverage-a", "coverage-b", "other"),
        minimum_stratum_entities=10,
        maximum_categories=20,
        minimum_level_entities=2,
        minimum_report_cell_count=10,
        bootstrap_seed=11,
        bootstrap_resamples=20,
        minimum_valid_resamples=10,
        confidence_level=.95,
    )
    values.update(updates)
    return ProxyConfig(**values)


def provenance(*, baseline=False):
    observed = datetime(2024, 12, 1, tzinfo=timezone.utc)
    return dict(
        candidate_source_id="source-v1",
        candidate_derivation_version="derivation-v1",
        reducer_id="reducer-v1",
        reducer_version="1",
        as_of_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        candidate_available_time=observed,
        protected_observation_time=observed,
        baseline_available_time=observed if baseline else None,
    )


def rows(*, single_provider=False, single_coverage=False, baseline=False):
    output = []
    for window in ProxyWindow:
        for index in range(120):
            protected = "class-b" if index % 2 else "class-a"
            candidate = None if index % 16 in (0, 1, 2, 3) else (1.0 if protected == "class-b" else 0.0) + ((index % 5) - 2) * .01
            output.append(
                ProxyEntity(
                    entity_id=f"SECRET-ENTITY-{window}-{index}",
                    window=window,
                    candidate=candidate,
                    protected=protected,
                    provider_stratum=(
                        "provider-a"
                        if single_provider or index % 4 < 2
                        else "provider-b"
                    ),
                    coverage_stratum=(
                        "coverage-a"
                        if single_coverage or index % 4 in (0, 3)
                        else "coverage-b"
                    ),
                    baseline=((index % 3) / 3,) if baseline else (),
                    **provenance(baseline=baseline),
                )
            )
    return tuple(output)


def test_approved_contract_is_exact_and_caller_scores_are_forbidden():
    with pytest.raises(ValidationError):
        ProxyEntity(
            entity_id="secret", window="development", candidate=1,
            protected="a", provider_stratum="p", coverage_stratum="c",
            candidate_score=.99,
            **provenance(),
        )
    with pytest.raises(ValidationError, match="ad_proxy_weighting_unsupported"):
        config(weighting="weighted")
    with pytest.raises(ValidationError, match="ad_proxy_candidate_prohibited"):
        config(candidate_id="entity_id")
    failure = ProxyFailure(ProxyReason.WEIGHTING_UNSUPPORTED)
    assert failure.disposition == "error"
    assert failure.canonical_message == (
        "Proxy-screening configuration requests weighted eligibility, fitting, "
        "metrics, bootstrap, or suppression."
    )
    secret = "SECRET-CONFIG-PAYLOAD"
    with pytest.raises(ValidationError) as captured:
        config(weighting="weighted", candidate_id=secret)
    assert secret not in str(captured.value)
    assert secret not in repr(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_reason_contract_dispositions_and_messages_are_exact():
    expected = {
        ProxyReason.CANDIDATE_PROHIBITED: (
            "error",
            "A candidate or baseline field is protected-derived, outcome, decision, post-decision, identifier, free text, exact geolocation, fold, weight, provider key, leakage-rejected, or otherwise prohibited by the proxy contract.",
        ),
        ProxyReason.ENTITY_CONFLICT: (
            "error",
            "One proxy-screening entity has conflicting protected, candidate, baseline, provider, coverage, or reducer values after authoritative reduction.",
        ),
        ProxyReason.WINDOW_CONFLICT: (
            "error",
            "Proxy-screening development and temporal-holdout windows are not strictly forward and non-overlapping.",
        ),
        ProxyReason.ISOLATION_FAILURE: (
            "error",
            "An entity, fitted transform, category vocabulary, or target-derived value crosses a proxy-screening fold or development/holdout boundary.",
        ),
        ProxyReason.PROTECTED_MISSING: (
            "exclude",
            "An entity lacks the user-supplied protected attribute required by this proxy screen.",
        ),
        ProxyReason.STATISTIC_UNDEFINED: (
            "unavailable",
            "A proxy statistic has no defined denominator, required class comparison, finite value, or corrected contingency dimension.",
        ),
        ProxyReason.PAIRED_POPULATION_MISMATCH: (
            "error",
            "Baseline and baseline-plus-candidate proxy evidence do not contain the exact same canonically ordered entity population.",
        ),
    }
    for reason, (disposition, message) in expected.items():
        failure = ProxyFailure(reason)
        assert (failure.disposition, failure.canonical_message) == (disposition, message)


def test_hand_calculated_metrics_and_frozen_fold():
    assert eta_squared(((0.0, "A"), (2.0, "A"), (4.0, "B"), (6.0, "B"))) == .8
    assert cramers_v(tuple((value, value) for value in ("a", "b") for _ in range(10))) == 1
    assert auc(((False, .1), (False, .4), (True, .6), (True, .9))) == 1
    assert auc(((False, .5), (True, .5))) == .5
    assert [proxy_fold("ad4-v1", f"entity-{index}", 7, 5) for index in range(6)] == [0, 2, 0, 1, 2, 1]


def test_entity_reduction_is_deterministic_and_fail_closed():
    item = rows()[0]
    assert reduce_entities((item, item)) == (item,)
    with pytest.raises(ProxyFailure, match="ad_proxy_entity_conflict"):
        reduce_entities((item, item.model_copy(update={"candidate": .25})))
    with pytest.raises(ProxyFailure, match="ad_proxy_window_conflict"):
        reduce_entities((item, item.model_copy(update={"window": "holdout"})))


def test_typed_reducer_source_and_observation_time_contracts_fail_closed():
    original = rows()[0]
    for update, reason in (
        ({"reducer_version": "wrong"}, "ad_proxy_entity_conflict"),
        ({"candidate_source_id": "wrong"}, "ad_proxy_entity_conflict"),
        ({"candidate_derivation_version": "wrong"}, "ad_proxy_entity_conflict"),
        ({"candidate_available_time": datetime(2026, 1, 1, tzinfo=timezone.utc)}, "ad_proxy_isolation_failure"),
        ({"protected_observation_time": datetime(2026, 1, 1, tzinfo=timezone.utc)}, "ad_proxy_isolation_failure"),
    ):
        changed = (original.model_copy(update=update),) + rows()[1:]
        with pytest.raises(ProxyFailure, match=reason):
            build_proxy_release(changed, config())


def test_internal_fixed_model_is_order_independent_and_holdout_is_scored_once():
    entities = rows()
    left = _diagnostic_scores(entities, config(), True, False)
    right = _diagnostic_scores(tuple(reversed(entities)), config(), True, False)
    assert left == right
    development, holdout, iterations = left
    assert len(development.entity_ids) == len(holdout.entity_ids) == 120
    assert iterations > 0
    # Frozen first logits/probabilities prove scores are produced internally.
    assert development.probabilities[:2] == right[0].probabilities[:2]
    assert holdout.probabilities[:2] == right[1].probabilities[:2]
    assert iterations == 4
    assert development.entity_ids[:3] == (
        "SECRET-ENTITY-development-0",
        "SECRET-ENTITY-development-1",
        "SECRET-ENTITY-development-10",
    )
    assert development.probabilities[:3] == (
        (0.5787215438340222, 0.4212784561659778),
        (0.5787215438340222, 0.4212784561659778),
        (0.5938093118816561, 0.40619068811834397),
    )
    encoder = _fit_encoder(
        tuple(row for row in entities if row.window == ProxyWindow.DEVELOPMENT),
        (CandidateKind.NUMERIC,), lambda row: (row.candidate,), config(),
    )
    assert encoder.numeric == ((0.5, 0.4999166666666667, 0.4282512810514666),)

    asymmetric = tuple(
        rows()[index].model_copy(update={"candidate": value})
        for index, value in enumerate((0.0, 0.0, 10.0, None))
    )
    asymmetric_encoder = _fit_encoder(
        asymmetric, (CandidateKind.NUMERIC,), lambda row: (row.candidate,), config(),
    )
    median, mean, std = asymmetric_encoder.numeric[0]
    assert (median, mean) == (0.0, 2.5)
    assert std == 4.330127018922194
    assert asymmetric_encoder.transform((0.0,))[1] == (0.0 - mean) / std
    assert asymmetric_encoder.transform((None,))[1:] == ((median - mean) / std, 1.0)


def test_rare_unseen_high_cardinality_and_nonconvergence_contracts():
    training = tuple(
        ProxyEntity(
            entity_id=f"cat-{index}", window="development",
            candidate=value, protected="a" if index % 2 else "b",
            provider_stratum="provider-a", coverage_stratum="coverage-a",
            **provenance(),
        )
        for index, value in enumerate(("common", "common", "rare-value"))
    )
    encoder = _fit_encoder(
        training, (CandidateKind.CATEGORICAL,), lambda row: (row.candidate,),
        config(minimum_level_entities=2),
    )
    assert encoder.transform(("rare-value",)) != encoder.transform(("rare",))
    assert encoder.transform((None,)) != encoder.transform(("missing",))
    assert encoder.transform(("holdout-only",)) != encoder.transform(("rare-value",))
    with pytest.raises(ProxyFailure, match="ad_high_cardinality_unsupported"):
        _fit_encoder(
            training, (CandidateKind.CATEGORICAL,), lambda row: (row.candidate,),
            config(maximum_categories=2, minimum_level_entities=1),
        )
    with pytest.raises(ProxyFailure, match="ad_proxy_model_nonconvergence"):
        _fit_logistic(((1.0, float("nan")), (1.0, 0.0)), (0, 1), 2)


def test_binary_auc_and_paired_incremental_auc_use_internal_predictions():
    entities = rows(baseline=True)
    release = build_proxy_release(
        entities,
        config(baseline_id="approved-baseline-v1", baseline_kinds=("numeric",)),
    )
    metrics = {item.evidence_key.metric for item in release.evidence}
    assert {"eta_squared", "missingness_cramers_v", "predictability_auc", "incremental_auc"} <= metrics
    increments = [
        item for item in release.evidence
        if item.evidence_key.metric == "incremental_auc"
        and item.evidence_key.stratum_dimension == "overall"
    ]
    assert len(increments) == 2
    assert all(item.denominator == 120 for item in increments)
    assert all(item.valid_resamples == 20 for item in increments)


def test_multiclass_auc_missingness_and_categorical_rare_unseen():
    entities = []
    classes = ("a", "b", "c")
    for window in ProxyWindow:
        for index in range(90):
            protected = classes[index % 3]
            value = protected if index < 87 else None
            entities.append(ProxyEntity(
                entity_id=f"multi-{window}-{index}", window=window,
                candidate=value, protected=protected,
                provider_stratum="provider-a" if index % 2 else "provider-b",
                coverage_stratum="coverage-a" if index % 4 < 2 else "coverage-b",
                **provenance(),
            ))
    release = build_proxy_release(entities, config(candidate_kind="categorical", association_threshold=.1))
    auc_items = [item for item in release.evidence if item.evidence_key.metric == "predictability_auc"]
    assert auc_items
    assert all(item.evidence_key.class_aggregation == "macro_ovr" for item in auc_items)
    assert any(item.evidence_key.metric == "missingness_cramers_v" for item in release.evidence)


def test_thresholds_and_three_stability_dimensions_gate_typed_flag():
    release = build_proxy_release(rows(), config())
    assert release.flag_state == "published"
    assert release.flag is not None
    assert release.flag.threshold_evidence.development.window == "development"
    assert release.flag.threshold_evidence.holdout.window == "holdout"
    assert len(release.flag.provider) == 2
    assert len(release.flag.coverage_stratum) == 2
    assert release.trace.rng_identity == "fairlendkit-sha256-counter-v1"

    provider = build_proxy_release(rows(single_provider=True), config())
    assert provider.flag is None
    assert provider.flag_reason_code in {
        "ad_proxy_strata_not_comparable", "ad_proxy_stratum_support"
    }
    coverage = build_proxy_release(rows(single_coverage=True), config())
    assert coverage.flag is None
    assert coverage.flag_reason_code in {
        "ad_proxy_strata_not_comparable", "ad_proxy_stratum_support"
    }


def test_one_sided_threshold_and_unreliable_interval_prevent_flag():
    changed = tuple(
        row.model_copy(update={"candidate": (index % 7) / 7})
        if row.window == ProxyWindow.HOLDOUT else row
        for index, row in enumerate(rows())
    )
    release = build_proxy_release(changed, config())
    assert release.flag is None
    assert release.flag_reason_code == "ad_proxy_threshold_not_met"

    unreliable = build_proxy_release(
        rows(),
        config(bootstrap_resamples=5, minimum_valid_resamples=5),
    )
    assert all(
        (item.lower is None and item.upper is None)
        if item.reliable is False else True
        for item in unreliable.evidence
    )


def test_joint_suppression_and_historical_equations_hide_all_derived_values():
    sparse_rows = rows()[:8] + rows()[120:128]
    release = build_proxy_release(sparse_rows, config())
    assert release.flag is None
    payload = release.model_dump(mode="json")
    hidden = [item for item in payload["evidence"] if item["state"] == "suppressed"]
    assert hidden
    for item in hidden:
        for key in (
            "eligible_count", "excluded_count", "missing_count", "denominator",
            "class_support", "point", "lower", "upper", "valid_resamples",
            "invalid_resamples", "reliable",
        ):
            assert item[key] is None
    repeated = build_proxy_release(sparse_rows, config(), previous_release=release)
    assert repeated == release

    published = build_proxy_release(rows(), config())
    assert build_proxy_release(rows(), config(), previous_release=published) == published
    changed = list(rows())
    changed[0] = changed[0].model_copy(update={"provider_stratum": "provider-b"})
    with pytest.raises(ValueError, match="historical exact value"):
        build_proxy_release(changed, config(), previous_release=published)

    for drifted in (
        config(bootstrap_seed=12),
        config(association_threshold=.6),
        config(stability_tolerance=.1),
    ):
        with pytest.raises(ProxyFailure, match="ad_proxy_isolation_failure"):
            build_proxy_release(rows(), drifted, previous_release=published)

    missing_changed = list(rows())
    missing_index = next(index for index, row in enumerate(missing_changed) if row.candidate is None)
    missing_changed[missing_index] = missing_changed[missing_index].model_copy(update={"candidate": 0.0})
    with pytest.raises(ValueError, match="historical exact value"):
        build_proxy_release(missing_changed, config(), previous_release=published)


def test_json_csv_html_share_typed_flag_and_evidence_references():
    release = build_proxy_release(rows(), config())
    normalized = _normalized_rows(release)
    csv_rows = tuple(csv.DictReader(io.StringIO(render_proxy_csv(release))))
    html = render_proxy_html(release)
    encoded = re.search(r"<pre>(.*)</pre>", html).group(1)
    decoded = json.loads(encoded.replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&"))
    assert len(csv_rows) == len(normalized)
    assert decoded == list(normalized)
    assert any(row["row_type"] == "proxy_flag" for row in normalized)
    assert any(row["row_type"] == "proxy_flag_evidence" for row in normalized)


def test_release_contains_no_identifiers_predictions_coefficients_or_forbidden_conclusions():
    release = build_proxy_release(rows(), config())
    outputs = (
        release.model_dump_json(),
        render_proxy_csv(release),
        render_proxy_html(release),
    )
    forbidden = (
        "SECRET-ENTITY", "coefficient", "prediction", "class-a", "class-b",
        "causation", "discrimination", "compliant", "creditworthy",
        "feature removal", "threshold recommendation",
    )
    for output in outputs:
        for secret in forbidden:
            assert secret not in output
