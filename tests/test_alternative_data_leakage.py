from datetime import UTC, datetime

import pytest

from fairlendkit.alternative_data import (
    AlternativeDataReasonCode,
    AlternativeDataSource,
    CreditCoverage,
    GateDisposition,
    ObservationWindow,
    SignalRecord,
    evaluate_feature_record,
    evaluate_credit_coverage,
    evaluate_outcome_record,
    evaluate_source_completion,
    select_authoritative_feature_records,
)


def window():
    return ObservationWindow(
        as_of_time="2026-01-01T00:00:00Z",
        feature_start="2025-01-01T00:00:00Z",
        feature_end="2026-01-01T00:00:00Z",
        performance_start="2026-01-02T00:00:00Z",
        performance_end="2026-01-31T00:00:00Z",
        label_maturity_time="2026-02-01T00:00:00Z",
        outcome_definition="Observed binary performance",
    )


def source(**overrides):
    values = {
        "source_id": "source-1",
        "signal_family": "cash_flow",
        "provider_id": "provider-1",
        "acquisition_method": "provider_direct",
        "permission_reference": "permission-1",
        "coverage_start": "2025-01-01T00:00:00Z",
        "coverage_end": "2026-01-31T00:00:00Z",
        "refresh_cadence": "P1D",
        "source_timezone": "UTC",
        "currency_policy": "record_currency",
        "default_currency": None,
        "source_version": "v1",
    }
    values.update(overrides)
    return AlternativeDataSource(**values)


def record(**overrides):
    values = {
        "entity_id": "entity-1",
        "record_id": "record-1",
        "source_id": "source-1",
        "signal_family": "cash_flow",
        "event_type": "inflow",
        "event_time": "2025-12-31T00:00:00Z",
        "observed_at": "2025-12-31T00:00:00Z",
        "amount": "10.00",
        "currency": "USD",
        "status": "posted",
        "source_version": "v1",
    }
    values.update(overrides)
    return SignalRecord(**values)


@pytest.mark.parametrize(
    ("item", "execution", "disposition", "code"),
    [
        (record(), "2026-02-01T00:00:00Z", GateDisposition.ELIGIBLE, None),
        (
            record(observed_at="2026-01-01T00:00:01Z"),
            "2026-02-01T00:00:00Z",
            GateDisposition.EXCLUDE,
            AlternativeDataReasonCode.OBSERVED_AFTER_DECISION,
        ),
        (
            record(event_time="2026-01-01T00:00:01Z"),
            "2026-02-01T00:00:00Z",
            GateDisposition.ERROR,
            AlternativeDataReasonCode.FEATURE_AFTER_DECISION,
        ),
        (
            record(observed_at="2026-02-02T00:00:00Z"),
            "2026-02-01T00:00:00Z",
            GateDisposition.ERROR,
            AlternativeDataReasonCode.FUTURE_TIMESTAMP,
        ),
    ],
)
def test_feature_leakage_truth_table(item, execution, disposition, code):
    decision = evaluate_feature_record(
        item, window(), datetime.fromisoformat(execution.replace("Z", "+00:00"))
    )
    assert (decision.disposition, decision.reason_code) == (disposition, code)


def test_future_maturity_is_unavailable_not_a_future_timestamp_error():
    outcome = record(
        event_time="2026-01-15T00:00:00Z",
        observed_at="2026-01-15T00:00:00Z",
    )

    decision = evaluate_outcome_record(
        outcome, window(), datetime(2026, 1, 31, tzinfo=UTC)
    )
    assert decision.disposition == GateDisposition.UNAVAILABLE
    assert decision.reason_code == AlternativeDataReasonCode.LABEL_IMMATURE


def test_truth_table_equality_boundaries_are_inclusive_only_where_declared():
    feature_at_decision = record(
        event_time="2026-01-01T00:00:00Z",
        observed_at="2026-01-01T00:00:00Z",
    )
    assert evaluate_feature_record(
        feature_at_decision, window(), datetime(2026, 2, 1, tzinfo=UTC)
    ).disposition == GateDisposition.ELIGIBLE

    outcome_observed_at_execution = record(
        event_time="2026-01-31T00:00:00Z",
        observed_at="2026-02-01T00:00:00Z",
    )
    assert evaluate_outcome_record(
        outcome_observed_at_execution,
        window(),
        datetime(2026, 2, 1, tzinfo=UTC),
    ).disposition == GateDisposition.ELIGIBLE


