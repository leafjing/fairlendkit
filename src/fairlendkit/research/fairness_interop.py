"""Deterministic, dependency-free fairness interoperability spike evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from fairlendkit.metrics import (
    adverse_impact_ratio,
    demographic_parity_difference,
    roc_auc,
    selection_rate,
)


ExecutionStatus = Literal[
    "not_executed",
    "dependency_identity_mismatch",
    "execution_failed",
    "execution_succeeded",
]

PACKAGE_IDENTITIES = {
    "fairlearn": {
        "package": "fairlearn",
        "version": "0.15.0",
        "artifact": "fairlearn-0.15.0-py3-none-any.whl",
        "sha256": "4f4656c25af384fc3369db719231680c4e83beb2e6e075e5dc3c2b27d06455c9",
        "license": "MIT",
        "source_url": "https://pypi.org/project/fairlearn/0.15.0/",
    },
    "aequitas": {
        "package": "aequitas",
        "version": "1.1.0",
        "artifact": "aequitas-1.1.0-py3-none-any.whl",
        "sha256": "a99b8031a499577251fb26fae2ff20f2b23b2ad759cc8657b8afaae53bbc0b33",
        "license": "MIT",
        "source_url": "https://pypi.org/project/aequitas/1.1.0/",
    },
}

SAMPLE_ROWS: tuple[dict[str, object], ...] = (
    {"id": "R1", "group": "reference", "outcome": True, "decision": True, "score": 0.9},
    {"id": "R2", "group": "reference", "outcome": True, "decision": True, "score": 0.7},
    {"id": "R3", "group": "reference", "outcome": False, "decision": True, "score": 0.6},
    {"id": "R4", "group": "reference", "outcome": False, "decision": False, "score": 0.2},
    {"id": "C1", "group": "comparison", "outcome": True, "decision": True, "score": 0.8},
    {"id": "C2", "group": "comparison", "outcome": True, "decision": False, "score": 0.4},
    {"id": "C3", "group": "comparison", "outcome": False, "decision": True, "score": 0.5},
    {"id": "C4", "group": "comparison", "outcome": False, "decision": False, "score": 0.1},
)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _group_rows(group: str) -> tuple[dict[str, object], ...]:
    return tuple(row for row in SAMPLE_ROWS if row["group"] == group)


def _group_metrics(group: str) -> dict[str, float]:
    rows = _group_rows(group)
    rate = selection_rate(tuple(bool(row["decision"]) for row in rows))
    auc = roc_auc(
        tuple(bool(row["outcome"]) for row in rows),
        tuple(float(row["score"]) for row in rows),
    )
    assert rate.value is not None and auc.value is not None
    return {"selection_rate": rate.value, "roc_auc": auc.value}


def _auc_case(
    case_id: str,
    outcomes: tuple[bool, ...],
    scores: tuple[float, ...],
    weights: tuple[float, ...] | None = None,
) -> dict[str, object]:
    try:
        result = roc_auc(outcomes, scores, weights)
    except (TypeError, ValueError):
        return {
            "case_id": case_id,
            "value": None,
            "status": "undefined",
            "reason_code": "invalid_score",
            "weight_mode": "weighted" if weights is not None else "unweighted",
        }
    return {
        "case_id": case_id,
        "value": result.value,
        "numerator": result.numerator,
        "denominator": result.denominator,
        "status": "defined" if result.value is not None else "undefined",
        "reason_code": result.undefined_reason,
        "weight_mode": "weighted" if weights is not None else "unweighted",
    }


def _auc_contract_cases() -> list[dict[str, object]]:
    return [
        _auc_case("constant_two_class_unweighted", (True, False), (0.5, 0.5)),
        _auc_case(
            "constant_two_class_weighted",
            (True, False, True, False),
            (0.5, 0.5, 0.5, 0.5),
            (2.0, 3.0, 1.0, 4.0),
        ),
        _auc_case("mixed_ties", (True, False, True), (0.5, 0.5, 0.9)),
        _auc_case("single_class", (True, True), (0.2, 0.8)),
        _auc_case(
            "zero_unfavorable_class_weight",
            (True, False),
            (0.8, 0.2),
            (1.0, 0.0),
        ),
        _auc_case("empty_sample", (), ()),
        _auc_case("invalid_score", (True, False), (float("nan"), 0.2)),
    ]


def _execution_record(tool: str, status: ExecutionStatus) -> dict[str, object]:
    if status not in {
        "not_executed",
        "dependency_identity_mismatch",
        "execution_failed",
        "execution_succeeded",
    }:
        raise ValueError("unsupported execution status")
    reason_by_status = {
        "not_executed": "external_not_executed",
        "dependency_identity_mismatch": "dependency_identity_mismatch",
        "execution_failed": "external_execution_failed",
        # No raw output is supplied by this dependency-free spike, so even a
        # forged success status remains fail closed.
        "execution_succeeded": "external_output_invalid",
    }
    return {
        "execution_status": status,
        "reason_code": reason_by_status[status],
        "expected_package_identity": PACKAGE_IDENTITIES[tool],
        "identity_verified": False,
        "command": [
            "python",
            "-m",
            "fairlendkit.research.external_fairness_adapter",
            "--tool",
            tool,
            "--input",
            "fixed-synthetic-v1",
        ],
        "command_status": "planned_not_executed",
        "exit_status": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "started_at_utc": None,
        "ended_at_utc": None,
        "raw_output": None,
        "reported_values": None,
        "normalized_values": None,
        "value_match": None,
    }


def build_interop_artifact(
    *,
    fairlearn_status: ExecutionStatus = "not_executed",
    aequitas_status: ExecutionStatus = "not_executed",
) -> dict[str, Any]:
    """Return fixed evidence without importing Fairlearn or Aequitas."""

    reference_rate = selection_rate(
        tuple(bool(row["decision"]) for row in _group_rows("reference"))
    )
    comparison_rate = selection_rate(
        tuple(bool(row["decision"]) for row in _group_rows("comparison"))
    )
    air = adverse_impact_ratio(comparison_rate, reference_rate)
    difference = demographic_parity_difference(comparison_rate, reference_rate)
    assert air.value is not None and difference.value is not None
    external = {
        "fairlearn": _execution_record("fairlearn", fairlearn_status),
        "aequitas": _execution_record("aequitas", aequitas_status),
    }
    reasons = {record["reason_code"] for record in external.values()}
    top_reason = next(
        reason
        for reason in (
            "dependency_identity_mismatch",
            "external_execution_failed",
            "external_not_executed",
            "external_output_invalid",
        )
        if reason in reasons
    )
    artifact: dict[str, Any] = {
        "artifact_schema": "fairlendkit.fairness_interop_spike.v2",
        "evidence_class": "external_interoperability_spike_not_production_validation",
        "evidence_status": "synthetic_semantic_spike_external_not_executed",
        "constraint_status": "failed",
        "reason_code": top_reason,
        "candidate_copy_status": "locked_research_only",
        "comparisons_emitted": False,
        "match_total": None,
        "mismatch_total": None,
        "not_comparable_total": None,
        "execution_failure_total": None,
        "comparison_totals": {
            "matches": None,
            "mismatches": None,
            "not_comparable": None,
            "execution_failures": None,
        },
        "input": {
            "row_count": len(SAMPLE_ROWS),
            "sha256": sha256_json(SAMPLE_ROWS),
            "rows": list(SAMPLE_ROWS),
        },
        "fairlendkit": {
            "reference": _group_metrics("reference"),
            "comparison": _group_metrics("comparison"),
            "directed_comparison_to_reference": {
                "adverse_impact_ratio": air.value,
                "selection_rate_difference": difference.value,
            },
            "auc_contract_cases": _auc_contract_cases(),
        },
        "external_execution": external,
        "metric_support": {
            "roc_auc": {
                "fairlearn": {
                    "api": "MetricFrame(metrics=sklearn.metrics.roc_auc_score, ...)",
                    "execution_status": fairlearn_status,
                    "normalized_value": None,
                    "value_match": None,
                    "reason_code": "external_not_executed",
                },
                "aequitas": {
                    "api": None,
                    "support_status": "metric_not_supported",
                    "execution_status": aequitas_status,
                    "normalized_value": None,
                    "value_match": None,
                    "reason_code": "metric_not_supported",
                },
            }
        },
        "acceptance_rules": [
            "fairlearn_not_executed_fails_closed",
            "aequitas_not_executed_fails_closed",
            "dependency_identity_mismatch_fails_before_comparison",
            "execution_failure_emits_no_totals",
            "constant_two_class_auc_is_half_for_supported_implementations",
            "undefined_auc_cases_are_not_coerced",
            "aequitas_auc_is_metric_not_supported",
            "fixture_values_cannot_promote_external_execution_status",
        ],
        "limitations": [
            "No Fairlearn or Aequitas package was installed, imported, or executed.",
            "No external normalized value, value match, total, or compatibility conclusion is emitted.",
            "This artifact uses only fixed synthetic rows and is not production validation.",
        ],
    }
    artifact["result_sha256"] = sha256_json(
        {key: value for key, value in artifact.items() if key != "result_sha256"}
    )
    return artifact
