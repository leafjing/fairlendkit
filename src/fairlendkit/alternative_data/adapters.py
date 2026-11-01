"""Strict, explicit external-row adapters for AD-2 signal families."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import Field, model_validator

from fairlendkit.alternative_data.contracts import (
    AlternativeDataSource,
    SignalFamily,
    SignalRecord,
    StrictModel,
)


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
                raise ValueError("adapter row is missing an explicitly mapped field")
            raise ValueError("adapter row contains an unmapped external field")
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
        records.append(SignalRecord.model_validate(payload))
    return tuple(records)
