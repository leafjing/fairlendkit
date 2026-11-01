"""Fail-closed time leakage gate and authoritative feature-version selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import Iterable

from fairlendkit.alternative_data.contracts import (
    AlternativeDataSource,
    CreditCoverage,
    ObservationWindow,
    RecordStatus,
    SignalRecord,
)
from fairlendkit.alternative_data.reasons import AlternativeDataReasonCode


class GateDisposition(StrEnum):
    ELIGIBLE = "eligible"
    ERROR = "error"
    EXCLUDE = "exclude"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class LeakageDecision:
    disposition: GateDisposition
    reason_code: AlternativeDataReasonCode | None = None

    def __post_init__(self) -> None:
        if (self.disposition == GateDisposition.ELIGIBLE) != (
            self.reason_code is None
        ):
            raise ValueError("only eligible decisions omit a reason code")


ELIGIBLE = LeakageDecision(GateDisposition.ELIGIBLE)


def _instant(value: datetime | date, *, end_of_day: bool = False) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("record times must be timezone-aware")
        return value.astimezone(UTC)
    boundary = time.max if end_of_day else time.min
    return datetime.combine(value, boundary, tzinfo=UTC)


def evaluate_source_completion(
    source: AlternativeDataSource, execution_time: datetime
) -> LeakageDecision:
    """Reject a completed-source claim whose end lies after execution."""

    if execution_time.tzinfo is None:
        raise ValueError("execution_time must be timezone-aware")
    if source.coverage_end is not None and source.coverage_end > execution_time.astimezone(UTC):
        return LeakageDecision(
            GateDisposition.ERROR, AlternativeDataReasonCode.FUTURE_TIMESTAMP
        )
    return ELIGIBLE


def evaluate_credit_coverage(
    coverage: CreditCoverage,
    window: ObservationWindow,
    execution_time: datetime,
) -> LeakageDecision:
    """Prevent post-decision coverage evidence from defining a consumer stratum."""

    if execution_time.tzinfo is None:
        raise ValueError("execution_time must be timezone-aware")
    if coverage.assessed_at > execution_time.astimezone(UTC):
        return LeakageDecision(
            GateDisposition.ERROR, AlternativeDataReasonCode.FUTURE_TIMESTAMP
        )
    if coverage.assessed_at > window.as_of_time:
        return LeakageDecision(
            GateDisposition.EXCLUDE,
            AlternativeDataReasonCode.OBSERVED_AFTER_DECISION,
        )
    return ELIGIBLE


def evaluate_feature_record(
    record: SignalRecord,
    window: ObservationWindow,
    execution_time: datetime,
) -> LeakageDecision:
    """Apply the normative feature rows in the AD-0 leakage truth table."""

    if execution_time.tzinfo is None:
        raise ValueError("execution_time must be timezone-aware")
    execution = execution_time.astimezone(UTC)
    evidence_end = _instant(record.evidence_end, end_of_day=True)
    if evidence_end > execution or record.observed_at > execution:
        return LeakageDecision(
            GateDisposition.ERROR, AlternativeDataReasonCode.FUTURE_TIMESTAMP
        )
    if evidence_end > window.as_of_time:
        return LeakageDecision(
            GateDisposition.ERROR, AlternativeDataReasonCode.FEATURE_AFTER_DECISION
        )
    if record.observed_at > window.as_of_time:
        code = (
            AlternativeDataReasonCode.REVISION_AFTER_DECISION
            if record.revision_of is not None
            else AlternativeDataReasonCode.OBSERVED_AFTER_DECISION
        )
        return LeakageDecision(GateDisposition.EXCLUDE, code)
    if record.status == RecordStatus.PENDING:
        return LeakageDecision(
            GateDisposition.UNAVAILABLE, AlternativeDataReasonCode.PENDING_RECORD
        )
    return ELIGIBLE


def evaluate_outcome_record(
    record: SignalRecord,
    window: ObservationWindow,
    execution_time: datetime,
) -> LeakageDecision:
    """Apply the normative outcome and maturity rows in the truth table."""

    if execution_time.tzinfo is None:
        raise ValueError("execution_time must be timezone-aware")
    execution = execution_time.astimezone(UTC)
    if record.observed_at > execution or _instant(
        record.evidence_end, end_of_day=True
    ) > execution:
        return LeakageDecision(
            GateDisposition.ERROR, AlternativeDataReasonCode.FUTURE_TIMESTAMP
        )
    if not window.label_is_mature(execution):
        return LeakageDecision(
            GateDisposition.UNAVAILABLE, AlternativeDataReasonCode.LABEL_IMMATURE
        )
    start = _instant(record.evidence_start)
    end = _instant(record.evidence_end, end_of_day=True)
    if start <= window.as_of_time:
        return LeakageDecision(
            GateDisposition.ERROR,
            AlternativeDataReasonCode.OUTCOME_NOT_POST_DECISION,
        )
    if start < window.performance_start or end > window.performance_end:
        return LeakageDecision(
            GateDisposition.EXCLUDE,
            AlternativeDataReasonCode.OUTCOME_OUTSIDE_WINDOW,
        )
    return ELIGIBLE


def select_authoritative_feature_records(
    records: Iterable[SignalRecord],
    sources: Iterable[AlternativeDataSource],
    window: ObservationWindow,
    execution_time: datetime,
) -> tuple[SignalRecord, ...]:
    """Validate revision graphs and retain each decision-time terminal version."""

    source_items = tuple(sources)
    source_map = {source.source_id: source for source in source_items}
    if len(source_map) != len(source_items):
        raise ValueError("source_id values must be unique")
    items = tuple(records)
    identities: dict[tuple[str, str, str], SignalRecord] = {}
    for record in items:
        source = source_map.get(record.source_id)
        if source is None:
            raise ValueError(AlternativeDataReasonCode.SOURCE_NOT_DECLARED.value)
        if record.signal_family != source.signal_family:
            raise ValueError(AlternativeDataReasonCode.SOURCE_FAMILY_MISMATCH.value)
        if record.source_version != source.source_version:
            raise ValueError(AlternativeDataReasonCode.SOURCE_VERSION_MISMATCH.value)
        identity = (record.source_id, record.source_version, record.record_id)
        if identity in identities:
            raise ValueError(AlternativeDataReasonCode.DUPLICATE_RECORD_IDENTITY.value)
        identities[identity] = record

    for record in items:
        for target_id, missing_code in (
            (record.revision_of, AlternativeDataReasonCode.REVISION_TARGET_MISSING),
            (record.reversal_of, AlternativeDataReasonCode.REVERSAL_TARGET_MISSING),
        ):
            if target_id is None:
                continue
            target = identities.get((record.source_id, record.source_version, target_id))
            if target is None:
                raise ValueError(missing_code.value)
            if (
                target.entity_id != record.entity_id
                or target.signal_family != record.signal_family
                or target.currency != record.currency
            ):
                raise ValueError(AlternativeDataReasonCode.LINKAGE_FAMILY_MISMATCH.value)
            if target.observed_at > record.observed_at:
                raise ValueError(AlternativeDataReasonCode.NON_MONOTONIC_HISTORY.value)

    revision_parent = {
        (record.source_id, record.source_version, record.record_id): (
            record.source_id,
            record.source_version,
            record.revision_of,
        )
        for record in items
        if record.revision_of is not None
    }
    for identity in revision_parent:
        seen: set[tuple[str, str, str]] = set()
        cursor = identity
        while cursor in revision_parent:
            if cursor in seen:
                raise ValueError(AlternativeDataReasonCode.NON_MONOTONIC_HISTORY.value)
            seen.add(cursor)
            cursor = revision_parent[cursor]

    eligible = {
        (record.source_id, record.source_version, record.record_id): record
        for record in items
        if evaluate_feature_record(record, window, execution_time).disposition
        == GateDisposition.ELIGIBLE
    }
    revised_targets = {
        (record.source_id, record.source_version, record.revision_of)
        for record in eligible.values()
        if record.revision_of is not None
    }
    terminal = [
        record for identity, record in eligible.items() if identity not in revised_targets
    ]
    roots: dict[tuple[str, str, str], SignalRecord] = {}
    for record in terminal:
        root = (record.source_id, record.source_version, record.record_id)
        while root in revision_parent:
            root = revision_parent[root]
        current = roots.get(root)
        if current is None or (current.observed_at, current.record_id) < (
            record.observed_at,
            record.record_id,
        ):
            roots[root] = record
    return tuple(
        sorted(
            roots.values(),
            key=lambda record: (
                record.source_id,
                record.entity_id,
                record.observed_at,
                record.record_id,
            ),
        )
    )
