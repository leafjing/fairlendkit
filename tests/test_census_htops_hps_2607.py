import json
from pathlib import Path

import pytest

from fairlendkit.research.census_htops_hps_2607 import (
    EXPECTED, VARIANCE_OUTPUTS_ENABLED, Htops2607IntegrityError, analysis_columns,
    canonical_sha256, summarize_numeric, validate_full_sample_weight_rows,
    validate_replicate_columns, validate_summary,
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


@pytest.mark.parametrize("prefix", ["PWEIGHT", "HWEIGHT"])
def test_replicates_are_strictly_one_through_eighty(prefix: str) -> None:
    valid_columns = (prefix + "0",) + tuple(prefix + str(index) for index in range(1, 81))
    validate_replicate_columns(valid_columns, prefix)
    variants = (
        valid_columns[1:],
        valid_columns + (prefix + "81",),
        valid_columns[:20] + valid_columns[21:],
        valid_columns[:2] + (valid_columns[2],) + valid_columns[2:],
        (prefix + "1", prefix + "0") + valid_columns[2:],
    )
    for drifted in variants:
        with pytest.raises(Htops2607IntegrityError, match="replicate sequence"):
            validate_replicate_columns(drifted, prefix)


def test_variance_semantics_are_pinned_but_not_implemented() -> None:
    assert EXPECTED["variance_factor"] == (4, 80)
    assert VARIANCE_OUTPUTS_ENABLED is False


def _weight_values() -> tuple[str, ...]:
    return tuple(str(index / 10) for index in range(EXPECTED["rows"]))


def test_person_full_sample_weight_zero_matches_main_rows() -> None:
    values = _weight_values()
    validate_full_sample_weight_rows(values, values, values, values)


def test_household_full_sample_weight_zero_matches_main_rows() -> None:
    values = _weight_values()
    validate_full_sample_weight_rows(values, values, values, values)


def test_person_single_full_sample_weight_drift_fails() -> None:
    values = _weight_values()
    drifted = list(values); drifted[EXPECTED["rows"] // 2] = "1.0001"
    with pytest.raises(Htops2607IntegrityError, match="PWEIGHT.*differs at row"):
        validate_full_sample_weight_rows(values, drifted, values, values)


def test_household_single_full_sample_weight_drift_fails() -> None:
    values = _weight_values()
    drifted = list(values); drifted[EXPECTED["rows"] // 2] = "1.0001"
    with pytest.raises(Htops2607IntegrityError, match="HWEIGHT.*differs at row"):
        validate_full_sample_weight_rows(values, values, values, drifted)


def test_full_sample_weight_length_drift_fails() -> None:
    with pytest.raises(Htops2607IntegrityError, match="row count"):
        validate_full_sample_weight_rows(("1",), ("1",), _weight_values(), _weight_values())


def test_schema_and_special_rules_artifact_matches_digests() -> None:
    artifact = json.loads(Path("docs/data-sources/census-htops-hps-2607-schema-and-codes.json").read_text())
    schemas = artifact["schemas"]
    assert canonical_sha256(schemas["HTOPS_HPS_2607_PUF.csv"]) == EXPECTED["main_schema_sha256"]
    assert canonical_sha256(schemas["HTOPS_HPS_2607_REPWGT_PUF.csv"]) == EXPECTED["replicate_schema_sha256"]
    rules = {k: [[c, v] for c, v in sorted(cols.items())]
             for k, cols in sorted(artifact["special_response_rules"].items())}
    assert canonical_sha256(rules) == EXPECTED["special_rules_sha256"]
