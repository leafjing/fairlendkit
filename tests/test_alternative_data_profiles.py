from decimal import Decimal

import pytest

from fairlendkit.alternative_data import (
    AlternativeDataConfig,
    AlternativeDataSource,
    ObservationWindow,
    SignalRecord,
    SignalRecordFieldMap,
    adapt_cash_flow_records,
)
from fairlendkit.alternative_data.profiles import (
    _calculate_cash_flow_profile,
    _calculate_rent_profile,
    _calculate_utility_profile,
)


def source(family):
    return AlternativeDataSource(
        source_id=f"{family}-source",
        signal_family=family,
        provider_id=f"{family}-provider",
        acquisition_method="provider_direct",
        permission_reference="permission-ref",
        coverage_start="2025-01-01T00:00:00Z",
        coverage_end="2025-03-31T23:59:59Z",
        refresh_cadence="P1D",
        source_timezone="UTC",
        currency_policy="single_currency",
        default_currency="USD",
        source_version="v1",
    )


def config(family):
    return AlternativeDataConfig(
        sources=(source(family),),
        observation_window=ObservationWindow(
            as_of_time="2025-03-31T23:59:59.999999Z",
            feature_start="2025-01-01T00:00:00Z",
            feature_end="2025-03-31T23:59:59.999999Z",
            performance_start="2025-04-01T00:00:00Z",
            performance_end="2025-04-30T00:00:00Z",
            label_maturity_time="2025-05-01T00:00:00Z",
            outcome_definition="fixture outcome",
        ),
        execution_time="2025-05-01T00:00:00Z",
        allowed_coverage_strata=("limited",),
        minimum_report_cell_count=10,
    )


def record(family, record_id, event_type, event_time, amount=None, **extra):
    payload = {
        "entity_id": "secret-entity",
        "record_id": record_id,
        "source_id": f"{family}-source",
        "signal_family": family,
        "event_type": event_type,
        "event_time": event_time,
        "observed_at": event_time if "T" in event_time else f"{event_time}T12:00:00Z",
        "amount": amount,
        "currency": "USD" if amount is not None else None,
        "status": "posted",
        "source_version": "v1",
    }
    payload.update(extra)
    return SignalRecord(**payload)


def period_record(family, record_id, event_type, start, end, **extra):
    payload = {
        "entity_id": "secret-entity",
        "record_id": record_id,
        "source_id": f"{family}-source",
        "signal_family": family,
        "event_type": event_type,
        "period_start": start,
        "period_end": end,
        "observed_at": f"{end}T12:00:00Z",
        "status": "posted",
        "source_version": "v1",
    }
    payload.update(extra)
    return SignalRecord(**payload)


def test_cash_flow_oracle_uses_decimal_reversals_and_period_denominators():
    rows = (
        record("cash_flow", "i1a", "inflow", "2025-01-05T00:00:00Z", "2000"),
        record("cash_flow", "i1b", "inflow", "2025-01-15T00:00:00Z", "500"),
        record("cash_flow", "o1", "outflow", "2025-01-20T00:00:00Z", "1200"),
        record("cash_flow", "b1", "balance", "2025-01-31T00:00:00Z", "1300"),
        record("cash_flow", "i2", "inflow", "2025-02-05T00:00:00Z", "2000"),
        record("cash_flow", "o2", "outflow", "2025-02-20T00:00:00Z", "1500"),
        record("cash_flow", "t2", "transfer", "2025-02-21T00:00:00Z", "300", transfer_scope="internal"),
        record("cash_flow", "b2", "balance", "2025-02-28T00:00:00Z", "1500"),
        record("cash_flow", "i3", "inflow", "2025-03-05T00:00:00Z", "2200"),
        record("cash_flow", "o3", "outflow", "2025-03-20T00:00:00Z", "1600"),
        record("cash_flow", "fee", "fee", "2025-03-21T00:00:00Z", "25"),
        record("cash_flow", "reversed-outflow", "outflow", "2025-03-22T00:00:00Z", "100"),
        record("cash_flow", "reversal", "reversal", "2025-03-23T00:00:00Z", None, currency="USD", reversal_of="reversed-outflow"),
        record("cash_flow", "b3", "balance", "2025-03-31T00:00:00Z", "1975"),
    )
    profile = _calculate_cash_flow_profile(rows, config=config("cash_flow"))

    assert profile.inflow_total == Decimal("6700")
    assert profile.outflow_total == Decimal("4300")
    assert profile.net_cash_flow == Decimal("2375")
    assert profile.mean_monthly_inflow == Decimal("6700") / Decimal(3)
    assert abs(profile.monthly_inflow_population_stddev - Decimal("205.48046676563254")) < Decimal("1e-14")
    assert profile.reversal_count == 1
    assert profile.reversed_amount == Decimal("100")
    assert profile.balance_availability_rate == Decimal(1)
    assert profile.internal_transfer_count == 1


def test_cash_flow_reporting_gap_never_invents_zero_behavior():
    rows = (
        record("cash_flow", "i1", "inflow", "2025-01-05T00:00:00Z", "100"),
        period_record("cash_flow", "gap", "outflow", "2025-02-01", "2025-02-28", amount="0", currency="USD", status="unavailable"),
        record("cash_flow", "i3", "inflow", "2025-03-05T00:00:00Z", "100"),
    )
    profile = _calculate_cash_flow_profile(rows, config=config("cash_flow"))
    assert profile.state == "unavailable"
    assert profile.mean_monthly_inflow is None
    assert "ad_provider_reporting_gap" in profile.reason_codes


