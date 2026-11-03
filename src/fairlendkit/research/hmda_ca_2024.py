"""Fail-closed 2024 California HMDA conditional-disparity research pipeline.

The public archive is never copied into the repository.  This module consumes
an externally supplied official ZIP, validates its frozen identity, and emits
aggregate evidence only.  Association estimates are research-only and are
withheld unless every source, schema, support, variance, multiplicity, and
disclosure gate passes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import re
import sys
import subprocess
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from zipfile import ZipFile

import numpy as np
import pandas as pd


SOURCE_URL = "https://files.ffiec.cfpb.gov/static-data/snapshot/2024/2024_public_lar_csv.zip"
SOURCE_BYTES = 664_242_987
SOURCE_SHA256 = "9383890f38c2ae1ef46942e72e1a2a211aa0b979c0e46db5fd6d7eb8669f22c1"
SOURCE_MEMBER_BYTES = 4_625_405_352
MAX_UNCOMPRESSED_BYTES = 5_000_000_000
HEADER_SHA256 = "dbef604276f5b4e28b72634d143f23f6b3b5a7ed9284671ac79cbba8bd126063"
CONTRACT_ID = "HMDA-CA-2024-CD-V1"
LOCKED_STATUS = "locked_research_only"
REQUIRED_FIELDS = (
    "activity_year", "lei", "state_code", "county_code", "census_tract",
    "action_taken", "loan_type", "lien_status", "loan_purpose",
    "occupancy_type", "construction_method", "total_units", "loan_amount",
    "income", "debt_to_income_ratio", "combined_loan_to_value_ratio",
    "property_value", "loan_term", "applicant_age", "derived_ethnicity",
    "derived_race", "derived_sex",
)
GROUPS = {
    "ethnicity": ("derived_ethnicity", "Hispanic or Latino", "Not Hispanic or Latino"),
    "race": ("derived_race", "Black or African American", "White"),
    "sex": ("derived_sex", "Female", "Male"),
}
SENSITIVITY_IDS = {
    "HMDA-SENS-ACTION-13", "HMDA-SENS-MISSING-COMPLETE",
    "HMDA-SENS-MISSING-CATEGORY", "HMDA-SENS-CONTROL-CORE",
    "HMDA-SENS-CONTROL-EXTENDED", "HMDA-SENS-BINS",
    "HMDA-SENS-GEOGRAPHY", "HMDA-SENS-LENDER", "HMDA-SENS-OVERLAP",
    "HMDA-SENS-YEAR",
}
SENSITIVITY_ESTIMANDS = {
    "HMDA-SENS-ACTION-13": {"unadjusted", "standardized", "regression_adjusted"},
    "HMDA-SENS-MISSING-COMPLETE": {"standardized", "regression_adjusted"},
    "HMDA-SENS-MISSING-CATEGORY": {"standardized", "regression_adjusted"},
    "HMDA-SENS-CONTROL-CORE": {"regression_adjusted"},
    "HMDA-SENS-CONTROL-EXTENDED": {"regression_adjusted"},
    "HMDA-SENS-BINS": {"standardized"},
    "HMDA-SENS-GEOGRAPHY": {"standardized"},
    "HMDA-SENS-LENDER": {"regression_adjusted"},
    "HMDA-SENS-OVERLAP": {"standardized", "regression_adjusted"},
}
SENSITIVITY_FAILURE_REASONS = {
    "hmda_sensitivity_not_implemented", "hmda_sensitivity_execution_failed",
    "hmda_common_support_insufficient", "hmda_cluster_count_insufficient",
    "hmda_bootstrap_insufficient_valid_replicates", "hmda_design_matrix_singular",
    "hmda_model_nonconvergence", "hmda_regression_variance_undefined",
}
COHORT_RULES = (
    ("activity_year", {"2024"}, "hmda_wrong_activity_year"),
    ("state_code", {"CA"}, "hmda_outside_california"),
    ("loan_type", {"1"}, "hmda_nonconventional_loan"),
    ("lien_status", {"1"}, "hmda_not_first_lien"),
    ("loan_purpose", {"1"}, "hmda_not_home_purchase"),
    ("occupancy_type", {"1"}, "hmda_not_owner_occupied"),
    ("construction_method", {"1"}, "hmda_not_site_built"),
    ("total_units", {"1"}, "hmda_not_one_unit"),
    ("action_taken", {"1", "2", "3"}, "hmda_action_outside_primary_contrast"),
)
DTI_MAP = {
    "<20%": "<30", "20%-<30%": "<30", "30%-<36%": "30-36", "36": "30-36",
    **{str(v): "37-43" for v in range(37, 44)},
    **{str(v): "44-49" for v in range(44, 50)},
    "50%-60%": "50-60", ">60%": ">60", "Exempt": "Exempt", "NA": None,
}
AGE_MAP = {v: v for v in ("<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74")}
AGE_MAP.update({"8888": None, "9999": None})
ALLOWED_VALUES = {
    "activity_year": {"2024"}, "action_taken": set("12345678"),
    "loan_type": set("1234"), "lien_status": {"1", "2"},
    "loan_purpose": {"1", "2", "4", "5", "31", "32"},
    "occupancy_type": {"1", "2", "3"}, "construction_method": {"1", "2"},
    "total_units": {"1", "2", "3", "4", "5-24", "25-49", "50-99", "100-149", ">149"},
    "debt_to_income_ratio": set(DTI_MAP), "applicant_age": set(AGE_MAP),
    "derived_ethnicity": {"Hispanic or Latino", "Not Hispanic or Latino", "Joint", "Ethnicity Not Available", "Free Form Text Only"},
    "derived_race": {"American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or Other Pacific Islander", "White", "2 or more minority races", "Joint", "Race Not Available", "Free Form Text Only"},
    "derived_sex": {"Male", "Female", "Joint", "Sex Not Available"},
}
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class HMDAContractError(ValueError):
    """Stable fail-closed contract violation."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class SourceEvidence:
    url: str
    archive_bytes: int
    archive_sha256: str
    member_name: str
    member_bytes: int
    header_sha256: str
    ordered_header: tuple[str, ...]
    row_count: int
    duplicate_row_count: int
    ordered_row_fingerprint_sha256: str

    def as_dict(self) -> dict[str, Any]:
        value = dict(self.__dict__)
        value["ordered_header"] = list(self.ordered_header)
        return value


