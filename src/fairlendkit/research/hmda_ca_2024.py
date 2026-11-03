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
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from zipfile import ZipFile

import numpy as np
import pandas as pd


SOURCE_URL = "https://files.ffiec.cfpb.gov/static-data/snapshot/2024/2024_public_lar_csv.zip"
SOURCE_BYTES = 664_242_987
SOURCE_SHA256 = "9383890f38c2ae1ef46942e72e1a2a211aa0b979c0e46db5fd6d7eb8669f22c1"
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
        ):
            raise HMDAContractError("hmda_source_identity_mismatch", "unsafe member")
        with zipped.open(member) as raw:
            header_raw = raw.readline().rstrip(b"\r\n")
            try:
                header = tuple(next(csv.reader([header_raw.decode("utf-8-sig")])))
            except (UnicodeDecodeError, csv.Error) as exc:
                raise HMDAContractError("hmda_source_identity_mismatch", "invalid header") from exc
            if not set(REQUIRED_FIELDS).issubset(header):
                raise HMDAContractError("hmda_schema_required_field_missing")
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
        header_sha256=hashlib.sha256(header_raw).hexdigest(),
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


def construct_cohort(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen ordered cohort rules and return aggregate flow only."""

    missing = sorted(set(REQUIRED_FIELDS) - set(frame.columns))
    if missing:
        raise HMDAContractError("hmda_schema_required_field_missing", ",".join(missing))
    current = _clean_strings(frame)
    flow: dict[str, Any] = {"source_rows": int(len(current)), "exclusions": []}
    for field, allowed, reason in COHORT_RULES:
        keep = current[field].isin(allowed)
        flow["exclusions"].append({"reason_code": reason, "rows": int((~keep).sum())})
        current = current.loc[keep].copy()
    flow["cohort_rows"] = int(len(current))
    return current, flow


def normalize_analysis_fields(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for field in ("loan_amount", "income", "property_value", "loan_term"):
        result[field + "_numeric"] = pd.to_numeric(result[field], errors="coerce")
    cltv = result["combined_loan_to_value_ratio"]
    result["cltv_numeric"] = pd.to_numeric(cltv, errors="coerce")
    result.loc[~result["cltv_numeric"].between(0, 1000), "cltv_numeric"] = np.nan
    result["dti_band"] = result["debt_to_income_ratio"].map(DTI_MAP)
    result["applicant_age_band"] = result["applicant_age"].map(AGE_MAP)
    result["favorable_action"] = result["action_taken"].isin(["1", "2"]).astype(int)
    return result


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
    return {
        "row_count": int(len(selected)), "counts": counts,
        "focal_rate": pf, "reference_rate": pr, "difference": pf - pr,
        "ratio": None if pr == 0 else pf / pr,
        "focal_rate_ci": _wilson(yf, nf), "reference_rate_ci": _wilson(yr, nr),
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
    evidence = {"supported_strata": len(supported), "retained_fraction": fractions, "overall_supported_fraction": overall}
    if len(supported) < 20 or overall < 0.7 or min(fractions.values()) < 0.7:
        raise HMDAContractError("hmda_common_support_insufficient", json.dumps(evidence, sort_keys=True))
    return retained, evidence


def standardized_estimate(frame: pd.DataFrame, group_field: str, focal: str, reference: str) -> dict[str, Any]:
    supported, evidence = apply_common_support(frame, group_field, focal, reference)
    keys = ["income_band", "loan_amount_band", "dti_band", "cltv_band"]
    total = len(supported)
    difference = 0.0
    for _, block in supported.groupby(keys, observed=True):
        weight = len(block) / total
        rates = block.groupby(group_field, observed=True)["favorable_action"].mean()
        difference += weight * (float(rates[focal]) - float(rates[reference]))
    return {"row_count": total, "difference": difference, "support": evidence}


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


def fail_closed_artifact(source: SourceEvidence, reason_codes: Iterable[str], *, configuration_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "contract_id": CONTRACT_ID,
        "source": source.as_dict(), "configuration_sha256": configuration_sha256,
        "constraint_status": "failed", "candidate_copy_status": LOCKED_STATUS,
        "results_emitted": False, "reason_codes": sorted(set(reason_codes)),
        "cohort_flow": None, "estimands": None,
        "interpretation_limits": ["association_only", "no_causal_claim", "no_discrimination_finding", "no_legal_conclusion"],
    }


def configuration_sha256(manifest_directory: str | Path) -> str:
    directory = Path(manifest_directory)
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json_artifact(artifact: Mapping[str, Any], output: str | Path) -> None:
    Path(output).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
