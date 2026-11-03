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
    add_alternate_strata,
    add_primary_strata,
    apply_overlap_support,
    apply_common_support,
    construct_cohort,
    fail_closed_artifact,
    geography_standardized_estimate,
    lender_regression_estimate,
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
        for income_index, income in enumerate((25, 75, 125, 200, 300)):
          for loan_index, loan_amount in enumerate((75000, 200000, 400000, 600000)):
            for index in range(per_cell):
                county_06001 = (index % 5 != 0) if group == "focal" else (index % 5 < 2)
                lender_index = (index + 7 * income_index + 13 * loan_index + (17 if group == "focal" else 0)) % 100
                rows.append({
                    "activity_year": "2024", "lei": f"LEI{lender_index:017d}", "state_code": "CA",
                    "county_code": "06001" if county_06001 else "06013", "census_tract": "06001000100", "action_taken": "1" if (index * 37) % 100 < ((65 if county_06001 else 45) + (5 if group == "focal" else 0)) else "3",
                    "loan_type": "1", "lien_status": "1", "loan_purpose": "1", "occupancy_type": "1",
                    "construction_method": "1", "total_units": "1", "loan_amount": str(loan_amount), "income": str(income),
                    "debt_to_income_ratio": "<20%" if index % 2 == 0 else "40",
                    "combined_loan_to_value_ratio": "50" if (index // 2) % 2 == 0 else "85",
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
        ("lei", "UNKNOWN_LENDER", "hmda_code_value_invalid"),
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
    for sensitivity_id in ("HMDA-SENS-MISSING-COMPLETE", "HMDA-SENS-MISSING-CATEGORY"):
        sensitivity = estimands["sensitivities"][sensitivity_id]
        assert sensitivity["status"] == "executed"
        assert set(sensitivity["groups"]) == {"ethnicity", "race", "sex"}
        assert all(
            set(group) == {"standardized", "regression_adjusted"}
            for group in sensitivity["groups"].values()
        )
    core = estimands["sensitivities"]["HMDA-SENS-CONTROL-CORE"]
    extended = estimands["sensitivities"]["HMDA-SENS-CONTROL-EXTENDED"]
    assert core["status"] == extended["status"] == "executed"
    for group in ("ethnicity", "race", "sex"):
        core_result = core["groups"][group]["regression_adjusted"]
        extended_result = extended["groups"][group]["regression_adjusted"]
        assert core_result["method_identity"] == "logit_core_v1"
        assert extended_result["method_identity"] == "logit_core_plus_county_code_sum_to_zero_v1"
        assert extended_result["design_columns"] > core_result["design_columns"]
        assert core_result["flow"]["reconciled"] is True
        assert extended_result["flow"]["reconciled"] is True
        assert extended_result["difference"] != pytest.approx(
            estimands["primary"][group]["regression_adjusted"]["difference"], abs=1e-10
        )
    bins = estimands["sensitivities"]["HMDA-SENS-BINS"]
    assert bins["status"] == "executed"
    for group in ("ethnicity", "race", "sex"):
        result = bins["groups"][group]["standardized"]
        assert result["method_identity"] == "alternate_registered_bins_lei_cluster_bootstrap_v1"
        assert result["flow"]["reconciled"] is True
        assert len(result["row_set_digest"]) == 64
    geography = estimands["sensitivities"]["HMDA-SENS-GEOGRAPHY"]
    assert geography["status"] == "executed"
    for group in ("ethnicity", "race", "sex"):
        result = geography["groups"][group]["standardized"]
        assert result["method_identity"] == "exact_county_strata_lei_cluster_bootstrap_v1"
        assert result["flow"]["reconciled"] is True
        assert result["geography_coverage"]["reconciled"] is True
        assert result["geography_coverage"]["included_units"] == ["06001", "06013"]
    lender = estimands["sensitivities"]["HMDA-SENS-LENDER"]
    assert lender["status"] == "executed"
    for group in ("ethnicity", "race", "sex"):
        result = lender["groups"][group]["regression_adjusted"]
        assert result["method_identity"] == "logit_core_plus_lei_sum_to_zero_v1"
        assert result["flow"]["reconciled"] is True
        assert result["lender_coverage"]["reconciled"] is True
        assert len(result["lender_coverage"]["included_lenders"]) == 100
    overlap = estimands["sensitivities"]["HMDA-SENS-OVERLAP"]
    assert overlap["status"] == "executed"
    for group in ("ethnicity", "race", "sex"):
        for name in ("standardized", "regression_adjusted"):
            result = overlap["groups"][group][name]
            assert result["flow"]["reconciled"] is True
            assert result["overlap_diagnostics"]["reconciled"] is True
            assert result["overlap_diagnostics"]["thresholds"]["minimum_rows_per_group_per_stratum"] == 50
    unavailable = set(estimands["sensitivities"]) - {
        "HMDA-SENS-ACTION-13", "HMDA-SENS-MISSING-COMPLETE",
        "HMDA-SENS-MISSING-CATEGORY", "HMDA-SENS-CONTROL-CORE",
        "HMDA-SENS-CONTROL-EXTENDED", "HMDA-SENS-BINS", "HMDA-SENS-GEOGRAPHY", "HMDA-SENS-LENDER",
        "HMDA-SENS-OVERLAP",
        "HMDA-SENS-YEAR",
    }
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


def test_missing_category_rebuild_changes_rows_and_reconciles_flow():
    frame = _rows()
    loan = frame["loan_amount"] == "75000"
    frame.loc[loan & (frame["income"] == "25"), "debt_to_income_ratio"] = "NA"
    frame.loc[loan & (frame["income"] == "75"), "combined_loan_to_value_ratio"] = "NA"
    frame.loc[loan & (frame["income"] == "125"), "applicant_age"] = "9999"
    estimands, _ = analyze_frame(frame, bootstrap_replicates=5)
    complete = estimands["sensitivities"]["HMDA-SENS-MISSING-COMPLETE"]["groups"]
    category = estimands["sensitivities"]["HMDA-SENS-MISSING-CATEGORY"]["groups"]
    for group in ("ethnicity", "race", "sex"):
        for estimand in ("standardized", "regression_adjusted"):
            assert category[group][estimand]["row_count"] > complete[group][estimand]["row_count"]
            assert category[group][estimand]["row_set_digest"] != complete[group][estimand]["row_set_digest"]
            assert complete[group][estimand]["flow"]["reconciled"] is True
            assert category[group][estimand]["flow"]["reconciled"] is True


def test_missing_category_collinearity_fails_closed():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    affected = (data["income"] == "25") & (data["loan_amount"] == "75000")
    data.loc[affected, ["dti_band", "cltv_band", "applicant_age_band"]] = ["NA", "NA", "9999"]
    with pytest.raises(HMDAContractError, match="hmda_design_matrix_singular"):
        regression_adjusted_estimate(
            data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
        )


def test_extended_control_missing_or_single_level_county_fails_closed():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    with pytest.raises(HMDAContractError, match="hmda_schema_required_field_missing"):
        regression_adjusted_estimate(
            data.drop(columns="county_code"), "derived_ethnicity",
            "Hispanic or Latino", "Not Hispanic or Latino", fixed_effect="county_code",
        )
    data["county_code"] = "06001"
    with pytest.raises(HMDAContractError, match="hmda_design_matrix_singular"):
        regression_adjusted_estimate(
            data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino",
            fixed_effect="county_code",
        )


def test_alternate_bins_exact_boundaries_and_missing_values():
    frame = pd.DataFrame({
        "income_numeric": [-1, 0, 0.1, 40, 40.1, 80, 80.1, 120, 120.1, 200, 200.1, np.nan],
        "loan_amount_numeric": [0, 150000, 150000.1, 300000, 300000.1, 450000, 450000.1, 650000, 650000.1, 700000, 800000, np.nan],
        "debt_to_income_ratio": ["40", "41"] * 6,
        "cltv_numeric": [0, 70, 70.1, 80, 80.1, 95, 95.1, 100, 100.1, 1000, np.nan, np.nan],
        "combined_loan_to_value_ratio": ["0", "70", "70.1", "80", "80.1", "95", "95.1", "100", "100.1", "1000", "NA", "Exempt"],
    })
    result = add_alternate_strata(frame)
    assert result["income_band"].tolist() == [
        "(-inf,0]", "(-inf,0]", "(0,40]", "(0,40]", "(40,80]", "(40,80]",
        "(80,120]", "(80,120]", "(120,200]", "(120,200]", "(200,inf)", pd.NA,
    ]
    assert result["loan_amount_band"].tolist()[0] is pd.NA
    assert result["loan_amount_band"].tolist()[1:9] == [
        "(0,150000]", "(150000,300000]", "(150000,300000]", "(300000,450000]",
        "(300000,450000]", "(450000,650000]", "(450000,650000]", "(650000,inf)",
    ]
    assert result.loc[0, "dti_band"] == "37-40"
    assert result.loc[1, "dti_band"] == "41-43"
    assert result["cltv_band"].tolist()[:10] == [
        "[0,70]", "[0,70]", "(70,80]", "(70,80]", "(80,95]", "(80,95]",
        "(95,100]", "(95,100]", "(100,1000]", "(100,1000]",
    ]
    assert result.loc[11, "cltv_band"] == "Exempt"


def test_alternate_bins_sparse_support_fails_closed():
    data = add_alternate_strata(normalize_analysis_fields(_rows(per_cell=4)))
    with pytest.raises(HMDAContractError, match="hmda_common_support_insufficient"):
        standardized_estimate(
            data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
        )


def test_geography_changes_estimate_and_audits_excluded_county():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    primary = standardized_estimate(
        data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    extra = data.iloc[:50].copy()
    extra["county_code"] = "06075"
    extra["_source_row_id"] = np.arange(10_000_000, 10_000_050)
    result = geography_standardized_estimate(
        pd.concat([data, extra], ignore_index=True),
        "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino",
    )
    assert result["difference"] != pytest.approx(primary["difference"], abs=1e-10)
    assert result["geography_coverage"]["excluded_units"] == ["06075"]
    assert result["geography_coverage"]["unit_counts"]["06075"]["focal"]["rows"] == 50
    assert result["geography_coverage"]["reconciled"] is True


def test_geography_missing_low_sample_single_unit_and_empty_fail_closed():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    data.loc[data.index[:10], "county_code"] = "NA"
    result = geography_standardized_estimate(
        data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    assert "NA" not in result["geography_coverage"]["input_units"]
    for reduced in (
        data.loc[data["county_code"] == "06001"],
        data.iloc[:0],
    ):
        with pytest.raises(HMDAContractError, match="hmda_common_support_insufficient"):
            geography_standardized_estimate(
                reduced, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
            )


def test_lender_rules_change_model_and_audit_exclusions():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    data["_source_row_id"] = np.arange(len(data))
    primary = regression_adjusted_estimate(
        data, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    low_sample = data.iloc[:50].copy()
    low_sample["lei"] = "LOWLENDER00000000000"
    low_sample["_source_row_id"] = np.arange(20_000_000, 20_000_050)
    result = lender_regression_estimate(
        pd.concat([data, low_sample], ignore_index=True),
        "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino",
    )
    assert result["difference"] != pytest.approx(primary["difference"], abs=1e-10)
    assert result["lender_coverage"]["excluded_lenders"] == ["LOWLENDER00000000000"]
    excluded = result["lender_coverage"]["lender_counts"]["LOWLENDER00000000000"]
    assert "minimum_lender_rows" in excluded["exclusion_reasons"]
    assert result["flow"]["reconciled"] is True


def test_lender_low_sample_single_valid_and_empty_fail_closed():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    cases = (
        data.assign(lei="SINGLELENDER000000000"),
        data.iloc[:50],
        data.iloc[:0],
    )
    for reduced in cases:
        with pytest.raises(HMDAContractError, match="hmda_cluster_count_insufficient"):
            lender_regression_estimate(
                reduced, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
            )


def _overlap_rows(strata: int = 20, rows_per_group: int = 50) -> pd.DataFrame:
    rows = []
    for stratum in range(strata):
        for group in ("focal", "reference"):
            for index in range(rows_per_group):
                rows.append({
                    "group": group, "income_band": f"income-{stratum}",
                    "loan_amount_band": "loan", "dti_band": "dti", "cltv_band": "cltv",
                    "favorable_action": int(index < 10), "_source_row_id": len(rows),
                })
    return pd.DataFrame(rows)


def test_overlap_exact_threshold_boundary_and_reconciliation():
    retained, evidence = apply_overlap_support(_overlap_rows(), "group", "focal", "reference")
    assert len(retained) == 20 * 2 * 50
    assert evidence["supported_strata"] == 20
    assert evidence["retained_fraction"] == {"focal": 1.0, "reference": 1.0}
    assert evidence["overall_supported_fraction"] == 1.0
    assert evidence["reconciled"] is True


def test_overlap_below_cell_outcome_strata_and_retention_thresholds_fail_closed():
    below_rows = _overlap_rows()
    below_rows = below_rows.drop(below_rows[(below_rows["income_band"] == "income-0") & (below_rows["group"] == "focal")].index[:1])
    below_outcome = _overlap_rows()
    mask = (below_outcome["income_band"] == "income-0") & (below_outcome["group"] == "focal")
    below_outcome.loc[mask, "favorable_action"] = 0
    retention = _overlap_rows(strata=25)
    for stratum in range(6):
        drop = retention[
            (retention["income_band"] == f"income-{stratum}") & (retention["group"] == "focal")
        ].index[:1]
        retention = retention.drop(drop)
    for frame in (below_rows, below_outcome, retention, _overlap_rows(strata=19), _overlap_rows().iloc[:0]):
        with pytest.raises(HMDAContractError, match="hmda_common_support_insufficient"):
            apply_overlap_support(frame, "group", "focal", "reference")


def test_overlap_stricter_rules_change_analysis_row_set():
    data = add_primary_strata(normalize_analysis_fields(_rows()))
    keys = ["income_band", "loan_amount_band", "dti_band", "cltv_band"]
    first_key = tuple(data[keys].drop_duplicates().iloc[0])
    in_stratum = np.logical_and.reduce([data[key] == value for key, value in zip(keys, first_key)])
    focal = in_stratum & (data["derived_ethnicity"] == "Hispanic or Latino")
    drop = data.loc[focal].index[40:]
    reduced = data.drop(drop)
    primary_rows, _ = apply_common_support(
        reduced, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    overlap_rows, evidence = apply_overlap_support(
        reduced, "derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"
    )
    assert len(overlap_rows) < len(primary_rows)
    assert evidence["support_excluded_rows"] > 0
    assert evidence["excluded_strata"]


def test_overlap_bootstrap_insufficient_valid_replicates_fails_closed():
    data = _overlap_rows()
    data["lei"] = [f"LEI{i % 30:017d}" for i in range(len(data))]

    def always_invalid(sample):
        raise HMDAContractError("hmda_common_support_insufficient")

    with pytest.raises(HMDAContractError, match="hmda_bootstrap_insufficient_valid_replicates"):
        cluster_bootstrap_differences(data, always_invalid, replicates=5)

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
    assert artifact["commit"] == "1dba4c8b989e1384906325c9a145a3b9410e33ba"
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