def _sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def validate_header_bytes(header_raw: bytes) -> tuple[str, ...]:
    try:
        header = tuple(next(csv.reader([header_raw.decode("utf-8-sig")])))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HMDAContractError("hmda_source_identity_mismatch", "invalid header") from exc
    if hashlib.sha256(header_raw).hexdigest() != HEADER_SHA256:
        raise HMDAContractError("hmda_schema_digest_mismatch")
    if not set(REQUIRED_FIELDS).issubset(header):
        raise HMDAContractError("hmda_schema_required_field_missing")
    return header


def admit_source_archive(path: str | Path, *, source_url: str = SOURCE_URL) -> SourceEvidence:
    """Validate the frozen official ZIP and scan full-row duplicate evidence."""

    archive = Path(path)
    size, digest = _sha256_file(archive)
    if source_url != SOURCE_URL or size != SOURCE_BYTES or digest != SOURCE_SHA256:
        raise HMDAContractError("hmda_source_identity_mismatch")
    with ZipFile(archive) as zipped:
        members = [item for item in zipped.infolist() if not item.is_dir()]
        if len(members) != 1:
            raise HMDAContractError("hmda_source_identity_mismatch", "expected one member")
        member = members[0]
        member_path = PurePosixPath(member.filename)
        if (
            member.flag_bits & 0x1
            or member_path.is_absolute()
            or ".." in member_path.parts
            or member_path.suffix.lower() != ".csv"
            or member.file_size != SOURCE_MEMBER_BYTES
            or member.file_size > MAX_UNCOMPRESSED_BYTES
        ):
            raise HMDAContractError("hmda_source_identity_mismatch", "unsafe member")
        with zipped.open(member) as raw:
            header_raw = raw.readline().rstrip(b"\r\n")
            header = validate_header_bytes(header_raw)
            header_digest = hashlib.sha256(header_raw).hexdigest()
            seen: set[bytes] = set()
            duplicate_count = 0
            rows = 0
            ordered_digest = hashlib.sha256()
            for line in raw:
                row_digest = hashlib.sha256(line.rstrip(b"\r\n")).digest()
                duplicate_count += row_digest in seen
                seen.add(row_digest)
                ordered_digest.update(row_digest)
                rows += 1
    return SourceEvidence(
        url=source_url,
        archive_bytes=size,
        archive_sha256=digest,
        member_name=member.filename,
        member_bytes=member.file_size,
        header_sha256=header_digest,
        ordered_header=header,
        row_count=rows,
        duplicate_row_count=duplicate_count,
        ordered_row_fingerprint_sha256=ordered_digest.hexdigest(),
    )


