"""Offline integrity and leakage guards for the external CTU Financial source."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from hashlib import sha256
import json
from typing import Iterable, Mapping, Sequence

DISPOSITION = "external_only"
DATABASE = "financial"
EXPECTED_COLUMNS = {
    "account": ("account_id", "district_id", "frequency", "date"),
    "card": ("card_id", "disp_id", "type", "issued"),
    "client": ("client_id", "gender", "birth_date", "district_id"),
    "disp": ("disp_id", "client_id", "account_id", "type"),
    "district": (
        "district_id", "A2", "A3", "A4", "A5", "A6", "A7", "A8",
        "A9", "A10", "A11", "A12", "A13", "A14", "A15", "A16",
    ),
    "loan": ("loan_id", "account_id", "date", "amount", "duration", "payments", "status"),
    "order": ("order_id", "account_id", "bank_to", "account_to", "amount", "k_symbol"),
    "trans": (
        "trans_id", "account_id", "date", "type", "operation", "amount",
        "balance", "k_symbol", "bank", "account",
    ),
}
EXPECTED_STATUS_COUNTS = {"A": 203, "B": 31, "C": 403, "D": 45}
SCHEMA_SHA256 = "cd494eba2b2b80aaaf74ca0c32bb3d43ea76bff87d7a12976ed89c451c8ae129"
TOTAL_ROWS = 1_079_680
TOTAL_COLUMNS = 55
TABLE_SNAPSHOTS = {
    "account": (4500, 4, "75968bd956668686bee3c0862737978dbaa5e80e3bcbe4a384236fa4ff9ea75a"),
    "card": (892, 4, "51cc2d890df840d50b66525281fc1a9492445934e902ab672f899b2e780e7b09"),
    "client": (5369, 4, "0dc07b5120bcd726cdc6b2d9c229d14dd7ea02e97a1c454c5fb19e26e2510178"),
    "disp": (5369, 4, "ccb76a4d1b5255b8eb8c2d98ff45487f74eec4169e0a671a109c20eac7bfaaeb"),
    "district": (77, 16, "9d85a1bd8f7a0fcd85c238f3fc805ed4d65cd6420eb7fe0c259627dc7380c705"),
    "loan": (682, 7, "a2c331ee1a4f1bd97e4e6c56e431a805b97a18d3b4d443af15244510bae64d2f"),
    "order": (6471, 6, "9b88d5bbdc6534cd630fea9fa311aa3fd931a43fd73916f9f5c429d202b8af0a"),
    "trans": (1056320, 10, "7d7498d12f57d39b3c7d7e1e02c95321e3324fa97f008093b35e1f46f29eb3a0"),
}
TRANSACTION_CUTOFF_COUNTS = {
    "strictly_before_loan_date": 17_621,
    "same_day_as_loan_date": 55,
    "after_loan_date": 73_013,
    "finished_loans_with_strictly_before_transactions": 234,
    "finished_loans_with_same_day_transactions": 40,
    "finished_loans_with_after_transactions": 234,
}
FINISHED_STATUSES = frozenset({"A", "B"})
SENSITIVE_OR_LINKABLE_COLUMNS = frozenset(
    {
        "account_id", "account_to", "bank", "bank_to", "birth_date",
        "card_id", "client_id", "disp_id", "district_id", "gender",
        "loan_id", "order_id", "trans_id",
    }
)


class CtuFinancialIntegrityError(ValueError):
    """Raised when external CTU evaluation evidence violates the reviewed boundary."""


def validate_snapshot_summary(
    columns_by_table: Mapping[str, Sequence[str]],
    status_counts: Mapping[str, int],
    *,
    schema_sha256: str,
    total_rows: int,
    total_columns: int,
    table_snapshots: Mapping[str, Sequence[object]],
) -> None:
    """Validate exact aggregate evidence for the reviewed live snapshot."""
    normalized = {name: tuple(columns) for name, columns in columns_by_table.items()}
    if normalized != EXPECTED_COLUMNS:
        raise CtuFinancialIntegrityError("CTU Financial schema does not match the reviewed live source")
    if schema_sha256 != SCHEMA_SHA256:
        raise CtuFinancialIntegrityError("CTU Financial schema SHA-256 changed")
    if (total_rows, total_columns) != (TOTAL_ROWS, TOTAL_COLUMNS):
        raise CtuFinancialIntegrityError("CTU Financial total row or column count changed")
    normalized_tables = {name: tuple(values) for name, values in table_snapshots.items()}
    if normalized_tables != TABLE_SNAPSHOTS:
        raise CtuFinancialIntegrityError("CTU Financial table row, column, or SHA-256 evidence changed")
    if dict(status_counts) != EXPECTED_STATUS_COUNTS:
        raise CtuFinancialIntegrityError("CTU Financial loan status counts changed")


def finished_label(status: str) -> int:
    """Map only completed-loan statuses; unfinished C/D records fail closed."""
    if status == "A":
        return 1
    if status == "B":
        return 0
    raise CtuFinancialIntegrityError("only completed A/B loans are eligible")


def predecision_transaction_mask(
    transaction_dates: Sequence[date], loan_date: date
) -> tuple[bool, ...]:
    """Return the mandatory loan-date cutoff mask for externally queried rows."""
    if not transaction_dates:
        raise CtuFinancialIntegrityError("at least one transaction date is required")
    return tuple(transaction_date < loan_date for transaction_date in transaction_dates)


def canonical_table_sha256(
    table: str,
    schema: Sequence[Mapping[str, object]],
    rows: Iterable[Sequence[object]],
) -> str:
    """Reproduce the reviewed primary-key-ordered JSON-Lines table digest."""
    expected_schema_fields = {"name", "ordinal", "type", "nullable", "key"}
    normalized_schema = []
    for column in schema:
        if set(column) != expected_schema_fields:
            raise CtuFinancialIntegrityError("canonical schema fields are incomplete")
        normalized_schema.append(dict(column))
    digest = sha256()
    header = {"table": table, "columns": normalized_schema}
    digest.update((json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n").encode())
    width = len(normalized_schema)
    for row in rows:
        if len(row) != width:
            raise CtuFinancialIntegrityError("canonical row width does not match schema")
        payload = [_canonical_value(value) for value in row]
        digest.update(
            (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    raise CtuFinancialIntegrityError(f"unsupported canonical value type: {type(value).__name__}")
