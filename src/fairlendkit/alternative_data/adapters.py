"""Strict, explicit external-row adapters for AD-2 signal families."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import Field, ValidationError, model_validator

from fairlendkit.alternative_data.contracts import (
    AlternativeDataSource,
    SignalFamily,
    SignalRecord,
    StrictModel,
)
from fairlendkit.alternative_data.reasons import AlternativeDataReasonCode


class SignalRecordFieldMap(StrictModel):
    """Explicit external-to-canonical mapping; nothing is inferred."""

    fields: dict[str, str] = Field(min_length=1)
    constants: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_mapping(self) -> "SignalRecordFieldMap":
        canonical = set(SignalRecord.model_fields)
        if not set(self.fields).issubset(canonical) or not set(self.constants).issubset(
            canonical
        ):
            raise ValueError("adapter mapping contains an unknown canonical field")
        if set(self.fields) & set(self.constants):
            raise ValueError("adapter fields and constants cannot define the same field")
        external = tuple(self.fields.values())
        if len(external) != len(set(external)):
            raise ValueError("one external field cannot populate multiple canonical fields")
        return self


def adapt_cash_flow_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    mapping: SignalRecordFieldMap,
    source: AlternativeDataSource,
) -> tuple[SignalRecord, ...]:
    return _adapt(rows, mapping, source, SignalFamily.CASH_FLOW)


def adapt_rent_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    mapping: SignalRecordFieldMap,
    source: AlternativeDataSource,
) -> tuple[SignalRecord, ...]:
    return _adapt(rows, mapping, source, SignalFamily.RENT)


def adapt_utility_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    mapping: SignalRecordFieldMap,
    source: AlternativeDataSource,
) -> tuple[SignalRecord, ...]:
    return _adapt(rows, mapping, source, SignalFamily.UTILITY)


def _adapt(
    rows: Iterable[Mapping[str, Any]],
    mapping: SignalRecordFieldMap,
    source: AlternativeDataSource,
    family: SignalFamily,
) -> tuple[SignalRecord, ...]:
    if source.signal_family != family:
        raise ValueError("adapter family must match the declared source family")
    expected_external = set(mapping.fields.values())
    records = []
    for row in rows:
        keys = set(row)
        if keys != expected_external:
            missing = expected_external - keys
            if missing:
                raise ValueError(AlternativeDataReasonCode.MISSING_REQUIRED_FIELD.value)
            raise ValueError(AlternativeDataReasonCode.UNKNOWN_FIELD.value)
        payload = {
            canonical: row[external]
            for canonical, external in mapping.fields.items()
        }
        payload.update(mapping.constants)
        for name, expected in (
            ("source_id", source.source_id),
            ("source_version", source.source_version),
            ("signal_family", family.value),
        ):
            supplied = payload.setdefault(name, expected)
            if supplied != expected:
                raise ValueError(f"adapter {name} must match its source contract")
        try:
            records.append(SignalRecord.model_validate(payload))
        except ValidationError as error:
            event_errors = {
                tuple(item["loc"])
                for item in error.errors(include_input=False, include_url=False)
            }
            messages = " ".join(
                str(item["msg"])
                for item in error.errors(include_input=False, include_url=False)
            )
            if ("event_type",) in event_errors:
                code = AlternativeDataReasonCode.UNSUPPORTED_EVENT_TYPE
            elif "require" in messages or "missing" in messages:
                code = AlternativeDataReasonCode.MISSING_REQUIRED_FIELD
            elif "amount" in messages:
                code = AlternativeDataReasonCode.INVALID_AMOUNT
            else:
                raise
            raise ValueError(code.value) from None
    return tuple(records)
