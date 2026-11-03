"""Validate the result-free HMDA implementation contract using stdlib only."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
HMDA = ROOT / "docs" / "research" / "hmda"
FILES = {
    "field_rules": "hmda-field-rules.json",
    "control_manifest": "hmda-control-manifest.json",
    "analysis_spec": "hmda-analysis-spec.json",
    "sensitivity_spec": "hmda-sensitivity-spec.json",
}


class ContractValidationError(ValueError):
    """Raised when a manifest is malformed or cross-file semantics drift."""


def _require(mapping, keys, location):
    if not isinstance(mapping, dict):
        raise ContractValidationError(f"{location}: expected object")
    missing = set(keys) - set(mapping)
    if missing:
        raise ContractValidationError(f"{location}: missing {sorted(missing)}")


def load_manifests(directory: Path = HMDA):
    return {kind: json.loads((directory / name).read_text()) for kind, name in FILES.items()}


def validate_manifests(payloads):
    envelope = {"$schema", "manifest_kind", "schema_version", "contract_id"}
    for kind, payload in payloads.items():
        _require(payload, envelope, kind)
        if payload["manifest_kind"] != kind:
            raise ContractValidationError(f"{kind}: manifest_kind mismatch")
        if payload["schema_version"] != "1.0.0" or payload["contract_id"] != "HMDA-CA-2024-CD-V1":
            raise ContractValidationError(f"{kind}: identity mismatch")

    fields = payloads["field_rules"]
    _require(fields, {"source_sha256", "normalization", "required_fields", "analysis_category_mappings", "ordered_cohort_rules", "outcomes", "group_contrasts"}, "field_rules")
    dti = fields["required_fields"]["debt_to_income_ratio"]["allowed"]
    age = fields["required_fields"]["applicant_age"]["allowed"]
    if set(dti) != set(fields["analysis_category_mappings"]["debt_to_income_ratio_primary"]):
        raise ContractValidationError("field_rules: DTI mapping is not exhaustive")
    if set(age) != set(fields["analysis_category_mappings"]["applicant_age_primary"]):
        raise ContractValidationError("field_rules: age mapping is not exhaustive")

    controls = payloads["control_manifest"]
    _require(controls, {"primary_regression_formula", "primary_regression_population", "variables", "prohibited_field_patterns", "unavailable_concepts"}, "control_manifest")
    variable_keys = {"field", "role", "coding", "missing_rule", "rationale", "allowed_analyses", "reference_category"}
    if not controls["variables"] or any(not variable_keys <= set(item) for item in controls["variables"]):
        raise ContractValidationError("control_manifest: malformed variable")
    if not isinstance(controls["primary_regression_formula"], str):
        raise ContractValidationError("control_manifest: formula must be a string")
    variables_by_field = {item["field"]: item for item in controls["variables"]}
    for field in ("county_code", "lei"):
        if variables_by_field[field].get("reference_category") is not None or variables_by_field[field].get("contrast_coding") != "sum_to_zero":
            raise ContractValidationError(f"control_manifest.{field}: sum-to-zero coding is not explicit")

    analysis = payloads["analysis_spec"]
    _require(analysis, {"global_order", "raw_to_analysis_mappings", "estimands", "multiplicity"}, "analysis_spec")
    if set(analysis["estimands"]) != {"unadjusted", "standardized", "regression_adjusted"}:
        raise ContractValidationError("analysis_spec: estimand set mismatch")
    estimand_keys = {"row_set", "formula", "variance", "p_value", "failure_reason_codes"}
    for name, estimand in analysis["estimands"].items():
        _require(estimand, estimand_keys, f"analysis_spec.estimands.{name}")
        _require(estimand["row_set"], {"id", "start", "complete_case_fields"}, f"analysis_spec.estimands.{name}.row_set")
        if not isinstance(estimand["formula"], str):
            raise ContractValidationError(f"analysis_spec.estimands.{name}: formula must be a string")
        if not estimand["failure_reason_codes"]:
            raise ContractValidationError(f"analysis_spec.estimands.{name}: empty failure reasons")
    regression = analysis["estimands"]["regression_adjusted"]
    if controls["primary_regression_population"] != regression["row_set"]["id"]:
        raise ContractValidationError("cross_file: regression row-set ID mismatch")
    if controls["primary_regression_formula"] != regression["formula"]:
        raise ContractValidationError("cross_file: regression formula mismatch")
    if fields["analysis_category_mappings"]["debt_to_income_ratio_primary"] != analysis["raw_to_analysis_mappings"]["dti_band"]:
        raise ContractValidationError("cross_file: DTI mapping mismatch")
    if fields["analysis_category_mappings"]["applicant_age_primary"] != analysis["raw_to_analysis_mappings"]["applicant_age"]:
        raise ContractValidationError("cross_file: age mapping mismatch")

    sensitivity = payloads["sensitivity_spec"]
    _require(sensitivity, {"analyses"}, "sensitivity_spec")
    required = {"id", "estimands", "outcome", "complete_case", "formula", "regression_formula", "reference_categories", "bins", "support", "variance", "p_value"}
    if len(sensitivity["analyses"]) != 10 or any(not required <= set(item) for item in sensitivity["analyses"]):
        raise ContractValidationError("sensitivity_spec: malformed or incomplete analysis")
    for item in sensitivity["analyses"]:
        if not isinstance(item["formula"], str):
            raise ContractValidationError(f"sensitivity_spec.{item['id']}: formula must be a string")
        if "regression_adjusted" in item["estimands"] and item["row_set_ids"].get("regression_adjusted") != regression["row_set"]["id"]:
            raise ContractValidationError(f"sensitivity_spec.{item['id']}: regression row-set ID mismatch")
    serialized = json.dumps(sensitivity)
    for forbidden in ("otherwise", "primary_configuration", "lexical_first"):
        if forbidden in serialized:
            raise ContractValidationError(f"sensitivity_spec: forbidden placeholder {forbidden}")
    if "income50_loan100k_dti_primary_cltv_primary" in serialized:
        raise ContractValidationError("sensitivity_spec: bins alias is not self-contained")


def main():
    validate_manifests(load_manifests())
    print("HMDA manifest contract validated")


if __name__ == "__main__":
    main()
