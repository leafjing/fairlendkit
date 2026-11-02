"""Offline integrity and leakage guards for the external CTU Financial source."""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

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
) -> None:
    """Validate the reviewed live schema and its four-state loan labels."""
    normalized = {name: tuple(columns) for name, columns in columns_by_table.items()}
    if normalized != EXPECTED_COLUMNS:
        raise CtuFinancialIntegrityError("CTU Financial schema does not match the reviewed live source")
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
    return tuple(transaction_date <= loan_date for transaction_date in transaction_dates)
