"""Static contract checks for the result-free HMDA implementation manifests."""

import json
import copy
import importlib.util
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[1]
HMDA = ROOT / "docs" / "research" / "hmda"
SCHEMAS = {
    "hmda-field-rules.json": "hmda-field-rules.schema.json",
    "hmda-control-manifest.json": "hmda-control-manifest.schema.json",
    "hmda-analysis-spec.json": "hmda-analysis-spec.schema.json",
    "hmda-sensitivity-spec.json": "hmda-sensitivity-spec.schema.json",
}
SPEC = importlib.util.spec_from_file_location("validate_hmda_manifests", ROOT / "scripts" / "validate_hmda_manifests.py")
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def _load(name):
    return json.loads((HMDA / name).read_text())


def test_manifest_envelopes_and_index_discoverability():
    expected = {
        "hmda-field-rules.json": "field_rules",
        "hmda-control-manifest.json": "control_manifest",
        "hmda-analysis-spec.json": "analysis_spec",
        "hmda-sensitivity-spec.json": "sensitivity_spec",
    }
    index = (ROOT / "docs" / "index.md").read_text()
    for name, kind in expected.items():
        payload = _load(name)
        assert payload["$schema"] == f"./{SCHEMAS[name]}"
        assert payload["manifest_kind"] == kind
        assert payload["schema_version"] == "1.0.0"
        assert payload["contract_id"] == "HMDA-CA-2024-CD-V1"
        assert f"research/hmda/{name}" in index


@pytest.mark.parametrize("manifest_name,schema_name", SCHEMAS.items())
def test_draft_2020_12_schema_accepts_manifest(manifest_name, schema_name):
    schema = _load(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_load(manifest_name))


@pytest.mark.parametrize(
    "manifest_name,schema_name,mutate",
    [
        ("hmda-analysis-spec.json", "hmda-analysis-spec.schema.json", lambda p: p["estimands"]["unadjusted"].__setitem__("formula", {})),
        ("hmda-control-manifest.json", "hmda-control-manifest.schema.json", lambda p: p.__setitem__("variables", [])),
        ("hmda-sensitivity-spec.json", "hmda-sensitivity-spec.schema.json", lambda p: p["analyses"][0].__setitem__("unknown_field", True)),
        ("hmda-field-rules.json", "hmda-field-rules.schema.json", lambda p: p["ordered_cohort_rules"][0].pop("exclude_reason")),
    ],
    ids=["wrong-type", "empty-variables", "unknown-field", "missing-nested-field"],
)
def test_schema_rejects_malformed_internal_structure(manifest_name, schema_name, mutate):
    payload = copy.deepcopy(_load(manifest_name))
    mutate(payload)
    assert list(Draft202012Validator(_load(schema_name)).iter_errors(payload))


def test_field_rules_freeze_mixed_enums_and_ordered_exclusions():
    payload = _load("hmda-field-rules.json")
    fields = payload["required_fields"]
    assert set(fields["debt_to_income_ratio"]["allowed"]) == {
        "<20%", "20%-<30%", "30%-<36%", *map(str, range(36, 50)),
        "50%-60%", ">60%", "NA", "Exempt",
    }
    assert fields["applicant_age"]["allowed"] == [
        "<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74", "8888", "9999"
    ]
    mappings = payload["analysis_category_mappings"]
    assert set(mappings["debt_to_income_ratio_primary"]) == set(fields["debt_to_income_ratio"]["allowed"])
    assert set(mappings["applicant_age_primary"]) == set(fields["applicant_age"]["allowed"])
    orders = [rule["order"] for rule in payload["ordered_cohort_rules"]]
    reasons = [rule["exclude_reason"] for rule in payload["ordered_cohort_rules"]]
    assert orders == sorted(orders) and len(orders) == len(set(orders))
    assert len(reasons) == len(set(reasons))


def test_control_manifest_is_per_variable_and_primary_formula_is_closed():
    payload = _load("hmda-control-manifest.json")
    required = {"field", "role", "coding", "missing_rule", "rationale", "allowed_analyses", "reference_category"}
    assert all(required <= set(variable) for variable in payload["variables"])
    formula = payload["primary_regression_formula"]
    assert "county_code" not in formula and "lei" not in formula
    assert payload["primary_regression_interactions"] == []
    by_field = {variable["field"]: variable for variable in payload["variables"]}
    for field in ("county_code", "lei"):
        assert by_field[field]["reference_category"] is None
        assert by_field[field]["contrast_coding"] == "sum_to_zero"