def test_post_decision_revision_is_excluded_with_specific_reason():
    revision = record(
        record_id="revision",
        revision_of="record-1",
        observed_at="2026-01-02T00:00:00Z",
    )
    decision = evaluate_feature_record(
        revision, window(), datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert decision.reason_code == AlternativeDataReasonCode.REVISION_AFTER_DECISION


@pytest.mark.parametrize(
    ("period_start", "period_end", "expected"),
    [
        (
            "2025-12-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
            GateDisposition.ELIGIBLE,
        ),
        (
            "2025-12-01T00:00:00Z",
            "2026-01-01T00:00:01Z",
            GateDisposition.ERROR,
        ),
        (
            "2026-01-02T00:00:00Z",
            "2026-01-03T00:00:00Z",
            GateDisposition.ERROR,
        ),
    ],
)
def test_feature_period_decision_boundaries(period_start, period_end, expected):
    item = record(
        event_time=None,
        period_start=period_start,
        period_end=period_end,
    )
    decision = evaluate_feature_record(
        item, window(), datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert decision.disposition == expected


@pytest.mark.parametrize(
    ("event_time", "expected", "code"),
    [
        ("2026-01-02T00:00:00Z", GateDisposition.ELIGIBLE, None),
        (
            "2026-01-01T12:00:00Z",
            GateDisposition.EXCLUDE,
            AlternativeDataReasonCode.OUTCOME_OUTSIDE_WINDOW,
        ),
        (
            "2026-02-01T00:00:00Z",
            GateDisposition.EXCLUDE,
            AlternativeDataReasonCode.OUTCOME_OUTSIDE_WINDOW,
        ),
    ],
)
def test_outcome_performance_window_boundaries(event_time, expected, code):
    outcome = record(event_time=event_time, observed_at=event_time)
    decision = evaluate_outcome_record(
        outcome, window(), datetime(2026, 2, 2, tzinfo=UTC)
    )
    assert (decision.disposition, decision.reason_code) == (expected, code)


def test_outcome_equal_to_decision_boundary_fails_closed():
    outcome = record(
        event_time="2026-01-01T00:00:00Z",
        observed_at="2026-01-01T00:00:00Z",
    )
    decision = evaluate_outcome_record(
        outcome, window(), datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert decision.reason_code == AlternativeDataReasonCode.OUTCOME_NOT_POST_DECISION


def test_completed_source_cannot_claim_future_coverage():
    decision = evaluate_source_completion(
        source(coverage_end="2026-02-02T00:00:00Z"),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    assert decision.reason_code == AlternativeDataReasonCode.FUTURE_TIMESTAMP
    assert evaluate_source_completion(
        source(coverage_end=None), datetime(2026, 2, 1, tzinfo=UTC)
    ).disposition == GateDisposition.ELIGIBLE


def test_coverage_stratum_requires_decision_time_available_evidence():
    coverage = CreditCoverage(
        entity_id="entity-1",
        coverage_stratum="limited_file",
        definition_id="definition-v1",
        assessed_at="2026-01-02T00:00:00Z",
        evidence_available=True,
    )
    decision = evaluate_credit_coverage(
        coverage, window(), datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert decision.disposition == GateDisposition.EXCLUDE
    assert decision.reason_code == AlternativeDataReasonCode.OBSERVED_AFTER_DECISION


def test_authoritative_revision_is_latest_version_observable_at_decision_time():
    original = record()
    eligible_revision = record(
        record_id="record-2",
        revision_of="record-1",
        observed_at="2025-12-31T12:00:00Z",
    )
    late_revision = record(
        record_id="record-3",
        revision_of="record-2",
        observed_at="2026-01-02T00:00:00Z",
    )

    selected = select_authoritative_feature_records(
        (late_revision, original, eligible_revision),
        (source(),),
        window(),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    assert tuple(item.record_id for item in selected) == ("record-2",)


def test_authoritative_branch_uses_canonical_latest_terminal_version():
    original = record()
    earlier = record(
        record_id="record-2",
        revision_of="record-1",
        observed_at="2025-12-31T12:00:00Z",
    )
    later = record(
        record_id="record-3",
        revision_of="record-1",
        observed_at="2025-12-31T13:00:00Z",
    )
    selected = select_authoritative_feature_records(
        (later, original, earlier),
        (source(),),
        window(),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    assert tuple(item.record_id for item in selected) == ("record-3",)


def test_equal_time_parallel_terminal_revisions_fail_independent_of_order():
    original = record()
    left = record(
        record_id="record-2",
        revision_of="record-1",
        observed_at="2025-12-31T12:00:00Z",
    )
    right = record(
        record_id="record-3",
        revision_of="record-1",
        observed_at="2025-12-31T12:00:00Z",
    )
    for items in ((original, left, right), (right, left, original)):
        with pytest.raises(ValueError, match="ad_non_monotonic_history"):
            select_authoritative_feature_records(
                items, (source(),), window(), datetime(2026, 2, 1, tzinfo=UTC)
            )


@pytest.mark.parametrize(
    "items",
    [
        (
            record(record_id="one", event_type="reversal", amount=None, reversal_of="two"),
            record(record_id="two", event_type="reversal", amount=None, reversal_of="one"),
        ),
        (
            record(record_id="one", revision_of="two"),
            record(record_id="two", event_type="reversal", amount=None, reversal_of="one"),
        ),
    ],
)
def test_reversal_and_mixed_linkage_cycles_fail_closed(items):
    with pytest.raises(ValueError, match="ad_non_monotonic_history"):
        select_authoritative_feature_records(
            items, (source(),), window(), datetime(2026, 2, 1, tzinfo=UTC)
        )


def test_authoritative_selection_rejects_missing_and_non_monotonic_links():
    with pytest.raises(ValueError, match="ad_revision_target_missing"):
        select_authoritative_feature_records(
            (record(revision_of="missing"),),
            (source(),),
            window(),
            datetime(2026, 2, 1, tzinfo=UTC),
        )

    first = record(record_id="one", revision_of="two")
    second = record(record_id="two", revision_of="one")
    with pytest.raises(ValueError, match="ad_non_monotonic_history"):
        select_authoritative_feature_records(
            (first, second),
            (source(),),
            window(),
            datetime(2026, 2, 1, tzinfo=UTC),
        )
