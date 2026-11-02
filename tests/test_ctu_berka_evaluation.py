from datetime import date
import json
from pathlib import Path

import pytest

from fairlendkit.research.ctu_berka import (
    CtuFinancialIntegrityError,
    DISPOSITION,
    EXPECTED_COLUMNS,
    EXPECTED_STATUS_COUNTS,
    SENSITIVE_OR_LINKABLE_COLUMNS,
    finished_label,
    predecision_transaction_mask,
    validate_snapshot_summary,
)


def test_reviewed_external_snapshot_summary_is_accepted() -> None:
    validate_snapshot_summary(EXPECTED_COLUMNS, EXPECTED_STATUS_COUNTS)
    assert DISPOSITION == "external_only"
    assert sum(EXPECTED_STATUS_COUNTS.values()) == 682
    assert EXPECTED_STATUS_COUNTS["A"] + EXPECTED_STATUS_COUNTS["B"] == 234


def test_snapshot_schema_and_status_drift_fail_closed() -> None:
    wrong_schema = {**EXPECTED_COLUMNS, "loan": EXPECTED_COLUMNS["loan"][:-1]}
    with pytest.raises(CtuFinancialIntegrityError, match="schema"):
        validate_snapshot_summary(wrong_schema, EXPECTED_STATUS_COUNTS)

    wrong_counts = {**EXPECTED_STATUS_COUNTS, "B": 32}
    with pytest.raises(CtuFinancialIntegrityError, match="counts"):
        validate_snapshot_summary(EXPECTED_COLUMNS, wrong_counts)


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
    assert mask == (True, True, False)
    with pytest.raises(CtuFinancialIntegrityError, match="at least one"):
        predecision_transaction_mask((), date(1996, 2, 1))


def test_linkable_and_sensitive_fields_are_explicitly_blocked() -> None:
    assert {"birth_date", "gender", "district_id", "account_id", "client_id"} <= (
        SENSITIVE_OR_LINKABLE_COLUMNS
    )


def test_manifest_pins_only_aggregate_external_evidence() -> None:
    manifest = json.loads(
        Path("docs/data-sources/ctu-berka-financial-evaluation-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["disposition"] == "external_only"
    assert manifest["total_rows"] == 1_079_680
    assert manifest["total_columns"] == 55
    assert manifest["loan_status_counts"] == EXPECTED_STATUS_COUNTS
    assert manifest["finished_ab_loans"] == 234
    assert set(manifest["tables"]) == set(EXPECTED_COLUMNS)
    assert all(len(table["sha256"]) == 64 for table in manifest["tables"].values())
    assert manifest["raw_or_transformed_data_committed"] is False
