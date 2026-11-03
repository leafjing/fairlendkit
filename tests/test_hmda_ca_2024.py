from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fairlendkit.research.hmda_ca_2024 import (
    HMDAContractError,
    SOURCE_BYTES,
    SOURCE_SHA256,
    SOURCE_URL,
    SourceEvidence,
    add_primary_strata,
    apply_common_support,
    construct_cohort,
    fail_closed_artifact,
    success_artifact,
    holm_adjust,
    normalize_analysis_fields,
    regression_adjusted_estimate,
    cluster_bootstrap_differences,
    standardized_estimate,
    unadjusted_estimate,
    admit_source_archive,
    analyze_frame,
    validate_header_bytes,
)


def _rows(per_cell: int = 300) -> pd.DataFrame:
    rows = []
    for group, ethnicity in (("focal", "Hispanic or Latino"), ("reference", "Not Hispanic or Latino")):
        for income in (25, 75, 125, 200, 300):
          for loan_amount in (75000, 200000, 400000, 600000):
            for index in range(per_cell):
                rows.append({
                    "activity_year": "2024", "lei": f"LEI{index:017d}", "state_code": "CA",
                    "county_code": "06001", "census_tract": "06001000100", "action_taken": "1" if (index // 4) % 2 == (group == "focal") else "3",
                    "loan_type": "1", "lien_status": "1", "loan_purpose": "1", "occupancy_type": "1",
                    "construction_method": "1", "total_units": "1", "loan_amount": str(loan_amount), "income": str(income),
                    "debt_to_income_ratio": "36" if index % 2 == 0 else "40",
                    "combined_loan_to_value_ratio": "75" if (index // 2) % 2 == 0 else "85",
                    "property_value": str(loan_amount + 100000 + index * index * 10),
                    "loan_term": str(120 + (index * 7) % 360),
                    "applicant_age": ("<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74")[index % 7],
                    "derived_ethnicity": ethnicity,
                    "derived_race": "Black or African American" if group == "focal" else "White",
                    "derived_sex": "Female" if group == "focal" else "Male",
                })
    return pd.DataFrame(rows)


def test_cohort_normalization_and_unadjusted_contract():
    frame = _rows()
    cohort, flow = construct_cohort(frame)
    normalized = normalize_analysis_fields(cohort)
    result = unadjusted_estimate(normalized, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino")
    assert flow["cohort_rows"] == len(frame)
    assert result["counts"]["focal"]["rows"] == len(frame) // 2
    assert result["raw_p_value"] is not None
    assert len(result["difference_ci"]) == 2
    assert len(result["ratio_ci"]) == 2


def test_newcombe_wilson_difference_ci_exact_values():
    frame = pd.DataFrame({
        "group": ["focal"] * 100 + ["reference"] * 100,
        "favorable_action": [1] * 80 + [0] * 20 + [1] * 60 + [0] * 40,
    })
    result = unadjusted_estimate(frame, "group", "focal", "reference")
    assert result["difference_ci"] == pytest.approx(
        [0.07311915999619883, 0.3185050993390346], abs=1e-15
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("derived_ethnicity", "UNKNOWN_CODE", "hmda_code_value_invalid"),
        ("loan_amount", "1,000", "hmda_numeric_value_invalid"),
        ("loan_term", "NaN", "hmda_numeric_value_invalid"),
    ],
)
def test_invalid_source_values_fail_closed(field, value, reason):
    frame = _rows(per_cell=2)
    frame.loc[0, field] = value
    with pytest.raises(HMDAContractError, match=reason):
        construct_cohort(frame)


def test_normalization_never_coerces_illegal_numeric_to_missing():
    frame = _rows(per_cell=2)
    frame.loc[0, "income"] = "not-a-number"
    with pytest.raises(HMDAContractError, match="hmda_numeric_value_invalid"):
        normalize_analysis_fields(frame)


def test_reordered_header_fails_schema_digest_gate():
    with pytest.raises(HMDAContractError, match="hmda_schema_digest_mismatch"):
        validate_header_bytes(b"lei,activity_year")


def test_independent_common_support_and_standardization():
    normalized = add_primary_strata(normalize_analysis_fields(_rows()))
    supported, evidence = apply_common_support(normalized, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino")
    assert evidence["supported_strata"] >= 20
    result = standardized_estimate(supported, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino")
    assert result["support"]["overall_supported_fraction"] == 1.0


def test_support_fails_closed_for_sparse_cells():
    normalized = add_primary_strata(normalize_analysis_fields(_rows(per_cell=4)))
    with pytest.raises(HMDAContractError, match="hmda_common_support_insufficient"):
        apply_common_support(normalized, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino")


def test_holm_and_undefined_family():
    adjusted = holm_adjust({"ethnicity": 0.01, "race": 0.04, "sex": 0.03})
    assert adjusted == {"ethnicity": 0.03, "sex": 0.06, "race": 0.06}
    assert holm_adjust({"ethnicity": 0.01, "race": None, "sex": 0.03}) is None


def test_synthetic_end_to_end_three_groups_estimands_holm_and_sensitivity():
    estimands, flow = analyze_frame(_rows(), bootstrap_replicates=5)
    assert flow["reconciled"] is True
    assert set(estimands["primary"]) == {"ethnicity", "race", "sex"}
    for group in estimands["primary"].values():
        assert set(group) == {"unadjusted", "standardized", "regression_adjusted"}
        assert all("holm_adjusted_p_value" in value for value in group.values())
        assert all(len(value["row_set_digest"]) == 64 for value in group.values())
        assert all(value["flow"]["reconciled"] is True for value in group.values())
        standardized = group["standardized"]
        assert standardized["difference"] == pytest.approx(
            standardized["focal_rate"] - standardized["reference_rate"]
        )
    assert set(estimands["sensitivities"]) == {
        "HMDA-SENS-ACTION-13", "HMDA-SENS-MISSING-COMPLETE",
        "HMDA-SENS-MISSING-CATEGORY", "HMDA-SENS-CONTROL-CORE",
        "HMDA-SENS-CONTROL-EXTENDED", "HMDA-SENS-BINS",
        "HMDA-SENS-GEOGRAPHY", "HMDA-SENS-LENDER", "HMDA-SENS-OVERLAP",
        "HMDA-SENS-YEAR",
    }
    action = estimands["sensitivities"]["HMDA-SENS-ACTION-13"]
    assert action["status"] == "executed"
    assert all(
        "holm_adjusted_p_value" in result
        for group in action["groups"].values() for result in group.values()
    )
    assert estimands["sensitivities"]["HMDA-SENS-YEAR"]["groups"] is None
    unavailable = set(estimands["sensitivities"]) - {"HMDA-SENS-ACTION-13", "HMDA-SENS-YEAR"}
    for sensitivity_id in unavailable:
        sensitivity = estimands["sensitivities"][sensitivity_id]
        assert sensitivity == {
            "status": "failed",
            "reason_codes": ["hmda_sensitivity_not_implemented"],
            "results_emitted": False,
            "groups": None,
        }
    source = SourceEvidence(
        url="synthetic", archive_bytes=1, archive_sha256="a" * 64, member_name="data.csv",
        member_bytes=2, header_sha256="b" * 64, ordered_header=("a",), row_count=len(_rows()),
        duplicate_row_count=0, ordered_row_fingerprint_sha256="c" * 64,
    )
    empty_executed = copy.deepcopy(estimands)
    empty_executed["sensitivities"]["HMDA-SENS-BINS"] = {"status": "executed", "groups": {}}
    artifact = success_artifact(source, empty_executed, flow, configuration_sha256="d" * 64)
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert "sensitivity_failures" not in artifact

    empty_applicability = copy.deepcopy(estimands)
    empty_applicability["sensitivities"]["HMDA-SENS-BINS"] = {
        "status": "not_applicable", "applicability": {}, "groups": None,
    }
    artifact = success_artifact(source, empty_applicability, flow, configuration_sha256="d" * 64)
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert "sensitivity_failures" not in artifact


def test_regression_and_cluster_bootstrap_contracts():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    regression = regression_adjusted_estimate(
        data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    assert regression["clusters"] >= 30
    assert len(regression["ci"]) == 2

    def mean_difference(sample):
        rates = sample.groupby("derived_ethnicity")["favorable_action"].mean()
        return {"difference": rates["Hispanic or Latino"] - rates["Not Hispanic or Latino"]}

    bootstrap = cluster_bootstrap_differences(data, mean_difference, replicates=20, seed=20241119)
    assert bootstrap["valid_replicates"] == 20
    assert 0 <= bootstrap["raw_p_value"] <= 1


def test_disclosure_gate_never_emits_failed_results(tmp_path: Path):
    source = SourceEvidence(
        url="official", archive_bytes=1, archive_sha256="a" * 64, member_name="data.csv",
        member_bytes=2, header_sha256="b" * 64, ordered_header=("a",), row_count=3,
        duplicate_row_count=1, ordered_row_fingerprint_sha256="c" * 64,
    )
    artifact = fail_closed_artifact(source, ["hmda_duplicate_rows_detected"], configuration_sha256="d" * 64)
    assert artifact["constraint_status"] == "failed"
    assert artifact["candidate_copy_status"] == "locked_research_only"
    assert artifact["results_emitted"] is False
    assert artifact["estimands"] is None
    assert artifact["commit"]
    assert artifact["command"]
    assert artifact["generated_at_utc"].endswith("+00:00")
    assert artifact["method_identity"]["multiplicity"].startswith("holm_")
    assert not any(isinstance(value, float) for value in artifact.values())


def test_incomplete_sensitivity_registry_cannot_create_success_artifact():
    source = SourceEvidence(
        url="synthetic", archive_bytes=1, archive_sha256="a" * 64, member_name="data.csv",
        member_bytes=2, header_sha256="b" * 64, ordered_header=("a",), row_count=3,
        duplicate_row_count=0, ordered_row_fingerprint_sha256="c" * 64,
    )
    artifact = success_artifact(
        source,
        {"sensitivities": {"HMDA-SENS-BINS": {"status": "failed"}}},
        {"reconciled": True},
        configuration_sha256="d" * 64,
    )
    assert artifact["constraint_status"] == "failed"
    assert artifact["results_emitted"] is False
    assert artifact["estimands"] is None
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]


@pytest.mark.parametrize("mutation", ["missing", "unknown", "illegal_status", "year_enabled"])
def test_sensitivity_registry_shape_is_exact_and_fail_closed(mutation):
    source = SourceEvidence(
        url="synthetic", archive_bytes=1, archive_sha256="a" * 64, member_name="data.csv",
        member_bytes=2, header_sha256="b" * 64, ordered_header=("a",), row_count=3,
        duplicate_row_count=0, ordered_row_fingerprint_sha256="c" * 64,
    )
    ids = {
        "HMDA-SENS-ACTION-13", "HMDA-SENS-MISSING-COMPLETE", "HMDA-SENS-MISSING-CATEGORY",
        "HMDA-SENS-CONTROL-CORE", "HMDA-SENS-CONTROL-EXTENDED", "HMDA-SENS-BINS",
        "HMDA-SENS-GEOGRAPHY", "HMDA-SENS-LENDER", "HMDA-SENS-OVERLAP", "HMDA-SENS-YEAR",
    }
    registry = {key: {"status": "executed", "groups": {}} for key in ids}
    registry["HMDA-SENS-YEAR"] = {"status": "disabled_pending_separate_source_admission", "groups": None}
    if mutation == "missing":
        registry.pop("HMDA-SENS-BINS")
    elif mutation == "unknown":
        registry["HMDA-SENS-UNKNOWN"] = {"status": "executed", "groups": {}}
    elif mutation == "illegal_status":
        registry["HMDA-SENS-BINS"]["status"] = "passed"
    else:
        registry["HMDA-SENS-YEAR"] = {"status": "executed", "groups": {}}
    artifact = success_artifact(source, {"sensitivities": registry}, {}, configuration_sha256="d" * 64)
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert artifact["results_emitted"] is False


def _structurally_valid_registry():
    common = {"row_set_digest": "a" * 64, "flow": {"reconciled": True},
              "raw_p_value": 0.1, "holm_adjusted_p_value": 0.2}
    bundle = {
        "unadjusted": {**common, "difference_ci": [-0.1, 0.3]},
        "standardized": {**common, "ci": [-0.1, 0.3], "valid_replicates": 950},
        "regression_adjusted": {**common, "ci": [-0.1, 0.3], "standard_error": 0.1, "clusters": 30},
    }
    registry = {
        "HMDA-SENS-ACTION-13": {
            "status": "executed", "groups": {group: copy.deepcopy(bundle) for group in ("ethnicity", "race", "sex")},
        },
        "HMDA-SENS-YEAR": {"status": "disabled_pending_separate_source_admission", "groups": None},
    }
    for sensitivity_id in (
        "HMDA-SENS-MISSING-COMPLETE", "HMDA-SENS-MISSING-CATEGORY", "HMDA-SENS-CONTROL-CORE",
        "HMDA-SENS-CONTROL-EXTENDED", "HMDA-SENS-BINS", "HMDA-SENS-GEOGRAPHY",
        "HMDA-SENS-LENDER", "HMDA-SENS-OVERLAP",
    ):
        registry[sensitivity_id] = {
            "status": "failed", "reason_codes": ["hmda_sensitivity_not_implemented"],
            "results_emitted": False, "groups": None,
        }
    return registry


def _registry_artifact(registry):
    source = SourceEvidence(
        url="synthetic", archive_bytes=1, archive_sha256="a" * 64, member_name="data.csv",
        member_bytes=2, header_sha256="b" * 64, ordered_header=("a",), row_count=3,
        duplicate_row_count=0, ordered_row_fingerprint_sha256="c" * 64,
    )
    return success_artifact(source, {"sensitivities": registry}, {}, configuration_sha256="d" * 64)


def test_action_13_cannot_be_not_applicable_and_arbitrary_checks_are_rejected():
    registry = _structurally_valid_registry()
    valid = _registry_artifact(registry)
    assert len(valid["sensitivity_failures"]) == 8
    registry["HMDA-SENS-ACTION-13"] = {
        "status": "not_applicable",
        "applicability": {"applicable": False, "checks": [{"x": 1}]},
        "groups": None,
    }
    invalid = _registry_artifact(registry)
    assert invalid["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert "sensitivity_failures" not in invalid


@pytest.mark.parametrize("field,value", [
    ("raw_p_value", True), ("raw_p_value", float("nan")),
    ("raw_p_value", float("inf")), ("raw_p_value", 1.01),
    ("holm_adjusted_p_value", -0.01),
])
def test_executed_sensitivity_rejects_invalid_probability_values(field, value):
    registry = _structurally_valid_registry()
    registry["HMDA-SENS-ACTION-13"]["groups"]["ethnicity"]["unadjusted"][field] = value
    artifact = _registry_artifact(registry)
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert "sensitivity_failures" not in artifact


@pytest.mark.parametrize("estimand,field,value", [
    ("standardized", "ci", [0.0, float("nan")]),
    ("standardized", "valid_replicates", True),
    ("standardized", "valid_replicates", 949),
    ("regression_adjusted", "standard_error", float("inf")),
    ("regression_adjusted", "standard_error", -0.1),
    ("regression_adjusted", "clusters", 29),
])
def test_executed_sensitivity_rejects_invalid_variance_evidence(estimand, field, value):
    registry = _structurally_valid_registry()
    registry["HMDA-SENS-ACTION-13"]["groups"]["ethnicity"][estimand][field] = value
    artifact = _registry_artifact(registry)
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]


def test_wrong_source_identity_fails_before_parsing(tmp_path: Path):
    archive = tmp_path / "not-official.zip"
    archive.write_bytes(b"PK\x05\x06" + b"\0" * 18)
    with pytest.raises(HMDAContractError, match="hmda_source_identity_mismatch"):
        admit_source_archive(archive)


def test_real_source_evidence_is_frozen_and_results_are_locked():
    artifact_path = Path(__file__).parents[1] / "docs" / "artifacts" / "hmda-ca-2024-v1.json"
    artifact = json.loads(artifact_path.read_text())
    source = artifact["source"]
    assert source["url"] == SOURCE_URL
    assert source["archive_bytes"] == SOURCE_BYTES
    assert source["archive_sha256"] == SOURCE_SHA256
    assert source["member_name"] == "2024_public_lar_csv.csv"
    assert source["row_count"] == 12_229_298
    assert source["duplicate_row_count"] == 26_734
    assert artifact["reason_codes"] == ["hmda_duplicate_rows_detected"]
    assert artifact["constraint_status"] == "failed"
    assert artifact["candidate_copy_status"] == "locked_research_only"
    assert artifact["results_emitted"] is False
    assert artifact["estimands"] is None


def test_synthetic_execution_artifact_fails_closed_on_incomplete_registry():
    artifact_path = Path(__file__).parents[1] / "docs" / "artifacts" / "hmda-ca-2024-synthetic-v1.json"
    artifact = json.loads(artifact_path.read_text())
    assert artifact["constraint_status"] == "failed"
    assert artifact["candidate_copy_status"] == "locked_research_only"
    assert artifact["results_emitted"] is False
    assert artifact["commit"] == "4df6be7b55fba9a27d9c781f65fa3c1cdf497956"
    assert artifact["command"][1] == "scripts/generate_hmda_synthetic_artifact.py"
    assert artifact["estimands"] is None
    assert artifact["reason_codes"] == ["hmda_sensitivity_registry_incomplete"]
    assert "sensitivity_failures" not in artifact


def test_synthetic_artifact_normalized_regeneration_equality(tmp_path: Path):
    checked_path = Path(__file__).parents[1] / "docs" / "artifacts" / "hmda-ca-2024-synthetic-v1.json"
    checked = json.loads(checked_path.read_text())
    generated = tmp_path / "artifact.json"
    subprocess.run([
        sys.executable, "scripts/generate_hmda_synthetic_artifact.py",
        "--output", str(generated), "--generated-at-utc", checked["generated_at_utc"],
        "--bootstrap-replicates", "5",
    ], check=True)
    actual = json.loads(generated.read_text())

    def normalize(value):
        result = json.loads(json.dumps(value))
        output_index = result["command"].index("--output") + 1
        result["command"][output_index] = "<OUTPUT>"
        return result

    assert normalize(actual) == normalize(checked)
