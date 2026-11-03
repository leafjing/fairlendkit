"""Static contract checks for the result-free HMDA implementation manifests."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
HMDA = ROOT / "docs" / "research" / "hmda"


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
        assert payload["$schema"] == "./hmda-manifest-schema-v1.json"
        assert payload["manifest_kind"] == kind
        assert payload["schema_version"] == "1.0.0"
        assert payload["contract_id"] == "HMDA-CA-2024-CD-V1"
        assert f"research/hmda/{name}" in index


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


def test_sensitivity_parameters_are_frozen_and_adjacent_year_disabled():
    payload = _load("hmda-sensitivity-spec.json")
    analyses = {item["id"]: item for item in payload["analyses"]}
    assert analyses["HMDA-SENS-BINS"]["change"]["dti_percent"]
    assert analyses["HMDA-SENS-CONTROL-EXTENDED"]["change"]["append_terms"]
    assert analyses["HMDA-SENS-OVERLAP"]["change"]["minimum_group_retained_fraction"] == 0.8
    assert analyses["HMDA-SENS-YEAR"]["status"] == "disabled_pending_separate_source_admission"