def test_estimands_have_independent_rows_support_and_p_values():
    payload = _load("hmda-analysis-spec.json")
    estimands = payload["estimands"]
    assert set(estimands) == {"unadjusted", "standardized", "regression_adjusted"}
    assert estimands["unadjusted"]["row_set"]["support"] == "not_applicable"
    assert estimands["standardized"]["row_set"] != estimands["regression_adjusted"]["row_set"]
    assert estimands["regression_adjusted"]["county_in_primary_model"] is False
    assert estimands["regression_adjusted"]["lei_in_primary_model"] is False
    assert "B_valid+1" in estimands["standardized"]["p_value"]
    assert payload["multiplicity"]["method"] == "holm_step_down"
    assert all(estimand["failure_reason_codes"] for estimand in estimands.values())


def test_sensitivity_parameters_are_frozen_and_adjacent_year_disabled():
    payload = _load("hmda-sensitivity-spec.json")
    analyses = {item["id"]: item for item in payload["analyses"]}
    assert analyses["HMDA-SENS-BINS"]["bins"]["dti"]
    assert "county_code" in analyses["HMDA-SENS-CONTROL-EXTENDED"]["regression_formula"]
    assert analyses["HMDA-SENS-OVERLAP"]["support"]["minimum_retained_fraction_each_group"] == 0.8
    assert analyses["HMDA-SENS-YEAR"]["status"] == "disabled_pending_separate_source_admission"
    required = {"id", "estimands", "outcome", "complete_case", "formula", "regression_formula", "reference_categories", "bins", "support", "variance", "p_value"}
    assert all(required <= set(item) for item in analyses.values())
    serialized = json.dumps(payload)
    assert "otherwise" not in serialized
    assert "primary_configuration" not in serialized
    assert "lexical_first" not in serialized
    assert "income50_loan100k_dti_primary_cltv_primary" not in serialized
    for item in analyses.values():
        if item["estimands"]:
            assert {"income", "loan_amount", "dti", "cltv"} <= set(item["bins"])


def test_cross_file_formula_and_mapping_consistency():
    fields = _load("hmda-field-rules.json")
    controls = _load("hmda-control-manifest.json")
    analysis = _load("hmda-analysis-spec.json")
    assert fields["analysis_category_mappings"]["debt_to_income_ratio_primary"] == analysis["raw_to_analysis_mappings"]["dti_band"]
    assert fields["analysis_category_mappings"]["applicant_age_primary"] == analysis["raw_to_analysis_mappings"]["applicant_age"]
    assert controls["primary_regression_formula"] == analysis["estimands"]["regression_adjusted"]["formula"]
    assert controls["primary_regression_population"] == analysis["estimands"]["regression_adjusted"]["row_set"]["id"]
    assert controls["primary_regression_population"] == "regression_support_only"
    for item in _load("hmda-sensitivity-spec.json")["analyses"]:
        if "regression_adjusted" in item["estimands"]:
            assert item["row_set_ids"]["regression_adjusted"] == controls["primary_regression_population"]


def test_stdlib_validator_accepts_frozen_contract():
    VALIDATOR.validate_manifests(VALIDATOR.load_manifests())


def test_validator_rejects_malformed_nested_structure():
    payloads = VALIDATOR.load_manifests()
    malformed = copy.deepcopy(payloads)
    del malformed["analysis_spec"]["estimands"]["standardized"]["p_value"]
    try:
        VALIDATOR.validate_manifests(malformed)
    except VALIDATOR.ContractValidationError as error:
        assert "p_value" in str(error)
    else:
        raise AssertionError("malformed estimand was accepted")


def test_validator_rejects_cross_file_row_set_drift():
    payloads = VALIDATOR.load_manifests()
    malformed = copy.deepcopy(payloads)
    malformed["control_manifest"]["primary_regression_population"] = "wrong_rows"
    try:
        VALIDATOR.validate_manifests(malformed)
    except VALIDATOR.ContractValidationError as error:
        assert "row-set ID mismatch" in str(error)
    else:
        raise AssertionError("cross-file row-set drift was accepted")
