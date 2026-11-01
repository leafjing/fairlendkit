"""Common AD-1 eligibility, temporal integrity, and coverage evidence."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import Iterable

from pydantic import AwareDatetime, Field, field_validator, model_validator

from fairlendkit.alternative_data.contracts import (
    AlternativeDataConfig,
    AlternativeDataSource,
    CreditCoverage,
    CurrencyPolicy,
    RecordStatus,
    SignalEventType,
    SignalFamily,
    SignalRecord,
    StrictModel,
    TransferScope,
)
from fairlendkit.alternative_data.leakage import (
    GateDisposition,
    evaluate_credit_coverage,
    evaluate_feature_record,
    evaluate_source_completion,
    select_authoritative_feature_records,
)
from fairlendkit.alternative_data.reasons import (
    AlternativeDataDisposition,
    AlternativeDataReasonCode,
    REASON_CONTRACT,
)

GroupLabel = str | int | bool


class QualityScopeKind(StrEnum):
    OVERALL = "overall"
    SIGNAL_FAMILY = "signal_family"
    COVERAGE = "coverage"
    AUDIT_GROUP = "audit_group"


class QualityEvidenceUnit(StrEnum):
    RECORD = "record"
    ENTITY = "entity"


class QualityPopulationEntity(StrictModel):
    """Sensitive run input; the entity identity never enters quality results."""

    entity_id: str = Field(min_length=1)
    audit_groups: dict[str, GroupLabel] = Field(default_factory=dict)

    @field_validator("entity_id")
    @classmethod
    def reject_identifier_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("entity_id cannot contain surrounding whitespace")
        return value

    @field_validator("audit_groups")
    @classmethod
    def validate_group_names(cls, value: dict[str, GroupLabel]) -> dict[str, GroupLabel]:
        if any(not name or name != name.strip() for name in value):
            raise ValueError("audit group names must be non-blank")
        return value


class QualityReasonCount(StrictModel):
    code: AlternativeDataReasonCode
    disposition: AlternativeDataDisposition
    count: int = Field(ge=1)
    unit: QualityEvidenceUnit
    denominator: int = Field(ge=1)
    signal_family: SignalFamily | None = None
    message: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_disposition(self) -> "QualityReasonCount":
        if REASON_CONTRACT[self.code] != (self.disposition, self.message):
            raise ValueError("reason disposition and message must match the contract")
        if self.count > self.denominator:
            raise ValueError("reason count cannot exceed its explicit denominator")
        if (
            self.code == AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED
            and self.signal_family is None
        ):
            raise ValueError("signal-not-provided evidence requires signal_family")
        return self


class ProviderCoverage(StrictModel):
    source_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    signal_family: SignalFamily
    entity_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    entity_coverage_rate: float = Field(ge=0.0, le=1.0)


class QualityScopeResult(StrictModel):
    scope_key: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    scope_kind: QualityScopeKind
    signal_family: SignalFamily | None = None
    attribute: str | None = None
    group: GroupLabel | None = None
    entity_count: int = Field(ge=0)
    input_record_count: int = Field(ge=0)
    authoritative_record_count: int = Field(ge=0)
    eligible_record_count: int = Field(ge=0)
    excluded_record_count: int = Field(ge=0)
    unavailable_record_count: int = Field(ge=0)
    excluded_entity_count: int = Field(ge=0)
    unavailable_entity_count: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    reversal_count: int = Field(ge=0)
    observation_start: AwareDatetime | None = None
    observation_end: AwareDatetime | None = None
    observation_duration_seconds: float | None = Field(default=None, ge=0.0)
    freshness_seconds: float | None = Field(default=None, ge=0.0)
    refresh_lag_seconds: float | None = Field(default=None, ge=0.0)
    providers: tuple[ProviderCoverage, ...]
    reasons: tuple[QualityReasonCount, ...]

    @model_validator(mode="after")
    def validate_counts_and_time(self) -> "QualityScopeResult":
        if self.authoritative_record_count > self.eligible_record_count:
            raise ValueError("authoritative records must be a subset of eligible records")
        if (
            self.input_record_count
            != self.eligible_record_count
            + self.excluded_record_count
            + self.unavailable_record_count
        ):
            raise ValueError("record eligibility counts must reconcile to input records")
        if self.scope_kind == QualityScopeKind.OVERALL:
            if self.attribute is not None or self.group is not None:
                raise ValueError("overall scope cannot carry a group")
            if self.signal_family is not None:
                raise ValueError("overall scope cannot carry a signal family")
        elif self.scope_kind == QualityScopeKind.SIGNAL_FAMILY:
            if self.signal_family is None or self.attribute is not None:
                raise ValueError("signal-family scope requires only signal_family")
        elif self.attribute is None:
            raise ValueError("grouped scopes require an attribute")
        time_values = (
            self.observation_start,
            self.observation_end,
            self.observation_duration_seconds,
            self.freshness_seconds,
            self.refresh_lag_seconds,
        )
        if self.authoritative_record_count == 0:
            if any(value is not None for value in time_values):
                raise ValueError("empty scopes cannot carry temporal summaries")
        elif any(value is None for value in time_values):
            raise ValueError("non-empty scopes require complete temporal summaries")
        return self


class AlternativeDataQualityResult(StrictModel):
    population_count: int = Field(ge=0)
    input_record_count: int = Field(ge=0)
    scopes: tuple[QualityScopeResult, ...]

    @model_validator(mode="after")
    def validate_scopes(self) -> "AlternativeDataQualityResult":
        keys = tuple(scope.scope_key for scope in self.scopes)
        if not keys or keys[0] != "overall":
            raise ValueError("quality results must begin with overall scope")
        if len(keys) != len(set(keys)):
            raise ValueError("quality scope keys must be unique")
        overall = self.scopes[0]
        if (
            overall.entity_count != self.population_count
            or overall.input_record_count != self.input_record_count
        ):
            raise ValueError("overall counts must match result metadata")
        return self


def calculate_quality_evidence(
    *,
    entities: Iterable[QualityPopulationEntity],
    records: Iterable[SignalRecord],
    coverages: Iterable[CreditCoverage],
    config: AlternativeDataConfig,
) -> AlternativeDataQualityResult:
    """Return deterministic aggregate quality evidence without behavior inference."""

    entity_items = tuple(entities)
    record_items = tuple(records)
    coverage_items = tuple(coverages)
    entity_map = {entity.entity_id: entity for entity in entity_items}
    if len(entity_map) != len(entity_items):
        raise ValueError("population entity identities must be unique")
    if any(record.entity_id not in entity_map for record in record_items):
        raise ValueError("every signal record must belong to the declared population")

    coverage_map = {coverage.entity_id: coverage for coverage in coverage_items}
    if len(coverage_map) != len(coverage_items):
        raise ValueError("credit coverage identities must be unique")
    if not set(coverage_map).issubset(entity_map):
        raise ValueError("credit coverage must belong to the declared population")

    for source in config.sources:
        decision = evaluate_source_completion(source, config.execution_time)
        if decision.disposition == GateDisposition.ERROR:
            raise ValueError(decision.reason_code.value)

    sources = {source.source_id: source for source in config.sources}
    record_reasons: dict[tuple[str, str, str], set[AlternativeDataReasonCode]] = {}
    entity_reasons: dict[
        str, list[tuple[AlternativeDataReasonCode, SignalFamily | None]]
    ] = {
        entity_id: [] for entity_id in entity_map
    }

    for entity_id in entity_map:
        coverage = coverage_map.get(entity_id)
        if coverage is None or not coverage.evidence_available:
            entity_reasons[entity_id].append(
                (AlternativeDataReasonCode.COVERAGE_STRATUM_UNAVAILABLE, None)
            )
            continue
        decision = evaluate_credit_coverage(
            coverage, config.observation_window, config.execution_time
        )
        if decision.disposition == GateDisposition.ERROR:
            raise ValueError(decision.reason_code.value)
        if decision.disposition == GateDisposition.EXCLUDE:
            entity_reasons[entity_id].append((decision.reason_code, None))
        if not _typed_contains(
            config.allowed_coverage_strata, coverage.coverage_stratum
        ):
            raise ValueError("coverage_stratum must belong to allowed_coverage_strata")

    for record in record_items:
        identity = _record_identity(record)
        source = sources.get(record.source_id)
        if source is None:
            raise ValueError(AlternativeDataReasonCode.SOURCE_NOT_DECLARED.value)
        reasons = record_reasons.setdefault(identity, set())
        if (
            source.currency_policy == CurrencyPolicy.SINGLE_CURRENCY
            and record.currency is not None
            and record.currency != source.default_currency
        ):
            reasons.add(AlternativeDataReasonCode.CURRENCY_INCONSISTENT)
        decision = evaluate_feature_record(
            record, config.observation_window, config.execution_time
        )
        if decision.disposition == GateDisposition.ERROR:
            raise ValueError(decision.reason_code.value)
        if decision.reason_code is not None:
            reasons.add(decision.reason_code)
        _add_record_observations(record, reasons)

    _add_signal_availability_reasons(
        entity_map, record_items, config, entity_reasons
    )
    # Validate every linkage before applying quality exclusions. This prevents
    # an excluded target from being misreported as a missing target.
    select_authoritative_feature_records(
        record_items,
        config.sources,
        config.observation_window,
        config.execution_time,
    )
    authoritative = _select_quality_authoritative(record_items, record_reasons)
    _add_period_integrity_reasons(authoritative, record_reasons)
    authoritative_ids = {_record_identity(record) for record in authoritative}

    scopes = [
        _scope(
            "overall",
            QualityScopeKind.OVERALL,
            None,
            None,
            None,
            set(entity_map),
        )
    ]
    for family in sorted(
        {source.signal_family for source in config.sources},
        key=lambda item: item.value,
    ):
        scopes.append(
            _scope(
                f"family.{family.value}",
                QualityScopeKind.SIGNAL_FAMILY,
                family,
                None,
                None,
                set(entity_map),
            )
        )
    coverage_values = sorted(
        config.allowed_coverage_strata, key=_typed_sort_key
    )
    for value in coverage_values:
        members = {
            entity_id
            for entity_id, coverage in coverage_map.items()
            if coverage.evidence_available
            and _typed_equal(coverage.coverage_stratum, value)
            and not any(
                code == AlternativeDataReasonCode.OBSERVED_AFTER_DECISION
                for code, _ in entity_reasons[entity_id]
            )
        }
        scopes.append(
            _scope(
                f"coverage.{_typed_token(value)}",
                QualityScopeKind.COVERAGE,
                None,
                "coverage_stratum",
                value,
                members,
            )
        )
    unavailable_coverage = {
        entity_id
        for entity_id in entity_map
        if entity_id not in coverage_map
        or not coverage_map[entity_id].evidence_available
        or any(
            code == AlternativeDataReasonCode.OBSERVED_AFTER_DECISION
            for code, _ in entity_reasons[entity_id]
        )
    }
    scopes.append(
        _scope(
            "coverage.unavailable",
            QualityScopeKind.COVERAGE,
            None,
            "coverage_stratum",
            None,
            unavailable_coverage,
        )
    )
    group_names = sorted(
        {name for entity in entity_items for name in entity.audit_groups}
    )
    for name in group_names:
        values = sorted(
            {
                _typed_token(entity.audit_groups[name]): entity.audit_groups[name]
                for entity in entity_items
                if name in entity.audit_groups
            }.values(),
            key=_typed_sort_key,
        )
        for value in values:
            members = {
                entity.entity_id
                for entity in entity_items
                if name in entity.audit_groups
                and _typed_equal(entity.audit_groups[name], value)
            }
            scopes.append(
                _scope(
                    f"group.{_typed_token(name)}.{_typed_token(value)}",
                    QualityScopeKind.AUDIT_GROUP,
                    None,
                    name,
                    value,
                    members,
                )
            )

    def assemble(
        spec: tuple[
            str,
            QualityScopeKind,
            SignalFamily | None,
            str | None,
            GroupLabel | None,
            set[str],
        ]
    ):
        key, kind, family, attribute, group, members = spec
        return _assemble_scope(
            key=key,
            kind=kind,
            family=family,
            attribute=attribute,
            group=group,
            members=members,
            records=record_items,
            authoritative_ids=authoritative_ids,
            record_reasons=record_reasons,
            entity_reasons=entity_reasons,
            sources=sources,
            as_of_time=config.observation_window.as_of_time,
        )

    results = tuple(assemble(spec) for spec in scopes)
    return AlternativeDataQualityResult(
        population_count=len(entity_items),
        input_record_count=len(record_items),
        scopes=results,
    )


def _scope(
    key: str,
    kind: QualityScopeKind,
    family: SignalFamily | None,
    attribute: str | None,
    group: GroupLabel | None,
    members: set[str],
) -> tuple[
    str,
    QualityScopeKind,
    SignalFamily | None,
    str | None,
    GroupLabel | None,
    set[str],
]:
    return key, kind, family, attribute, group, members


def _assemble_scope(
    *,
    key: str,
    kind: QualityScopeKind,
    family: SignalFamily | None,
    attribute: str | None,
    group: GroupLabel | None,
    members: set[str],
    records: tuple[SignalRecord, ...],
    authoritative_ids: set[tuple[str, str, str]],
    record_reasons: dict[tuple[str, str, str], set[AlternativeDataReasonCode]],
    entity_reasons: dict[
        str, list[tuple[AlternativeDataReasonCode, SignalFamily | None]]
    ],
    sources: dict[str, AlternativeDataSource],
    as_of_time: datetime,
) -> QualityScopeResult:
    scoped = tuple(
        record
        for record in records
        if record.entity_id in members
        and (family is None or record.signal_family == family)
    )
    authoritative = tuple(
        record for record in scoped if _record_identity(record) in authoritative_ids
    )
    record_denominators = {
        signal_family: sum(record.signal_family == signal_family for record in scoped)
        for signal_family in SignalFamily
    }
    eligible = 0
    excluded = 0
    unavailable = 0
    reason_counts: dict[
        tuple[AlternativeDataReasonCode, SignalFamily | None, QualityEvidenceUnit],
        int,
    ] = {}
    for record in scoped:
        dispositions = {
            REASON_CONTRACT[code][0]
            for code in record_reasons[_record_identity(record)]
        }
        if AlternativeDataDisposition.EXCLUDE in dispositions:
            excluded += 1
        elif AlternativeDataDisposition.UNAVAILABLE in dispositions:
            unavailable += 1
        else:
            eligible += 1
        for code in record_reasons[_record_identity(record)]:
            reason_key = (code, record.signal_family, QualityEvidenceUnit.RECORD)
            reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
    excluded_entities = 0
    unavailable_entities = 0
    for entity_id in members:
        codes = tuple(
            code
            for code, reason_family in entity_reasons[entity_id]
            if family is None or reason_family is None or reason_family == family
        )
        dispositions = {REASON_CONTRACT[code][0] for code in codes}
        if AlternativeDataDisposition.EXCLUDE in dispositions:
            excluded_entities += 1
        elif any(
            REASON_CONTRACT[code][0] == AlternativeDataDisposition.UNAVAILABLE
            for code in codes
        ):
            unavailable_entities += 1
        for code, reason_family in entity_reasons[entity_id]:
            if family is not None and reason_family not in (None, family):
                continue
            reason_key = (code, reason_family, QualityEvidenceUnit.ENTITY)
            reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1

    starts = tuple(_instant(record.evidence_start) for record in authoritative)
    ends = tuple(_instant(record.evidence_end, end_of_day=True) for record in authoritative)
    observed = tuple(record.observed_at for record in authoritative)
    observation_start = min(starts) if starts else None
    observation_end = max(ends) if ends else None
    duration = (
        (observation_end - observation_start).total_seconds()
        if observation_start is not None and observation_end is not None
        else None
    )
    freshness = (
        (as_of_time - observation_end).total_seconds()
        if observation_end is not None
        else None
    )
    refresh_lag = (
        (as_of_time - max(observed)).total_seconds() if observed else None
    )

    providers = []
    for source_id in sorted(
        source_id
        for source_id, source in sources.items()
        if family is None or source.signal_family == family
    ):
        source = sources[source_id]
        provider_records = tuple(
            record
            for record in authoritative
            if record.source_id == source_id
        )
        provider_entities = {record.entity_id for record in provider_records}
        providers.append(
            ProviderCoverage(
                source_id=source_id,
                provider_id=source.provider_id,
                signal_family=source.signal_family,
                entity_count=len(provider_entities),
                record_count=len(provider_records),
                entity_coverage_rate=(
                    len(provider_entities) / len(members) if members else 0.0
                ),
            )
        )

    reasons = tuple(
        QualityReasonCount(
            code=key[0],
            disposition=REASON_CONTRACT[key[0]][0],
            count=count,
            unit=key[2],
            denominator=(
                record_denominators[key[1]]
                if key[2] == QualityEvidenceUnit.RECORD and key[1] is not None
                else len(scoped)
                if key[2] == QualityEvidenceUnit.RECORD
                else len(members)
            ),
            signal_family=key[1],
            message=REASON_CONTRACT[key[0]][1],
        )
        for key, count in sorted(
            reason_counts.items(),
            key=lambda item: (
                item[0][0].value,
                "" if item[0][1] is None else item[0][1].value,
                item[0][2].value,
            ),
        )
    )
    return QualityScopeResult(
        scope_key=key,
        scope_kind=kind,
        signal_family=family,
        attribute=attribute,
        group=group,
        entity_count=len(members),
        input_record_count=len(scoped),
        authoritative_record_count=len(authoritative),
        eligible_record_count=eligible,
        excluded_record_count=excluded,
        unavailable_record_count=unavailable,
        excluded_entity_count=excluded_entities,
        unavailable_entity_count=unavailable_entities,
        revision_count=sum(record.revision_of is not None for record in scoped),
        reversal_count=sum(record.reversal_of is not None for record in scoped),
        observation_start=observation_start,
        observation_end=observation_end,
        observation_duration_seconds=duration,
        freshness_seconds=freshness,
        refresh_lag_seconds=refresh_lag,
        providers=tuple(providers),
        reasons=reasons,
    )


def _add_signal_availability_reasons(
    entities: dict[str, QualityPopulationEntity],
    records: tuple[SignalRecord, ...],
    config: AlternativeDataConfig,
    reasons: dict[
        str, list[tuple[AlternativeDataReasonCode, SignalFamily | None]]
    ],
) -> None:
    families = {source.signal_family for source in config.sources}
    observed = {(record.entity_id, record.signal_family) for record in records}
    for entity_id in entities:
        for family in sorted(families, key=lambda item: item.value):
            if (entity_id, family) not in observed:
                reasons[entity_id].append(
                    (AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED, family)
                )


def _add_record_observations(
    record: SignalRecord, reasons: set[AlternativeDataReasonCode]
) -> None:
    if record.status == RecordStatus.UNAVAILABLE or record.event_type == SignalEventType.REPORTING_UNAVAILABLE:
        reasons.add(AlternativeDataReasonCode.PROVIDER_REPORTING_GAP)
    if record.reversal_of is not None and record.signal_family == SignalFamily.CASH_FLOW:
        reasons.add(AlternativeDataReasonCode.CASHFLOW_REVERSAL_OBSERVED)
    if (
        record.signal_family == SignalFamily.CASH_FLOW
        and record.event_type in {SignalEventType.INFLOW, SignalEventType.OUTFLOW}
        and record.category_id is None
    ):
        reasons.add(AlternativeDataReasonCode.CASHFLOW_CATEGORY_UNRESOLVED)
    if record.transfer_scope == TransferScope.UNCERTAIN:
        reasons.add(AlternativeDataReasonCode.UNCERTAIN_TRANSFER)
    family_codes = {
        (SignalFamily.RENT, SignalEventType.PARTIAL_PAYMENT): AlternativeDataReasonCode.RENT_PARTIAL_PAYMENT_OBSERVED,
        (SignalFamily.RENT, SignalEventType.WAIVER): AlternativeDataReasonCode.RENT_WAIVER_OBSERVED,
        (SignalFamily.UTILITY, SignalEventType.ESTIMATED_BILL): AlternativeDataReasonCode.UTILITY_ESTIMATED_BILL_OBSERVED,
        (SignalFamily.UTILITY, SignalEventType.ADJUSTMENT): AlternativeDataReasonCode.UTILITY_ADJUSTMENT_OBSERVED,
        (SignalFamily.UTILITY, SignalEventType.SERVICE_INTERRUPTION): AlternativeDataReasonCode.SERVICE_INTERRUPTION_OBSERVED,
    }
    code = family_codes.get((record.signal_family, record.event_type))
    if code is not None:
        reasons.add(code)


def _add_period_integrity_reasons(
    records: tuple[SignalRecord, ...],
    reasons: dict[tuple[str, str, str], set[AlternativeDataReasonCode]],
) -> None:
    by_history: dict[tuple[str, str], list[SignalRecord]] = {}
    for record in records:
        if record.period_start is not None:
            by_history.setdefault((record.source_id, record.entity_id), []).append(record)
    for history in by_history.values():
        ordered = sorted(history, key=lambda record: _instant(record.period_start))
        for previous, current in zip(ordered, ordered[1:]):
            previous_end = _instant(previous.period_end, end_of_day=True)
            current_start = _instant(current.period_start)
            if current_start <= previous_end:
                reasons[_record_identity(previous)].add(
                    AlternativeDataReasonCode.PERIOD_OVERLAP
                )
                reasons[_record_identity(current)].add(
                    AlternativeDataReasonCode.PERIOD_OVERLAP
                )
            elif (current_start - previous_end).total_seconds() > 1.0:
                reasons[_record_identity(current)].add(
                    AlternativeDataReasonCode.TEMPORAL_GAP
                )


def _select_quality_authoritative(
    records: tuple[SignalRecord, ...],
    reasons: dict[tuple[str, str, str], set[AlternativeDataReasonCode]],
) -> tuple[SignalRecord, ...]:
    """Select terminal revisions after applying non-error quality dispositions."""

    eligible = {
        _record_identity(record): record
        for record in records
        if not any(
            REASON_CONTRACT[code][0]
            in {AlternativeDataDisposition.EXCLUDE, AlternativeDataDisposition.UNAVAILABLE}
            for code in reasons[_record_identity(record)]
        )
    }
    revised_targets = {
        (record.source_id, record.source_version, record.revision_of)
        for record in eligible.values()
        if record.revision_of is not None
    }
    terminal = tuple(
        record for identity, record in eligible.items() if identity not in revised_targets
    )
    parent = {
        _record_identity(record): (
            record.source_id,
            record.source_version,
            record.revision_of,
        )
        for record in records
        if record.revision_of is not None
    }
    by_root: dict[tuple[str, str, str], list[SignalRecord]] = {}
    for record in terminal:
        root = _record_identity(record)
        while root in parent:
            root = parent[root]
        by_root.setdefault(root, []).append(record)
    return tuple(
        sorted(
            (max(items, key=lambda item: item.observed_at) for items in by_root.values()),
            key=lambda item: (
                item.source_id,
                item.entity_id,
                item.observed_at,
                item.record_id,
            ),
        )
    )


def _record_identity(record: SignalRecord) -> tuple[str, str, str]:
    return record.source_id, record.source_version, record.record_id


def _instant(value: datetime | date, *, end_of_day: bool = False) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    return datetime.combine(value, time.max if end_of_day else time.min, tzinfo=UTC)


def _typed_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _typed_contains(values: tuple[GroupLabel, ...], expected: object) -> bool:
    return any(_typed_equal(value, expected) for value in values)


def _typed_sort_key(value: GroupLabel) -> tuple[str, str]:
    return type(value).__name__, json.dumps(value, ensure_ascii=False)


def _typed_token(value: GroupLabel) -> str:
    type_name, payload = _typed_sort_key(value)
    return f"{type_name}-{payload.encode('utf-8').hex()}"
