"""Strict, framework-neutral contracts for alternative-data evidence."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

OpaqueId = str
CoverageLabel = str | int | bool
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_DURATION = re.compile(
    r"^P(?=\d|T\d)(?:(?P<years>\d+(?:\.\d+)?)Y)?"
    r"(?:(?P<months>\d+(?:\.\d+)?)M)?(?:(?P<weeks>\d+(?:\.\d+)?)W)?"
    r"(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )


class SignalFamily(StrEnum):
    CASH_FLOW = "cash_flow"
    RENT = "rent"
    UTILITY = "utility"


class AcquisitionMethod(StrEnum):
    CONSUMER_PERMISSIONED = "consumer_permissioned"
    CONSUMER_SUBMITTED = "consumer_submitted"
    PROVIDER_DIRECT = "provider_direct"
    PUBLIC_RECORD = "public_record"


class CurrencyPolicy(StrEnum):
    SINGLE_CURRENCY = "single_currency"
    RECORD_CURRENCY = "record_currency"


class RecordStatus(StrEnum):
    POSTED = "posted"
    PENDING = "pending"
    REVERSED = "reversed"
    ADJUSTED = "adjusted"
    UNAVAILABLE = "unavailable"


class TransferScope(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNCERTAIN = "uncertain"


class CashFlowEventType(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    BALANCE = "balance"
    FEE = "fee"
    TRANSFER = "transfer"
    REVERSAL = "reversal"


class RentEventType(StrEnum):
    OBLIGATION = "obligation"
    PAYMENT = "payment"
    PARTIAL_PAYMENT = "partial_payment"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"
    WAIVER = "waiver"
    REPORTING_UNAVAILABLE = "reporting_unavailable"


class UtilityEventType(StrEnum):
    BILL = "bill"
    PAYMENT = "payment"
    PARTIAL_PAYMENT = "partial_payment"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"
    ESTIMATED_BILL = "estimated_bill"
    SERVICE_INTERRUPTION = "service_interruption"
    REPORTING_UNAVAILABLE = "reporting_unavailable"


class SignalEventType(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    BALANCE = "balance"
    FEE = "fee"
    TRANSFER = "transfer"
    REVERSAL = "reversal"
    OBLIGATION = "obligation"
    PAYMENT = "payment"
    PARTIAL_PAYMENT = "partial_payment"
    ADJUSTMENT = "adjustment"
    WAIVER = "waiver"
    REPORTING_UNAVAILABLE = "reporting_unavailable"
    BILL = "bill"
    ESTIMATED_BILL = "estimated_bill"
    SERVICE_INTERRUPTION = "service_interruption"


def _non_blank(value: str, field: str) -> str:
    if not value or value != value.strip():
        raise ValueError(f"{field} must be non-empty without surrounding whitespace")
    return value


class AlternativeDataSource(StrictModel):
    source_id: OpaqueId
    signal_family: SignalFamily
    provider_id: OpaqueId
    acquisition_method: AcquisitionMethod
    permission_reference: OpaqueId
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime | None
    refresh_cadence: str
    source_timezone: str
    currency_policy: CurrencyPolicy
    default_currency: str | None
    source_version: str

    @field_validator(
        "source_id",
        "provider_id",
        "permission_reference",
        "source_version",
    )
    @classmethod
    def validate_identifier(cls, value: str, info: object) -> str:
        return _non_blank(value, getattr(info, "field_name", "identifier"))

    @field_validator("coverage_start", "coverage_end")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        return None if value is None else value.astimezone(UTC)

    @field_validator("refresh_cadence")
    @classmethod
    def validate_duration(cls, value: str) -> str:
        match = _DURATION.fullmatch(value)
        if match is None:
            raise ValueError("refresh_cadence must be a positive ISO 8601 duration")
        total = sum(float(part or 0) for part in match.groupdict().values())
        if total <= 0:
            raise ValueError("refresh_cadence must be positive")
        return value

    @field_validator("source_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("source_timezone must be an IANA timezone") from error
        return value

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is not None and _CURRENCY.fullmatch(value) is None:
            raise ValueError("default_currency must be an uppercase ISO 4217 code")
        return value

    @model_validator(mode="after")
    def validate_source_semantics(self) -> "AlternativeDataSource":
        if self.coverage_end is not None and self.coverage_end < self.coverage_start:
            raise ValueError("coverage_end cannot precede coverage_start")
        has_default = self.default_currency is not None
        if has_default != (self.currency_policy == CurrencyPolicy.SINGLE_CURRENCY):
            raise ValueError(
                "default_currency is required only for single_currency sources"
            )
        return self


class ObservationWindow(StrictModel):
    as_of_time: AwareDatetime
    feature_start: AwareDatetime
    feature_end: AwareDatetime
    performance_start: AwareDatetime
    performance_end: AwareDatetime
    label_maturity_time: AwareDatetime
    outcome_definition: str

    @field_validator(
        "as_of_time",
        "feature_start",
        "feature_end",
        "performance_start",
        "performance_end",
        "label_maturity_time",
    )
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("outcome_definition")
    @classmethod
    def validate_outcome_definition(cls, value: str) -> str:
        return _non_blank(value, "outcome_definition")

    @model_validator(mode="after")
    def validate_window_order(self) -> "ObservationWindow":
        if not (
            self.feature_start
            <= self.feature_end
            <= self.as_of_time
            < self.performance_start
            <= self.performance_end
            <= self.label_maturity_time
        ):
            raise ValueError(
                "window order must satisfy feature_start <= feature_end <= "
                "as_of_time < performance_start <= performance_end <= "
                "label_maturity_time"
            )
        return self

    def label_is_mature(self, execution_time: datetime) -> bool:
        if execution_time.tzinfo is None:
            raise ValueError("execution_time must be timezone-aware")
        return self.label_maturity_time <= execution_time.astimezone(UTC)


class CreditCoverage(StrictModel):
    entity_id: OpaqueId
    coverage_stratum: CoverageLabel | None
    definition_id: str
    assessed_at: AwareDatetime
    evidence_available: bool

    @field_validator("entity_id", "definition_id")
    @classmethod
    def validate_identifiers(cls, value: str, info: object) -> str:
        return _non_blank(value, getattr(info, "field_name", "identifier"))

    @field_validator("assessed_at")
    @classmethod
    def normalize_assessed_at(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_availability(self) -> "CreditCoverage":
        if self.evidence_available != (self.coverage_stratum is not None):
            raise ValueError(
                "coverage_stratum is required exactly when evidence is available"
            )
        return self


class AlternativeDataConfig(StrictModel):
    """Run-level AD-0 configuration without analytical metric policy."""

    sources: tuple[AlternativeDataSource, ...] = Field(min_length=1)
    observation_window: ObservationWindow
    execution_time: AwareDatetime
    allowed_coverage_strata: tuple[CoverageLabel, ...] = Field(min_length=1)
    minimum_report_cell_count: int = Field(ge=10)

    @field_validator("execution_time")
    @classmethod
    def normalize_execution_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_run_contract(self) -> "AlternativeDataConfig":
        source_ids = tuple(source.source_id for source in self.sources)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_id values must be unique")
        if any(
            type(value) is type(earlier) and value == earlier
            for index, value in enumerate(self.allowed_coverage_strata)
            for earlier in self.allowed_coverage_strata[:index]
        ):
            raise ValueError("allowed_coverage_strata must be type-sensitively unique")
        return self


class SignalRecord(StrictModel):
    entity_id: OpaqueId
    record_id: OpaqueId
    source_id: OpaqueId
    signal_family: SignalFamily
    event_type: SignalEventType
    event_time: AwareDatetime | date | None = None
    period_start: AwareDatetime | date | None = None
    period_end: AwareDatetime | date | None = None
    observed_at: AwareDatetime
    amount: Decimal | None = None
    currency: str | None = None
    status: RecordStatus
    revision_of: OpaqueId | None = None
    reversal_of: OpaqueId | None = None
    source_version: str
    transfer_scope: TransferScope | None = None
    category_id: str | None = None
    obligation_id: str | None = None
    due_date: date | None = None
    provider_id: str | None = None
    service_type: str | None = None

    @field_validator(
        "entity_id",
        "record_id",
        "source_id",
        "source_version",
        "revision_of",
        "reversal_of",
        "category_id",
        "obligation_id",
        "provider_id",
        "service_type",
    )
    @classmethod
    def validate_optional_identifiers(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        return _non_blank(value, getattr(info, "field_name", "identifier"))

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("amount", mode="before")
    @classmethod
    def parse_decimal_string(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("amount must be supplied as a decimal string")
        try:
            amount = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("amount must be a finite decimal string") from error
        if not amount.is_finite():
            raise ValueError("amount must be finite")
        return amount

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    @field_validator("currency")
    @classmethod
    def validate_record_currency(cls, value: str | None) -> str | None:
        if value is not None and _CURRENCY.fullmatch(value) is None:
            raise ValueError("currency must be an uppercase ISO 4217 code")
        return value

    @model_validator(mode="after")
    def validate_record_semantics(self) -> "SignalRecord":
        point = self.event_time is not None
        period = self.period_start is not None or self.period_end is not None
        if point == period or (period and None in (self.period_start, self.period_end)):
            raise ValueError("configure exactly event_time or both period boundaries")
        if period and self.period_end < self.period_start:  # type: ignore[operator]
            raise ValueError("period_end cannot precede period_start")
        allowed_types = {
            SignalFamily.CASH_FLOW: {item.value for item in CashFlowEventType},
            SignalFamily.RENT: {item.value for item in RentEventType},
            SignalFamily.UTILITY: {item.value for item in UtilityEventType},
        }[self.signal_family]
        if self.event_type.value not in allowed_types:
            raise ValueError("event_type does not belong to signal_family")
        if self.amount is not None and self.currency is None:
            raise ValueError("currency is required when amount is present")
        if (
            self.event_type == SignalEventType.REVERSAL
            or self.status == RecordStatus.REVERSED
        ) and self.reversal_of is None:
            raise ValueError("reversal records require reversal_of")
        self._validate_family_payload()
        return self

    def _validate_family_payload(self) -> None:
        if self.signal_family == SignalFamily.CASH_FLOW:
            monetary = self.event_type != SignalEventType.REVERSAL
            if monetary and self.amount is None:
                raise ValueError("cash-flow monetary events require amount")
            if (
                self.amount is not None
                and self.event_type != SignalEventType.BALANCE
                and self.amount < 0
            ):
                raise ValueError("cash-flow amounts are non-negative except balances")
            if (self.event_type == SignalEventType.TRANSFER) != (
                self.transfer_scope is not None
            ):
                raise ValueError("transfer_scope is required only for transfers")
        elif self.signal_family == SignalFamily.RENT:
            if self.event_type == SignalEventType.OBLIGATION and None in (
                self.amount,
                self.due_date,
                self.obligation_id,
            ):
                raise ValueError("rent obligations require amount, due_date, and obligation_id")
            if self.event_type in {
                SignalEventType.PAYMENT,
                SignalEventType.PARTIAL_PAYMENT,
                SignalEventType.ADJUSTMENT,
            } and self.obligation_id is None:
                raise ValueError("rent payment-like events require obligation_id")
            if self.event_type == SignalEventType.REPORTING_UNAVAILABLE and (
                self.event_time is not None or self.amount is not None
            ):
                raise ValueError("reporting_unavailable requires a period and no amount")
        else:
            if self.event_type in {SignalEventType.BILL, SignalEventType.ESTIMATED_BILL}:
                if None in (
                    self.amount,
                    self.due_date,
                    self.obligation_id,
                    self.provider_id,
                    self.service_type,
                ) or self.period_start is None:
                    raise ValueError(
                        "utility bills require period, due date, amount, provider, "
                        "service type, and obligation_id"
                    )
            if self.event_type in {
                SignalEventType.PAYMENT,
                SignalEventType.PARTIAL_PAYMENT,
                SignalEventType.ADJUSTMENT,
            } and self.obligation_id is None:
                raise ValueError("utility payment-like events require obligation_id")
            if self.event_type == SignalEventType.REPORTING_UNAVAILABLE and (
                self.event_time is not None or self.amount is not None
            ):
                raise ValueError("reporting_unavailable requires a period and no amount")

    @property
    def evidence_start(self) -> datetime | date:
        return self.event_time if self.event_time is not None else self.period_start  # type: ignore[return-value]

    @property
    def evidence_end(self) -> datetime | date:
        return self.event_time if self.event_time is not None else self.period_end  # type: ignore[return-value]


class SafeSignalProjection(StrictModel):
    """Deliberately excludes every consumer and linkage identifier."""

    source_id: str
    source_version: str
    signal_family: SignalFamily
    provider_id: str | None
    event_type: SignalEventType
    status: RecordStatus


def report_safe_projection(record: SignalRecord) -> SafeSignalProjection:
    return SafeSignalProjection(
        source_id=record.source_id,
        source_version=record.source_version,
        signal_family=record.signal_family,
        provider_id=record.provider_id,
        event_type=record.event_type,
        status=record.status,
    )
