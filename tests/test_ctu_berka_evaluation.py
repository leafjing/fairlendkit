from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest

from fairlendkit.research.ctu_berka import (
    CtuFinancialIntegrityError,
    DISPOSITION,
    EXPECTED_COLUMNS,
    EXPECTED_STATUS_COUNTS,
    SCHEMA_SHA256,
    SENSITIVE_OR_LINKABLE_COLUMNS,
    TABLE_SNAPSHOTS,
    TOTAL_COLUMNS,
    TOTAL_ROWS,
    TRANSACTION_CUTOFF_COUNTS,
    canonical_table_sha256,
    finished_label,
    predecision_transaction_mask,
    validate_snapshot_summary,
)


def test_reviewed_external_snapshot_summary_is_accepted() -> None:
    validate_snapshot_summary(
        EXPECTED_COLUMNS,
        EXPECTED_STATUS_COUNTS,
        schema_sha256=SCHEMA_SHA256,
        total_rows=TOTAL_ROWS,
        total_columns=TOTAL_COLUMNS,
        table_snapshots=TABLE_SNAPSHOTS,
    )
    assert DISPOSITION == "external_only"
    assert sum(EXPECTED_STATUS_COUNTS.values()) == 682
    assert EXPECTED_STATUS_COUNTS["A"] + EXPECTED_STATUS_COUNTS["B"] == 234


def test_snapshot_schema_and_status_drift_fail_closed() -> None:
    wrong_schema = {**EXPECTED_COLUMNS, "loan": EXPECTED_COLUMNS["loan"][:-1]}
    with pytest.raises(CtuFinancialIntegrityError, match="schema"):
        validate_snapshot_summary(
            wrong_schema,
            EXPECTED_STATUS_COUNTS,
            schema_sha256=SCHEMA_SHA256,
            total_rows=TOTAL_ROWS,
            total_columns=TOTAL_COLUMNS,
            table_snapshots=TABLE_SNAPSHOTS,
        )

    wrong_counts = {**EXPECTED_STATUS_COUNTS, "B": 32}
    with pytest.raises(CtuFinancialIntegrityError, match="counts"):
        validate_snapshot_summary(
            EXPECTED_COLUMNS,
            wrong_counts,
            schema_sha256=SCHEMA_SHA256,
            total_rows=TOTAL_ROWS,
            total_columns=TOTAL_COLUMNS,
            table_snapshots=TABLE_SNAPSHOTS,
        )


@pytest.mark.parametrize("drift", ["schema_hash", "total_rows", "table_rows", "table_hash"])
def test_snapshot_integrity_evidence_drift_fails_closed(drift: str) -> None:
    schema_hash = SCHEMA_SHA256
    total_rows = TOTAL_ROWS
    tables = dict(TABLE_SNAPSHOTS)
    if drift == "schema_hash":
        schema_hash = "0" * 64
    elif drift == "total_rows":
        total_rows += 1
    elif drift == "table_rows":
        _, columns, digest = tables["loan"]
        tables["loan"] = (683, columns, digest)
    else:
        rows, columns, _ = tables["loan"]
        tables["loan"] = (rows, columns, "0" * 64)
    with pytest.raises(CtuFinancialIntegrityError):
        validate_snapshot_summary(
            EXPECTED_COLUMNS,
            EXPECTED_STATUS_COUNTS,
            schema_sha256=schema_hash,
            total_rows=total_rows,
            total_columns=TOTAL_COLUMNS,
            table_snapshots=tables,
        )


def test_only_completed_a_b_loans_are_eligible() -> None:
    assert finished_label("A") == 1
    assert finished_label("B") == 0
    for unfinished in ("C", "D"):
        with pytest.raises(CtuFinancialIntegrityError, match="completed A/B"):
            finished_label(unfinished)


def test_transaction_cutoff_excludes_post_loan_rows() -> None:
    mask = predecision_transaction_mask(
        (date(1996, 1, 1), date(1996, 2, 1), date(1996, 2, 2)),
        date(1996, 2, 1),
    )
    assert mask == (True, False, False)
    with pytest.raises(CtuFinancialIntegrityError, match="at least one"):
        predecision_transaction_mask((), date(1996, 2, 1))


def test_linkable_and_sensitive_fields_are_explicitly_blocked() -> None:
    assert {"birth_date", "gender", "district_id", "account_id", "client_id"} <= (
        SENSITIVE_OR_LINKABLE_COLUMNS
    )


def test_canonical_table_hash_is_deterministic_and_structure_sensitive() -> None:
    schema = (
        {"name": "id", "ordinal": 1, "type": "int(11)", "nullable": "NO", "key": "PRI"},
        {"name": "amount", "ordinal": 2, "type": "decimal(6,2)", "nullable": "YES", "key": ""},
        {"name": "date", "ordinal": 3, "type": "date", "nullable": "NO", "key": ""},
    )
    rows = ((1, Decimal("10.20"), date(1996, 1, 1)), (2, None, date(1996, 1, 2)))
    digest = canonical_table_sha256("synthetic", schema, rows)
    assert digest == "1f80a953f0b336852511e4a3ba17129d0768423f34a083f9b1cb6cf27472bb0c"
    assert canonical_table_sha256("synthetic", schema, reversed(rows)) != digest
    with pytest.raises(CtuFinancialIntegrityError, match="row width"):
        canonical_table_sha256("synthetic", schema, ((1, Decimal("10.20")),))


def test_manifest_pins_only_aggregate_external_evidence() -> None:
    manifest = json.loads(
        Path("docs/data-sources/ctu-berka-financial-evaluation-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["disposition"] == "external_only"
    assert manifest["schema_sha256"] == SCHEMA_SHA256
    assert manifest["total_rows"] == TOTAL_ROWS
    assert manifest["total_columns"] == TOTAL_COLUMNS
    assert manifest["loan_status_counts"] == EXPECTED_STATUS_COUNTS
    assert manifest["finished_ab_loans"] == 234
    observed_tables = {
        name: (values["rows"], values["columns"], values["sha256"])
        for name, values in manifest["tables"].items()
    }
    assert observed_tables == TABLE_SNAPSHOTS
    assert manifest["finished_loan_transaction_counts"] == TRANSACTION_CUTOFF_COUNTS
    assert manifest["raw_or_transformed_data_committed"] is False
