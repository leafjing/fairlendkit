import json
from pathlib import Path

import pytest

from fairlendkit.research.census_htops_hps_2607 import (
    EXPECTED, Htops2607IntegrityError, analysis_columns, canonical_sha256,
    summarize_numeric, validate_summary,
)


def valid():
    return {**EXPECTED, "identifier_nulls": 0, "identifier_unique": 12755,
            "identifier_order_matches": True}


def test_reviewed_evidence_validates() -> None:
    validate_summary(**valid())


@pytest.mark.parametrize("field", list(EXPECTED) + ["identifier_nulls", "identifier_unique", "identifier_order_matches"])
def test_every_evidence_drift_fails_closed(field: str) -> None:
    evidence = valid()
    evidence[field] = False if field == "identifier_order_matches" else None
    with pytest.raises(Htops2607IntegrityError): validate_summary(**evidence)


def test_identifier_is_removed_and_aliases_fail() -> None:
    assert analysis_columns(("SCRAMID", "PWEIGHT")) == ("PWEIGHT",)
    for columns in (("PWEIGHT",), ("SCRAMID", "scramid", "PWEIGHT")):
        with pytest.raises(Htops2607IntegrityError): analysis_columns(columns)


def test_numeric_summary() -> None:
    assert summarize_numeric(("", "nan", "0", "-1", "2")) == (1, 1, 1, 1, -1.0, 2.0)


def test_schema_and_special_rules_artifact_matches_digests() -> None:
    artifact = json.loads(Path("docs/data-sources/census-htops-hps-2607-schema-and-codes.json").read_text())
    schemas = artifact["schemas"]
    assert canonical_sha256(schemas["HTOPS_HPS_2607_PUF.csv"]) == EXPECTED["main_schema_sha256"]
    assert canonical_sha256(schemas["HTOPS_HPS_2607_REPWGT_PUF.csv"]) == EXPECTED["replicate_schema_sha256"]
    rules = {k: [[c, v] for c, v in sorted(cols.items())]
             for k, cols in sorted(artifact["special_response_rules"].items())}
    assert canonical_sha256(rules) == EXPECTED["special_rules_sha256"]