def _clean_strings(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        result[column] = result[column].astype("string").str.strip()
    return result


def validate_field_values(frame: pd.DataFrame) -> None:
    """Apply frozen categorical, pattern, and strict numeric source rules."""

    for field, allowed in ALLOWED_VALUES.items():
        invalid = ~frame[field].isin(allowed)
        if invalid.any():
            raise HMDAContractError("hmda_code_value_invalid", field)
    patterns = {
        "lei": re.compile(r"^[A-Z0-9]{20}$"),
        "state_code": re.compile(r"^(?:[A-Z]{2}|NA)$"),
        "county_code": re.compile(r"^(?:[0-9]{5}|NA)$"),
        "census_tract": re.compile(r"^(?:[0-9]{11}|NA)$"),
    }
    for field, pattern in patterns.items():
        if (~frame[field].str.fullmatch(pattern)).any():
            raise HMDAContractError("hmda_code_value_invalid", field)
    for field in ("loan_amount", "income", "property_value"):
        invalid = ~frame[field].isin(["NA", "Exempt"]) & ~frame[field].str.fullmatch(DECIMAL_PATTERN)
        if invalid.any():
            raise HMDAContractError("hmda_numeric_value_invalid", field)
    cltv = frame["combined_loan_to_value_ratio"]
    cltv_special = cltv.isin(["NA", "Exempt"])
    if (~cltv_special & ~cltv.str.fullmatch(DECIMAL_PATTERN)).any():
        raise HMDAContractError("hmda_numeric_value_invalid", "combined_loan_to_value_ratio")
    cltv_numeric = pd.to_numeric(cltv.where(~cltv_special), errors="raise")
    if (~cltv_special & ~cltv_numeric.between(0, 1000)).any():
        raise HMDAContractError("hmda_numeric_value_invalid", "combined_loan_to_value_ratio")
    term = frame["loan_term"]
    term_special = term.isin(["NA", "Exempt"])
    if (~term_special & ~term.str.fullmatch(r"^(?:0|[1-9][0-9]*)$")).any():
        raise HMDAContractError("hmda_numeric_value_invalid", "loan_term")
    term_numeric = pd.to_numeric(term.where(~term_special), errors="raise")
    if (~term_special & ~term_numeric.between(1, 600)).any():
        raise HMDAContractError("hmda_numeric_value_invalid", "loan_term")


def construct_cohort(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen ordered cohort rules and return aggregate flow only."""

    missing = sorted(set(REQUIRED_FIELDS) - set(frame.columns))
    if missing:
        raise HMDAContractError("hmda_schema_required_field_missing", ",".join(missing))
    current = _clean_strings(frame)
    validate_field_values(current)
    if "_source_row_id" not in current:
        current["_source_row_id"] = np.arange(len(current), dtype=np.int64)
    flow: dict[str, Any] = {"source_rows": int(len(current)), "exclusions": []}
    for field, allowed, reason in COHORT_RULES:
        keep = current[field].isin(allowed)
        flow["exclusions"].append({"reason_code": reason, "rows": int((~keep).sum())})
        current = current.loc[keep].copy()
    flow["cohort_rows"] = int(len(current))
    flow["reconciled"] = flow["source_rows"] == flow["cohort_rows"] + sum(item["rows"] for item in flow["exclusions"])
    if not flow["reconciled"]:
        raise HMDAContractError("hmda_cohort_flow_not_reconciled")
    return current, flow


def normalize_analysis_fields(frame: pd.DataFrame) -> pd.DataFrame:
    """Create analysis columns only after strict source-value validation."""
    result = frame.copy()
    validate_field_values(result)
    for field in ("loan_amount", "income", "property_value", "loan_term"):
        result[field + "_numeric"] = pd.to_numeric(
            result[field].where(~result[field].isin(["NA", "Exempt"])), errors="raise"
        )
    cltv = result["combined_loan_to_value_ratio"]
    result["cltv_numeric"] = pd.to_numeric(
        cltv.where(~cltv.isin(["NA", "Exempt"])), errors="raise"
    )
    result["dti_band"] = result["debt_to_income_ratio"].map(DTI_MAP)
    result["applicant_age_band"] = result["applicant_age"].map(AGE_MAP)
    result["favorable_action"] = result["action_taken"].isin(["1", "2"]).astype(int)
    return result


def row_set_digest(frame: pd.DataFrame) -> str:
    if "_source_row_id" not in frame:
        raise HMDAContractError("hmda_artifact_reproduction_mismatch", "missing source row ID")
    digest = hashlib.sha256()
    for value in frame["_source_row_id"].astype("int64"):
        digest.update(int(value).to_bytes(8, "big", signed=False))
    return digest.hexdigest()


def load_admitted_rows(path: str | Path, *, chunksize: int = 250_000) -> pd.DataFrame:
    """Load only frozen analysis columns after archive identity admission."""
    pieces: list[pd.DataFrame] = []
    with ZipFile(path) as zipped:
        member = next(item for item in zipped.infolist() if not item.is_dir())
        with zipped.open(member) as raw:
            for chunk in pd.read_csv(raw, dtype="string", usecols=list(REQUIRED_FIELDS), chunksize=chunksize):
                cleaned = _clean_strings(chunk)
                validate_field_values(cleaned)
                pieces.append(cleaned)
    if not pieces:
        raise HMDAContractError("hmda_cohort_empty")
    return pd.concat(pieces, ignore_index=True)


def _wilson(successes: float, total: float, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def _normal_two_sided(z_value: float) -> float:
    return math.erfc(abs(z_value) / math.sqrt(2.0))


def unadjusted_estimate(frame: pd.DataFrame, group_field: str, focal: str, reference: str) -> dict[str, Any]:
    selected = frame.loc[frame[group_field].isin([focal, reference])]
    counts: dict[str, dict[str, int]] = {}
    for label, value in (("focal", focal), ("reference", reference)):
        rows = selected.loc[selected[group_field] == value]
        counts[label] = {"rows": int(len(rows)), "favorable": int(rows["favorable_action"].sum())}
    nf, nr = counts["focal"]["rows"], counts["reference"]["rows"]
    yf, yr = counts["focal"]["favorable"], counts["reference"]["favorable"]
    if nf == 0 or nr == 0:
        raise HMDAContractError("hmda_group_denominator_empty")
    pf, pr = yf / nf, yr / nr
    pooled = (yf + yr) / (nf + nr)
    standard_error = math.sqrt(pooled * (1 - pooled) * (1 / nf + 1 / nr))
    p_value = 1.0 if standard_error == 0 else _normal_two_sided((pf - pr) / standard_error)
    focal_ci, reference_ci = _wilson(yf, nf), _wilson(yr, nr)
    # Newcombe method 10: combine the two Wilson score limits geometrically.
    difference = pf - pr
    difference_ci = [
        difference - math.sqrt((pf - focal_ci[0]) ** 2 + (reference_ci[1] - pr) ** 2),
        difference + math.sqrt((focal_ci[1] - pf) ** 2 + (pr - reference_ci[0]) ** 2),
    ]
    ratio_ci = None
    if yf > 0 and yr > 0 and pf > 0 and pr > 0:
        ratio_se = math.sqrt(1 / yf - 1 / nf + 1 / yr - 1 / nr)
        log_ratio = math.log(pf / pr)
        ratio_ci = [math.exp(log_ratio - 1.959963984540054 * ratio_se), math.exp(log_ratio + 1.959963984540054 * ratio_se)]
    return {
        "row_count": int(len(selected)), "counts": counts,
        "focal_rate": pf, "reference_rate": pr, "difference": pf - pr,
        "ratio": None if pr == 0 else pf / pr,
        "focal_rate_ci": focal_ci, "reference_rate_ci": reference_ci,
        "difference_ci": difference_ci, "ratio_ci": ratio_ci,
        "raw_p_value": p_value,
    }


def _bin_series(values: pd.Series, breaks: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(values, bins=breaks, labels=labels, include_lowest=True, right=True).astype("string")


def add_primary_strata(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["income_band"] = _bin_series(
        result["income_numeric"], [-np.inf, 0, 50, 100, 150, 250, np.inf],
        ["(-inf,0]", "(0,50]", "(50,100]", "(100,150]", "(150,250]", "(250,inf)"],
    )
    result["loan_amount_band"] = _bin_series(
        result["loan_amount_numeric"], [0, 100000, 250000, 500000, 750000, np.inf],
        ["(0,100000]", "(100000,250000]", "(250000,500000]", "(500000,750000]", "(750000,inf)"],
    )
    numeric = result["cltv_numeric"]
    result["cltv_band"] = _bin_series(
        numeric, [0, 60, 80, 90, 100, 1000],
        ["[0,60]", "(60,80]", "(80,90]", "(90,100]", "(100,1000]"],
    )
    result.loc[result["combined_loan_to_value_ratio"] == "Exempt", "cltv_band"] = "Exempt"
    return result


def apply_common_support(frame: pd.DataFrame, group_field: str, focal: str, reference: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys = ["income_band", "loan_amount_band", "dti_band", "cltv_band"]
    selected = frame.loc[frame[group_field].isin([focal, reference])].dropna(subset=keys)
    grouped = selected.groupby(keys + [group_field], observed=True)["favorable_action"].agg(["size", "sum"])
    supported: list[tuple[Any, ...]] = []
    for key, block in grouped.groupby(level=keys, observed=True):
        valid = True
        for group in (focal, reference):
            try:
                row = block.xs(group, level=group_field)
            except KeyError:
                valid = False
                break
            favorable = int(row["sum"].iloc[0])
            total = int(row["size"].iloc[0])
            valid &= total >= 30 and favorable >= 5 and total - favorable >= 5
        if valid:
            supported.append(key if isinstance(key, tuple) else (key,))
    key_index = pd.MultiIndex.from_frame(selected[keys])
    supported_index = pd.MultiIndex.from_tuples(supported, names=keys)
    retained = selected.loc[key_index.isin(supported_index)].copy()
    fractions = {
        label: (len(retained.loc[retained[group_field] == group]) / max(1, len(selected.loc[selected[group_field] == group])))
        for label, group in (("focal", focal), ("reference", reference))
    }
    overall = len(retained) / max(1, len(selected))
    evidence = {
        "input_rows": int(len(selected)),
        "supported_rows": int(len(retained)),
        "support_excluded_rows": int(len(selected) - len(retained)),
        "supported_strata": len(supported),
        "retained_fraction": fractions,
        "overall_supported_fraction": overall,
        "reconciled": len(selected) == len(retained) + (len(selected) - len(retained)),
    }
    if len(supported) < 20 or overall < 0.7 or min(fractions.values()) < 0.7:
        raise HMDAContractError("hmda_common_support_insufficient", json.dumps(evidence, sort_keys=True))
    return retained, evidence


def standardized_estimate(frame: pd.DataFrame, group_field: str, focal: str, reference: str) -> dict[str, Any]:
    supported, evidence = apply_common_support(frame, group_field, focal, reference)
    keys = ["income_band", "loan_amount_band", "dti_band", "cltv_band"]
    total = len(supported)
    focal_rate = 0.0
    reference_rate = 0.0
    for _, block in supported.groupby(keys, observed=True):
        weight = len(block) / total
        rates = block.groupby(group_field, observed=True)["favorable_action"].mean()
        focal_rate += weight * float(rates[focal])
        reference_rate += weight * float(rates[reference])
    return {
        "row_count": total,
        "focal_rate": focal_rate,
        "reference_rate": reference_rate,
        "difference": focal_rate - reference_rate,
        "support": evidence,
    }


def cluster_bootstrap_differences(
    frame: pd.DataFrame,
    estimator,
    *,
    replicates: int = 1000,
    seed: int = 20241119,
) -> dict[str, Any]:
    """Cluster-resample LEIs and return percentile CI and zero-centered p-value."""

    clusters = frame["lei"].dropna().unique()
    if len(clusters) == 0:
        raise HMDAContractError("hmda_bootstrap_insufficient_valid_replicates")
    rng = np.random.default_rng(seed)
    by_cluster = {cluster: frame.loc[frame["lei"] == cluster] for cluster in clusters}
    estimates: list[float] = []
    for _ in range(replicates):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        pieces = []
        for ordinal, cluster in enumerate(sampled):
            piece = by_cluster[cluster].copy()
            piece["lei"] = f"{cluster}#{ordinal}"
            pieces.append(piece)
        try:
            estimates.append(float(estimator(pd.concat(pieces, ignore_index=True))["difference"]))
        except HMDAContractError:
            continue
    minimum_valid = math.ceil(replicates * 0.95)
    if len(estimates) < minimum_valid:
        raise HMDAContractError("hmda_bootstrap_insufficient_valid_replicates")
    values = np.asarray(estimates)
    denominator = len(values) + 1
    p_value = min(1.0, 2 * min((1 + int((values <= 0).sum())) / denominator, (1 + int((values >= 0).sum())) / denominator))
    return {"valid_replicates": len(values), "ci": np.quantile(values, [0.025, 0.975]).tolist(), "raw_p_value": p_value}


def _design_matrix(frame: pd.DataFrame, group_field: str, focal: str) -> np.ndarray:
    categorical = pd.DataFrame({
        "protected_group": (frame[group_field] == focal).astype(float),
        "log1p_loan_amount": np.log1p(frame["loan_amount_numeric"]),
        "log1p_income": np.log1p(frame["income_numeric"]),
        "log1p_property_value": np.log1p(frame["property_value_numeric"]),
        "loan_term_months": frame["loan_term_numeric"],
    }, index=frame.index)
    dummies = pd.get_dummies(
        frame[["dti_band", "cltv_band", "applicant_age_band"]],
        columns=["dti_band", "cltv_band", "applicant_age_band"], dtype=float,
    )
    for reference in ("dti_band_<30", "cltv_band_[0,60]", "applicant_age_band_35-44"):
        if reference in dummies:
            dummies = dummies.drop(columns=reference)
    return np.column_stack([np.ones(len(frame)), categorical.to_numpy(float), dummies.to_numpy(float)])


def regression_adjusted_estimate(frame: pd.DataFrame, group_field: str, focal: str, reference: str) -> dict[str, Any]:
    required = ["loan_amount_numeric", "income_numeric", "property_value_numeric", "loan_term_numeric", "dti_band", "cltv_band", "applicant_age_band", "lei"]
    data = frame.dropna(subset=required).copy()
    data = data.loc[(data["loan_amount_numeric"] > 0) & (data["income_numeric"] > 0) & (data["property_value_numeric"] > 0) & data["loan_term_numeric"].between(1, 600)]
    data, support = apply_common_support(data, group_field, focal, reference)
    if data["lei"].nunique() < 30:
        raise HMDAContractError("hmda_cluster_count_insufficient")
    x = _design_matrix(data, group_field, focal)
    y = data["favorable_action"].to_numpy(float)
    beta = np.zeros(x.shape[1])
    for _ in range(100):
        eta = np.clip(x @ beta, -30, 30)
        probability = 1 / (1 + np.exp(-eta))
        weights = np.maximum(probability * (1 - probability), 1e-9)
        information = x.T @ (weights[:, None] * x)
        score = x.T @ (y - probability)
        try:
            step = np.linalg.solve(information, score)
        except np.linalg.LinAlgError as exc:
            raise HMDAContractError("hmda_design_matrix_singular") from exc
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    else:
        raise HMDAContractError("hmda_model_nonconvergence")
    x_focal, x_reference = x.copy(), x.copy()
    x_focal[:, 1], x_reference[:, 1] = 1.0, 0.0
    p_focal = 1 / (1 + np.exp(-np.clip(x_focal @ beta, -30, 30)))
    p_reference = 1 / (1 + np.exp(-np.clip(x_reference @ beta, -30, 30)))
    difference = float(np.mean(p_focal - p_reference))
    gradient = np.mean((p_focal * (1 - p_focal))[:, None] * x_focal - (p_reference * (1 - p_reference))[:, None] * x_reference, axis=0)
    bread = np.linalg.inv(x.T @ ((1 / (1 + np.exp(-np.clip(x @ beta, -30, 30))) * (1 - 1 / (1 + np.exp(-np.clip(x @ beta, -30, 30)))))[:, None] * x))
    residual = y - 1 / (1 + np.exp(-np.clip(x @ beta, -30, 30)))
    meat = np.zeros((x.shape[1], x.shape[1]))
    for _, indexes in data.groupby("lei").groups.items():
        cluster_score = x[data.index.get_indexer(indexes)].T @ residual[data.index.get_indexer(indexes)]
        meat += np.outer(cluster_score, cluster_score)
    covariance = bread @ meat @ bread
    variance = float(gradient @ covariance @ gradient)
    if not math.isfinite(variance) or variance <= 0:
        raise HMDAContractError("hmda_regression_variance_undefined")
    standard_error = math.sqrt(variance)
    return {"row_count": len(data), "difference": difference, "standard_error": standard_error, "ci": [difference - 1.959963984540054 * standard_error, difference + 1.959963984540054 * standard_error], "raw_p_value": _normal_two_sided(difference / standard_error), "clusters": int(data["lei"].nunique()), "support": support}


def holm_adjust(p_values: Mapping[str, float | None]) -> dict[str, float] | None:
    if any(value is None or not math.isfinite(float(value)) for value in p_values.values()):
        return None
    ordered = sorted((float(value), key) for key, value in p_values.items())
    adjusted: dict[str, float] = {}
    previous = 0.0
    total = len(ordered)
    for index, (value, key) in enumerate(ordered):
        previous = max(previous, min(1.0, (total - index) * value))
        adjusted[key] = previous
    return adjusted


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "src/fairlendkit/research/hmda_ca_2024.py", "scripts/run_hmda_ca_2024.py"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def artifact_identity(*, command: list[str] | None = None, generated_at_utc: str | None = None) -> dict[str, Any]:
    return {
        "commit": _git_commit(),
        "command": command or list(sys.argv),
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "pandas": pd.__version__, "numpy": np.__version__,
        },
        "method_identity": {
            "unadjusted": "wilson_newcombe_log_ratio_pooled_score_v1",
            "standardized": "pooled_strata_lei_bootstrap_v1",
            "regression_adjusted": "logit_cluster_sandwich_delta_v1",
            "multiplicity": "holm_three_group_family_per_estimand_v1",
        },
    }


def _estimand_bundle(
    frame: pd.DataFrame, group_field: str, focal: str, reference: str, *, bootstrap_replicates: int,
) -> dict[str, Any]:
    group_rows = frame.loc[frame[group_field].isin([focal, reference])].copy()
    if group_rows.empty:
        raise HMDAContractError("hmda_group_denominator_empty")
    unadjusted_rows = group_rows.dropna(subset=["favorable_action"])
    unadjusted = unadjusted_estimate(unadjusted_rows, group_field, focal, reference)
    unadjusted["row_set_digest"] = row_set_digest(unadjusted_rows)
    unadjusted["flow"] = {
        "named_group_input_rows": int(len(frame)),
        "named_group_excluded_rows": int(len(frame) - len(group_rows)),
        "complete_case_input_rows": int(len(group_rows)),
        "complete_case_excluded_rows": int(len(group_rows) - len(unadjusted_rows)),
        "support_excluded_rows": 0,
        "final_rows": int(len(unadjusted_rows)),
        "reconciled": len(frame) == (len(frame) - len(group_rows)) + (len(group_rows) - len(unadjusted_rows)) + len(unadjusted_rows),
    }

    standardized_rows = group_rows.loc[
        (group_rows["loan_amount_numeric"] > 0)
        & group_rows["income_numeric"].notna()
        & group_rows["dti_band"].notna()
        & group_rows["cltv_band"].notna()
    ].copy()
    standardized = standardized_estimate(standardized_rows, group_field, focal, reference)
    supported_rows, _ = apply_common_support(standardized_rows, group_field, focal, reference)
    bootstrap = cluster_bootstrap_differences(
        standardized_rows,
        lambda sample: standardized_estimate(sample, group_field, focal, reference),
        replicates=bootstrap_replicates,
    )
    standardized.update(bootstrap)
    standardized["row_set_digest"] = row_set_digest(supported_rows)
    standardized["flow"] = {
        "named_group_input_rows": int(len(frame)),
        "named_group_excluded_rows": int(len(frame) - len(group_rows)),
        "complete_case_input_rows": int(len(group_rows)),
        "complete_case_excluded_rows": int(len(group_rows) - len(standardized_rows)),
        "support_excluded_rows": int(len(standardized_rows) - len(supported_rows)),
        "final_rows": int(len(supported_rows)),
        "reconciled": len(frame) == (len(frame) - len(group_rows)) + (len(group_rows) - len(standardized_rows)) + (len(standardized_rows) - len(supported_rows)) + len(supported_rows),
    }

    regression = regression_adjusted_estimate(group_rows, group_field, focal, reference)
    regression_rows = group_rows.dropna(subset=[
        "loan_amount_numeric", "income_numeric", "property_value_numeric", "loan_term_numeric",
        "dti_band", "cltv_band", "applicant_age_band", "lei",
    ])
    regression_rows = regression_rows.loc[
        (regression_rows["loan_amount_numeric"] > 0) & (regression_rows["income_numeric"] > 0)
        & (regression_rows["property_value_numeric"] > 0) & regression_rows["loan_term_numeric"].between(1, 600)
    ]
    regression_rows, _ = apply_common_support(regression_rows, group_field, focal, reference)
    regression["row_set_digest"] = row_set_digest(regression_rows)
    regression["flow"] = {
        "named_group_input_rows": int(len(frame)),
        "named_group_excluded_rows": int(len(frame) - len(group_rows)),
        "complete_case_input_rows": int(len(group_rows)),
        "complete_case_excluded_rows": int(len(group_rows) - len(regression_rows) - regression["support"]["support_excluded_rows"]),
        "support_excluded_rows": int(regression["support"]["support_excluded_rows"]),
        "final_rows": int(len(regression_rows)),
        "reconciled": len(frame) == (len(frame) - len(group_rows)) + (len(group_rows) - len(regression_rows) - regression["support"]["support_excluded_rows"]) + regression["support"]["support_excluded_rows"] + len(regression_rows),
    }
    return {"unadjusted": unadjusted, "standardized": standardized, "regression_adjusted": regression}


def analyze_frame(frame: pd.DataFrame, *, bootstrap_replicates: int = 1000) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the frozen three-group x three-estimand contract on synthetic/admitted rows."""
    cohort, flow = construct_cohort(frame)
    normalized = add_primary_strata(normalize_analysis_fields(cohort))
    primary: dict[str, Any] = {}
    for group_name, (field, focal, reference) in GROUPS.items():
        primary[group_name] = _estimand_bundle(
            normalized, field, focal, reference, bootstrap_replicates=bootstrap_replicates,
        )
    for estimand in ("unadjusted", "standardized", "regression_adjusted"):
        adjusted = holm_adjust({group: primary[group][estimand]["raw_p_value"] for group in GROUPS})
        if adjusted is None:
            raise HMDAContractError("hmda_multiplicity_family_incomplete")
        for group in GROUPS:
            primary[group][estimand]["holm_adjusted_p_value"] = adjusted[group]

    sensitivity_rows = normalized.loc[normalized["action_taken"].isin(["1", "3"])].copy()
    sensitivity_rows["favorable_action"] = (sensitivity_rows["action_taken"] == "1").astype(int)
    action_13: dict[str, Any] = {}
    for group_name, (field, focal, reference) in GROUPS.items():
        action_13[group_name] = _estimand_bundle(
            sensitivity_rows, field, focal, reference, bootstrap_replicates=bootstrap_replicates,
        )
    for estimand in ("unadjusted", "standardized", "regression_adjusted"):
        adjusted = holm_adjust({group: action_13[group][estimand]["raw_p_value"] for group in GROUPS})
        if adjusted is None:
            raise HMDAContractError("hmda_multiplicity_family_incomplete")
        for group in GROUPS:
            action_13[group][estimand]["holm_adjusted_p_value"] = adjusted[group]

    def unavailable() -> dict[str, Any]:
        return {
            "status": "failed",
            "reason_codes": ["hmda_sensitivity_not_implemented"],
            "results_emitted": False,
            "groups": None,
        }

    sensitivities: dict[str, Any] = {
        "HMDA-SENS-ACTION-13": {"status": "executed", "groups": action_13},
        "HMDA-SENS-MISSING-COMPLETE": unavailable(),
        "HMDA-SENS-MISSING-CATEGORY": unavailable(),
        "HMDA-SENS-CONTROL-CORE": unavailable(),
        "HMDA-SENS-CONTROL-EXTENDED": unavailable(),
        "HMDA-SENS-BINS": unavailable(),
        "HMDA-SENS-GEOGRAPHY": unavailable(),
        "HMDA-SENS-LENDER": unavailable(),
        "HMDA-SENS-OVERLAP": unavailable(),
        "HMDA-SENS-YEAR": {
            "status": "disabled_pending_separate_source_admission", "groups": None,
        },
    }
    return {"primary": primary, "sensitivities": sensitivities}, flow


def success_artifact(
    source: SourceEvidence, estimands: Mapping[str, Any], cohort_flow: Mapping[str, Any], *,
    configuration_sha256: str, command: list[str] | None = None, generated_at_utc: str | None = None,
) -> dict[str, Any]:
    def finite_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, (bool, np.bool_)) and math.isfinite(float(value))

    def probability(value: Any) -> bool:
        return finite_number(value) and 0.0 <= float(value) <= 1.0

    def finite_interval(value: Any) -> bool:
        return (
            isinstance(value, list) and len(value) == 2
            and all(finite_number(bound) for bound in value)
            and float(value[0]) <= float(value[1])
        )

    def valid_executed(sensitivity_id: str, result: Mapping[str, Any]) -> bool:
        groups = result.get("groups")
        expected_estimands = SENSITIVITY_ESTIMANDS[sensitivity_id]
        if not isinstance(groups, Mapping) or set(groups) != set(GROUPS):
            return False
        for group_result in groups.values():
            if not isinstance(group_result, Mapping) or set(group_result) != expected_estimands:
                return False
            for estimand, estimate in group_result.items():
                if not isinstance(estimate, Mapping):
                    return False
                flow = estimate.get("flow")
                digest = estimate.get("row_set_digest")
                if not (
                    isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
                    and isinstance(flow, Mapping) and flow.get("reconciled") is True
                    and probability(estimate.get("raw_p_value"))
                    and probability(estimate.get("holm_adjusted_p_value"))
                ):
                    return False
                if estimand == "unadjusted" and not finite_interval(estimate.get("difference_ci")):
                    return False
                if estimand == "standardized" and not (
                    finite_interval(estimate.get("ci"))
                    and isinstance(estimate.get("valid_replicates"), int)
                    and not isinstance(estimate.get("valid_replicates"), bool)
                    and estimate["valid_replicates"] >= 950
                ):
                    return False
                if estimand == "regression_adjusted" and not (
                    finite_interval(estimate.get("ci"))
                    and finite_number(estimate.get("standard_error"))
                    and estimate["standard_error"] >= 0
                    and isinstance(estimate.get("clusters"), int)
                    and not isinstance(estimate.get("clusters"), bool)
                    and estimate["clusters"] >= 30
                ):
                    return False
        return True

    sensitivities = estimands.get("sensitivities")
    registry_valid = isinstance(sensitivities, Mapping) and set(sensitivities) == SENSITIVITY_IDS
    if registry_valid:
        for sensitivity_id, result in sensitivities.items():
            if not isinstance(result, Mapping):
                registry_valid = False
                break
            status = result.get("status")
            if sensitivity_id == "HMDA-SENS-YEAR":
                registry_valid &= status == "disabled_pending_separate_source_admission" and result.get("groups") is None
            else:
                registry_valid &= status in {"executed", "failed"}
                if sensitivity_id == "HMDA-SENS-ACTION-13":
                    registry_valid &= status == "executed"
                if status == "executed":
                    registry_valid &= valid_executed(sensitivity_id, result)
                elif status == "failed":
                    reasons = result.get("reason_codes")
                    registry_valid &= (
                        result.get("results_emitted") is False
                        and isinstance(reasons, list) and bool(reasons)
                        and all(isinstance(reason, str) and reason in SENSITIVITY_FAILURE_REASONS for reason in reasons)
                        and result.get("groups") is None
                    )
                else:
                    registry_valid = False
            if not registry_valid:
                break
    if not registry_valid:
        return fail_closed_artifact(
            source, ["hmda_sensitivity_registry_incomplete"],
            configuration_sha256=configuration_sha256, command=command,
            generated_at_utc=generated_at_utc,
        )
    failed_sensitivities = sorted(
        sensitivity_id
        for sensitivity_id, result in sensitivities.items()
        if result.get("status") == "failed"
    )
    if failed_sensitivities:
        artifact = fail_closed_artifact(
            source,
            ["hmda_sensitivity_registry_incomplete"],
            configuration_sha256=configuration_sha256,
            command=command,
            generated_at_utc=generated_at_utc,
        )
        artifact["sensitivity_failures"] = failed_sensitivities
        return artifact
    artifact = {
        "schema_version": "1.0.0", "contract_id": CONTRACT_ID,
        "source": source.as_dict(), "configuration_sha256": configuration_sha256,
        "constraint_status": "passed", "candidate_copy_status": LOCKED_STATUS,
        "results_emitted": True, "reason_codes": [], "cohort_flow": cohort_flow,
        "estimands": estimands,
        "interpretation_limits": ["association_only", "no_causal_claim", "no_discrimination_finding", "no_legal_conclusion"],
    }
    artifact.update(artifact_identity(command=command, generated_at_utc=generated_at_utc))
    return artifact


def fail_closed_artifact(
    source: SourceEvidence, reason_codes: Iterable[str], *, configuration_sha256: str,
    command: list[str] | None = None, generated_at_utc: str | None = None,
) -> dict[str, Any]:
    artifact = {
        "schema_version": "1.0.0", "contract_id": CONTRACT_ID,
        "source": source.as_dict(), "configuration_sha256": configuration_sha256,
        "constraint_status": "failed", "candidate_copy_status": LOCKED_STATUS,
        "results_emitted": False, "reason_codes": sorted(set(reason_codes)),
        "cohort_flow": None, "estimands": None,
        "interpretation_limits": ["association_only", "no_causal_claim", "no_discrimination_finding", "no_legal_conclusion"],
    }
    artifact.update(artifact_identity(command=command, generated_at_utc=generated_at_utc))
    return artifact


def configuration_sha256(manifest_directory: str | Path) -> str:
    directory = Path(manifest_directory)
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json_artifact(artifact: Mapping[str, Any], output: str | Path) -> None:
    Path(output).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
