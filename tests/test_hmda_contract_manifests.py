"""Static contract checks for the result-free HMDA implementation manifests."""

import json
import copy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver, ValidationError


ROOT = Path(__file__).parents[1]
HMDA = ROOT / "docs" / "research" / "hmda"
MANIFESTS = {
    "hmda-field-rules.json": "field_rules", "hmda-control-manifest.json": "control_manifest",
    "hmda-analysis-spec.json": "analysis_spec", "hmda-sensitivity-spec.json": "sensitivity_spec",
}


def _load(name):
    return json.loads((HMDA / name).read_text())


def _validator():
    schema = _load("hmda-manifest-schema-v2.json")
    subordinate = [_load(name) for name in (
        "hmda-field-rules.schema.json", "hmda-control-manifest.schema.json",
        "hmda-analysis-spec.schema.json", "hmda-sensitivity-spec.schema.json",
    )]
    Draft202012Validator.check_schema(schema)
    for item in subordinate:
        Draft202012Validator.check_schema(item)
    store = {item["$id"]: item for item in subordinate}
    return Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store))


def test_manifest_envelopes_and_index_discoverability():
    index = (ROOT / "docs" / "index.md").read_text()
    for name, kind in MANIFESTS.items():
        payload = _load(name)
        assert payload["$schema"] == "./hmda-manifest-schema-v2.json"
        assert payload["manifest_type"] == kind
        assert payload["schema_version"] == "1.0.0"
        assert payload["contract_id"] == "HMDA-CA-2024-CD-V1"
        assert f"research/hmda/{name}" in index


@pytest.mark.parametrize("manifest_name", MANIFESTS)
def test_draft_2020_12_oneof_schema_accepts_manifest(manifest_name):
    _validator().validate(_load(manifest_name))


@pytest.mark.parametrize(
    "manifest_name,mutate",
    [
        ("hmda-analysis-spec.json", lambda p: p["estimands"]["unadjusted"].__setitem__("formula", 7)),
        ("hmda-control-manifest.json", lambda p: p.__setitem__("variables", [])),
        ("hmda-field-rules.json", lambda p: p.__setitem__("ordered_cohort_rules", "bad")),
        ("hmda-analysis-spec.json", lambda p: p.__setitem__("global_order", None)),
        ("hmda-sensitivity-spec.json", lambda p: p["analyses"][0].__setitem__("bins", "bad")),
        ("hmda-sensitivity-spec.json", lambda p: p["analyses"][0].__setitem__("unknown_field", True)),
        ("hmda-analysis-spec.json", lambda p: p["estimands"]["standardized"]["variance"].__setitem__("unknown", 1)),
        ("hmda-analysis-spec.json", lambda p: p["estimands"]["standardized"]["support"].__setitem__("minimum_supported_strata", "twenty")),
        ("hmda-analysis-spec.json", lambda p: p["estimands"]["standardized"]["bins"].__setitem__("dti_band", "bad")),
        ("hmda-sensitivity-spec.json", lambda p: p["analyses"][0]["reference_categories"].__setitem__("unknown", "bad")),
        ("hmda-sensitivity-spec.json", lambda p: p["analyses"][0]["p_value"].__setitem__("unknown", "bad")),
    ],
    ids=["numeric-formula", "empty-variables", "array-to-string", "array-to-null", "sensitivity-child-type", "unknown-field", "deep-variance-unknown", "deep-support-type", "deep-bin-type", "deep-reference-unknown", "deep-pvalue-unknown"],
)
def test_schema_rejects_malformed_internal_structure(manifest_name, mutate):
    payload = copy.deepcopy(_load(manifest_name))
    mutate(payload)
    with pytest.raises(ValidationError):
        _validator().validate(payload)


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
    assert analyses["HMDA-SENS-CONTROL-EXTENDED"]["county_contrast_coding"] == "sum_to_zero"
    assert analyses["HMDA-SENS-LENDER"]["lender_contrast_coding"] == "sum_to_zero"
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