def test_rent_oracle_excludes_nonparticipating_period_from_behavior():
    rows = (
        record("rent", "ob1", "obligation", "2025-01-01", "1000", obligation_id="m1", due_date="2025-01-05"),
        record("rent", "pay1", "payment", "2025-01-05", "1000", obligation_id="m1"),
        record("rent", "ob2", "obligation", "2025-02-01", "1000", obligation_id="m2", due_date="2025-02-05"),
        record("rent", "pay2a", "partial_payment", "2025-02-08", "600", obligation_id="m2"),
        record("rent", "pay2b", "payment", "2025-02-13", "400", obligation_id="m2"),
        record("rent", "ob3", "obligation", "2025-03-01", "1000", obligation_id="m3", due_date="2025-03-05"),
        period_record("rent", "gap", "reporting_unavailable", "2025-03-01", "2025-03-31", status="unavailable"),
    )
    profile = _calculate_rent_profile(rows, config=config("rent"), grace_days=5)
    assert profile.scheduled_obligation_count == 3
    assert profile.scheduled_amount == Decimal("3000")
    assert profile.observable_obligation_count == 2
    assert profile.provider_coverage_rate == Decimal(2) / Decimal(3)
    assert profile.fully_paid_rate == Decimal(1)
    assert profile.timely_paid_rate == Decimal(1) / Decimal(2)
    assert profile.partial_payment_rate == Decimal(1) / Decimal(2)
    assert profile.amount_coverage_rate == Decimal(1)


def test_utility_oracle_uses_linked_adjustments_and_explicit_payments():
    rows = (
        period_record("utility", "b1", "bill", "2025-01-01", "2025-01-31", amount="100", currency="USD", obligation_id="m1", due_date="2025-01-31", provider_id="p", service_type="electricity"),
        record("utility", "p1", "payment", "2025-01-31", "100", obligation_id="m1"),
        period_record("utility", "b2", "bill", "2025-02-01", "2025-02-28", amount="120", currency="USD", obligation_id="m2", due_date="2025-02-28", provider_id="p", service_type="electricity"),
        record("utility", "p2a", "partial_payment", "2025-02-28", "60", obligation_id="m2"),
        record("utility", "p2b", "payment", "2025-03-01", "60", obligation_id="m2"),
        period_record("utility", "b3", "estimated_bill", "2025-03-01", "2025-03-31", amount="80", currency="USD", obligation_id="m3", due_date="2025-03-31", provider_id="p", service_type="electricity"),
        record("utility", "a3", "adjustment", "2025-03-20", "-20", obligation_id="m3"),
        record("utility", "p3", "payment", "2025-03-31", "60", obligation_id="m3"),
    )
    profile = _calculate_utility_profile(rows, config=config("utility"))
    assert profile.original_billed_amount == Decimal("300")
    # Decimal arithmetic matches the corrected normative oracle.
    assert profile.net_adjusted_obligation == Decimal("280")
    assert profile.linked_payment_amount == Decimal("280")
    assert profile.fully_paid_rate == Decimal(1)
    assert profile.timely_paid_rate == Decimal(2) / Decimal(3)
    assert profile.partial_payment_rate == Decimal(1) / Decimal(3)
    assert profile.estimated_bill_rate == Decimal(1) / Decimal(3)
    assert profile.adjustment_rate == Decimal(1) / Decimal(3)


def test_explicit_adapter_rejects_unmapped_and_unknown_categories():
    mapping = SignalRecordFieldMap(
        fields={
            "entity_id": "consumer",
            "record_id": "id",
            "event_type": "kind",
            "event_time": "when",
            "observed_at": "seen",
            "amount": "amount",
            "currency": "currency",
            "status": "status",
        }
    )
    row = {
        "consumer": "secret",
        "id": "r1",
        "kind": "inflow",
        "when": "2025-01-01T00:00:00Z",
        "seen": "2025-01-01T00:00:00Z",
        "amount": "1.25",
        "currency": "USD",
        "status": "posted",
    }
    assert adapt_cash_flow_records((row,), mapping=mapping, source=source("cash_flow"))[0].amount == Decimal("1.25")
    with pytest.raises(ValueError, match="unmapped external field"):
        adapt_cash_flow_records(({**row, "description": "private"},), mapping=mapping, source=source("cash_flow"))
    with pytest.raises(ValueError):
        adapt_cash_flow_records(({**row, "kind": "mystery"},), mapping=mapping, source=source("cash_flow"))


def test_profile_mutations_fail_closed_or_remain_unavailable_without_adverse_inference():
    with pytest.raises(ValueError):
        record(
            "rent",
            "missing-due-date",
            "obligation",
            "2025-01-01",
            "100",
            obligation_id="m1",
        )
    with pytest.raises(ValueError, match="ad_reversal_target_missing"):
        _calculate_cash_flow_profile(
            (
                record(
                    "cash_flow",
                    "broken-reversal",
                    "reversal",
                    "2025-01-02T00:00:00Z",
                    None,
                    currency="USD",
                    reversal_of="missing",
                ),
            ),
            config=config("cash_flow"),
        )

    with pytest.raises(ValueError, match="ad_feature_after_decision"):
        _calculate_cash_flow_profile(
            (
                record("cash_flow", "future", "inflow", "2025-04-02T00:00:00Z", "999"),
            ),
            config=config("cash_flow"),
        )

    profile = _calculate_cash_flow_profile(
        (
            record("cash_flow", "usd", "inflow", "2025-01-01T00:00:00Z", "100"),
            record("cash_flow", "eur", "inflow", "2025-01-02T00:00:00Z", "999", currency="EUR"),
        ),
        config=config("cash_flow"),
    )
    assert profile.inflow_total == Decimal("100")
    assert profile.state == "unavailable"
    assert profile.mean_monthly_inflow is None
