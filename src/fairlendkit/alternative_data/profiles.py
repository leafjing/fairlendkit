"""Deterministic internal AD-2 signal-family profiles.

These typed objects are deliberately not exported from the package report API.
Only disclosure-controlled releases may cross the public reporting boundary.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Iterable

from pydantic import Field, field_serializer

from fairlendkit.alternative_data.contracts import (
    AlternativeDataConfig,
    RecordStatus,
    SignalEventType,
    SignalFamily,
    SignalRecord,
    StrictModel,
    TransferScope,
)
from fairlendkit.alternative_data.leakage import (
    GateDisposition,
    evaluate_feature_record,
    select_authoritative_feature_records,
)
from fairlendkit.alternative_data.reasons import AlternativeDataReasonCode


class _Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class _DecimalProfile(StrictModel):
    @field_serializer("*", check_fields=False)
    def serialize_decimal(self, value: object) -> object:
        return str(value) if isinstance(value, Decimal) else value


class _CashFlowProfile(_DecimalProfile):
    state: _Availability
    calendar_period_count: int = Field(ge=1)
    observed_period_count: int = Field(ge=0)
    missing_period_count: int = Field(ge=0)
    inflow_total: Decimal
    outflow_total: Decimal
    fee_total: Decimal
    net_cash_flow: Decimal
    mean_monthly_inflow: Decimal | None
    monthly_inflow_population_stddev: Decimal | None
    monthly_inflow_coefficient_of_variation: Decimal | None
    balance_observation_count: int = Field(ge=0)
    balance_availability_rate: Decimal
    negative_balance_count: int = Field(ge=0)
    negative_balance_rate: Decimal | None
    internal_transfer_count: int = Field(ge=0)
    uncertain_transfer_count: int = Field(ge=0)
    fee_event_count: int = Field(ge=0)
    reversal_count: int = Field(ge=0)
    reversed_amount: Decimal
    reason_codes: tuple[AlternativeDataReasonCode, ...]


class _ObligationProfile(_DecimalProfile):
    state: _Availability
    scheduled_obligation_count: int = Field(ge=0)
    scheduled_amount: Decimal
    observable_obligation_count: int = Field(ge=0)
    provider_coverage_rate: Decimal | None
    fully_paid_count: int = Field(ge=0)
    fully_paid_rate: Decimal | None
    timely_paid_count: int = Field(ge=0)
    timely_paid_rate: Decimal | None
    partial_payment_count: int = Field(ge=0)
    partial_payment_rate: Decimal | None
    observable_obligation_amount: Decimal
    linked_payment_amount: Decimal
    amount_coverage_rate: Decimal | None
    reversal_count: int = Field(ge=0)
    reporting_gap_count: int = Field(ge=0)
    reason_codes: tuple[AlternativeDataReasonCode, ...]


class _RentProfile(_ObligationProfile):
    grace_days: int = Field(ge=0)


class _UtilityProfile(_ObligationProfile):
    original_billed_amount: Decimal
    net_adjusted_obligation: Decimal
    estimated_bill_count: int = Field(ge=0)
    estimated_bill_rate: Decimal | None
    adjustment_count: int = Field(ge=0)
    adjustment_rate: Decimal | None
    service_interruption_count: int = Field(ge=0)
    provider_count: int = Field(ge=0)
    service_type_count: int = Field(ge=0)


def _calculate_cash_flow_profile(
    records: Iterable[SignalRecord],
    *,
    config: AlternativeDataConfig,
    minimum_behavior_periods: int = 3,
) -> _CashFlowProfile:
    if minimum_behavior_periods < 1:
        raise ValueError("minimum_behavior_periods must be positive")
    selected = _family_records(records, config, SignalFamily.CASH_FLOW)
    reversed_targets = {item.reversal_of for item in selected if item.reversal_of}
    active = tuple(
        item
        for item in selected
        if item.record_id not in reversed_targets
        and item.event_type != SignalEventType.REVERSAL
        and item.status not in {RecordStatus.PENDING, RecordStatus.UNAVAILABLE}
    )
    months = _calendar_months(
        config.observation_window.feature_start,
        config.observation_window.feature_end,
    )
    reporting_gaps = {
        _month_key(item.evidence_start)
        for item in selected
        if item.status == RecordStatus.UNAVAILABLE
    }
    observed_months = {
        _month_key(item.evidence_start) for item in active
    } - reporting_gaps
    missing = set(months) - observed_months
    monthly_inflow = {month: Decimal(0) for month in months}
    inflow = outflow = fees = Decimal(0)
    balances = []
    internal = uncertain = fee_count = 0
    for item in active:
        amount = item.amount or Decimal(0)
        if item.event_type == SignalEventType.INFLOW:
            inflow += amount
            monthly_inflow[_month_key(item.evidence_start)] += amount
        elif item.event_type == SignalEventType.OUTFLOW:
            outflow += amount
        elif item.event_type == SignalEventType.FEE:
            fees += amount
            fee_count += 1
        elif item.event_type == SignalEventType.BALANCE:
            balances.append(amount)
        elif item.event_type == SignalEventType.TRANSFER:
            if item.transfer_scope == TransferScope.INTERNAL:
                internal += 1
            elif item.transfer_scope == TransferScope.UNCERTAIN:
                uncertain += 1
    complete = len(observed_months) >= minimum_behavior_periods and not reporting_gaps
    mean = stddev = coefficient = None
    if complete:
        values = tuple(monthly_inflow[month] for month in months)
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        with localcontext() as context:
            context.prec = 34
            variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
            stddev = variance.sqrt()
            coefficient = None if mean == 0 else stddev / mean
    reversal_targets = {
        item.record_id: item.amount or Decimal(0) for item in selected
    }
    reversed_amount = sum(
        (reversal_targets.get(item.reversal_of or "", Decimal(0)) for item in selected if item.reversal_of),
        Decimal(0),
    )
    reasons = []
    if not balances:
        reasons.append(AlternativeDataReasonCode.BALANCE_HISTORY_UNAVAILABLE)
    if not complete:
        reasons.append(AlternativeDataReasonCode.INSUFFICIENT_CALENDAR_COVERAGE)
    if reporting_gaps:
        reasons.append(AlternativeDataReasonCode.PROVIDER_REPORTING_GAP)
    return _CashFlowProfile(
        state=_Availability.AVAILABLE if complete else _Availability.UNAVAILABLE,
        calendar_period_count=len(months),
        observed_period_count=len(observed_months),
        missing_period_count=len(missing),
        inflow_total=inflow,
        outflow_total=outflow,
        fee_total=fees,
        net_cash_flow=inflow - outflow - fees,
        mean_monthly_inflow=mean,
        monthly_inflow_population_stddev=stddev,
        monthly_inflow_coefficient_of_variation=coefficient,
        balance_observation_count=len(balances),
        balance_availability_rate=Decimal(len(balances)) / Decimal(len(months)),
        negative_balance_count=sum(value < 0 for value in balances),
        negative_balance_rate=(
            Decimal(sum(value < 0 for value in balances)) / Decimal(len(balances))
            if balances
            else None
        ),
        internal_transfer_count=internal,
        uncertain_transfer_count=uncertain,
        fee_event_count=fee_count,
        reversal_count=sum(item.event_type == SignalEventType.REVERSAL for item in selected),
        reversed_amount=reversed_amount,
        reason_codes=tuple(sorted(set(reasons), key=lambda item: item.value)),
    )


def _calculate_rent_profile(
    records: Iterable[SignalRecord],
    *,
    config: AlternativeDataConfig,
    grace_days: int,
) -> _RentProfile:
    if grace_days < 0:
        raise ValueError("grace_days cannot be negative")
    selected = _family_records(records, config, SignalFamily.RENT)
    common = _obligation_profile(selected, grace_days=grace_days, utility=False)
    return _RentProfile(**common, grace_days=grace_days)


def _calculate_utility_profile(
    records: Iterable[SignalRecord],
    *,
    config: AlternativeDataConfig,
) -> _UtilityProfile:
    selected = _family_records(records, config, SignalFamily.UTILITY)
    common = _obligation_profile(selected, grace_days=0, utility=True)
    bills = tuple(
        item
        for item in selected
        if item.event_type in {SignalEventType.BILL, SignalEventType.ESTIMATED_BILL}
        and item.status not in {RecordStatus.PENDING, RecordStatus.UNAVAILABLE}
    )
    adjustments = tuple(
        item for item in selected if item.event_type == SignalEventType.ADJUSTMENT
    )
    original = sum((item.amount or Decimal(0) for item in bills), Decimal(0))
    adjusted = original + sum((item.amount or Decimal(0) for item in adjustments), Decimal(0))
    count = len(bills)
    return _UtilityProfile(
        **common,
        original_billed_amount=original,
        net_adjusted_obligation=adjusted,
        estimated_bill_count=sum(item.event_type == SignalEventType.ESTIMATED_BILL for item in bills),
        estimated_bill_rate=(
            Decimal(sum(item.event_type == SignalEventType.ESTIMATED_BILL for item in bills))
            / Decimal(count)
            if count
            else None
        ),
        adjustment_count=len(adjustments),
        adjustment_rate=Decimal(len(adjustments)) / Decimal(count) if count else None,
        service_interruption_count=sum(
            item.event_type == SignalEventType.SERVICE_INTERRUPTION for item in selected
        ),
        provider_count=len({item.provider_id for item in bills}),
        service_type_count=len({item.service_type for item in bills}),
    )


def _obligation_profile(
    selected: tuple[SignalRecord, ...], *, grace_days: int, utility: bool
) -> dict[str, object]:
    obligation_types = (
        {SignalEventType.BILL, SignalEventType.ESTIMATED_BILL}
        if utility
        else {SignalEventType.OBLIGATION}
    )
    obligations = {
        (item.source_id, item.obligation_id): item
        for item in selected
        if item.event_type in obligation_types
        and item.status not in {RecordStatus.PENDING, RecordStatus.UNAVAILABLE}
    }
    payment_types = {SignalEventType.PAYMENT, SignalEventType.PARTIAL_PAYMENT}
    payments: dict[tuple[str, str | None], list[SignalRecord]] = defaultdict(list)
    adjustments: dict[tuple[str, str | None], Decimal] = defaultdict(Decimal)
    gaps = tuple(
        item for item in selected if item.event_type == SignalEventType.REPORTING_UNAVAILABLE
    )
    unmatched_payment = any(
        item.event_type in payment_types
        and (item.source_id, item.obligation_id) not in obligations
        for item in selected
    )
    reversed_targets = {item.reversal_of for item in selected if item.reversal_of}
    for item in selected:
        if item.record_id in reversed_targets or item.status in {
            RecordStatus.PENDING,
            RecordStatus.UNAVAILABLE,
        }:
            continue
        obligation_key = (item.source_id, item.obligation_id)
        if item.event_type in payment_types and obligation_key in obligations:
            if item.currency != obligations[obligation_key].currency:
                raise ValueError(AlternativeDataReasonCode.LINKAGE_FAMILY_MISMATCH.value)
            payments[obligation_key].append(item)
        elif item.event_type in {SignalEventType.ADJUSTMENT, SignalEventType.WAIVER}:
            if obligation_key in obligations:
                if item.amount is not None and item.currency != obligations[obligation_key].currency:
                    raise ValueError(AlternativeDataReasonCode.LINKAGE_FAMILY_MISMATCH.value)
                adjustments[obligation_key] += item.amount or Decimal(0)
    observable = []
    fully_paid = timely = partial = 0
    observable_amount = paid_amount = Decimal(0)
    for obligation_key, obligation in sorted(obligations.items()):
        if any(_date_in_period(obligation.due_date, gap) for gap in gaps):
            continue
        linked = sorted(payments.get(obligation_key, ()), key=_event_sort_key)
        if not linked:
            # Absence is not behavior evidence; it remains unavailable.
            continue
        observable.append(obligation)
        amount_due = (obligation.amount or Decimal(0)) + adjustments[obligation_key]
        observable_amount += amount_due
        cumulative = Decimal(0)
        completion: date | None = None
        for payment in linked:
            cumulative += payment.amount or Decimal(0)
            if completion is None and cumulative >= amount_due:
                completion = _as_date(payment.event_time)
        paid_amount += cumulative
        fully_paid += completion is not None
        timely += completion is not None and completion <= obligation.due_date + timedelta(days=grace_days)
        partial += any(item.event_type == SignalEventType.PARTIAL_PAYMENT for item in linked)
    scheduled = len(obligations)
    observed = len(observable)
    reasons = []
    if not obligations:
        reasons.append(AlternativeDataReasonCode.OBLIGATION_SCHEDULE_UNAVAILABLE)
    if gaps:
        reasons.append(AlternativeDataReasonCode.PROVIDER_REPORTING_GAP)
        reasons.append(AlternativeDataReasonCode.PROVIDER_NONPARTICIPATION)
    if unmatched_payment:
        reasons.append(AlternativeDataReasonCode.UNMATCHED_OBLIGATION)
    scheduled_amount = sum((item.amount or Decimal(0) for item in obligations.values()), Decimal(0))
    return {
        "state": _Availability.AVAILABLE if observed else _Availability.UNAVAILABLE,
        "scheduled_obligation_count": scheduled,
        "scheduled_amount": scheduled_amount,
        "observable_obligation_count": observed,
        "provider_coverage_rate": Decimal(observed) / Decimal(scheduled) if scheduled else None,
        "fully_paid_count": fully_paid,
        "fully_paid_rate": Decimal(fully_paid) / Decimal(observed) if observed else None,
        "timely_paid_count": timely,
        "timely_paid_rate": Decimal(timely) / Decimal(observed) if observed else None,
        "partial_payment_count": partial,
        "partial_payment_rate": Decimal(partial) / Decimal(observed) if observed else None,
        "observable_obligation_amount": observable_amount,
        "linked_payment_amount": paid_amount,
        "amount_coverage_rate": paid_amount / observable_amount if observable_amount else None,
        "reversal_count": sum(item.event_type == SignalEventType.REVERSAL for item in selected),
        "reporting_gap_count": len(gaps),
        "reason_codes": tuple(sorted(set(reasons), key=lambda item: item.value)),
    }


def _family_records(
    records: Iterable[SignalRecord],
    config: AlternativeDataConfig,
    family: SignalFamily,
) -> tuple[SignalRecord, ...]:
    items = tuple(records)
    for item in items:
        decision = evaluate_feature_record(
            item, config.observation_window, config.execution_time
        )
        if decision.disposition == GateDisposition.ERROR:
            raise ValueError(decision.reason_code.value)
    selected = select_authoritative_feature_records(
        items,
        config.sources,
        config.observation_window,
        config.execution_time,
    )
    family_items = tuple(item for item in selected if item.signal_family == family)
    if len({item.entity_id for item in family_items}) > 1:
        raise ValueError("internal signal profiles require exactly one entity scope")
    sources = {source.source_id: source for source in config.sources}
    return tuple(
        item
        for item in family_items
        if not (
            item.amount is not None
            and sources[item.source_id].default_currency is not None
            and item.currency != sources[item.source_id].default_currency
        )
    )


def _calendar_months(start: datetime, end: datetime) -> tuple[tuple[int, int], ...]:
    cursor = date(start.year, start.month, 1)
    final = date(end.year, end.month, 1)
    output = []
    while cursor <= final:
        output.append((cursor.year, cursor.month))
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    return tuple(output)


def _month_key(value: datetime | date) -> tuple[int, int]:
    return value.year, value.month


def _as_date(value: datetime | date | None) -> date:
    if value is None:
        raise ValueError("payment event requires event_time")
    return value.astimezone(UTC).date() if isinstance(value, datetime) else value


def _date_in_period(value: date | None, period: SignalRecord) -> bool:
    if value is None:
        return False
    return _as_date(period.period_start) <= value <= _as_date(period.period_end)


def _event_sort_key(record: SignalRecord) -> tuple[date, datetime, str]:
    return _as_date(record.event_time), record.observed_at, record.record_id
