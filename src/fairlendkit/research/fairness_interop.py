"""Deterministic, dependency-free fairness interoperability spike evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fairlendkit.metrics import (
    adverse_impact_ratio,
    demographic_parity_difference,
    roc_auc,
    selection_rate,
)


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


def build_interop_artifact() -> dict[str, Any]:
    """Return fixed evidence without importing Fairlearn or Aequitas.

    The spike deliberately separates executable FairLendKit results from
    external semantic mappings. External package results must not be inferred
    when optional dependencies are absent.
    """

    reference_rate = selection_rate(
        tuple(bool(row["decision"]) for row in _group_rows("reference"))
    )
    comparison_rate = selection_rate(
        tuple(bool(row["decision"]) for row in _group_rows("comparison"))
    )
    air = adverse_impact_ratio(comparison_rate, reference_rate)
    difference = demographic_parity_difference(comparison_rate, reference_rate)
    assert air.value is not None and difference.value is not None
    fairlendkit = {
        "reference": _group_metrics("reference"),
        "comparison": _group_metrics("comparison"),
        "directed_comparison_to_reference": {
            "adverse_impact_ratio": air.value,
            "selection_rate_difference": difference.value,
        },
    }
    artifact: dict[str, Any] = {
        "artifact_schema": "fairlendkit.fairness_interop_spike.v1",
        "evidence_status": "synthetic_semantic_spike_not_external_validation",
        "input": {
            "row_count": len(SAMPLE_ROWS),
            "sha256": sha256_json(SAMPLE_ROWS),
            "rows": list(SAMPLE_ROWS),
        },
        "fairlendkit": fairlendkit,
        "external_execution": {
            "fairlearn": {
                "status": "not_executed_no_runtime_dependency",
                "reported_values": None,
            },
            "aequitas": {
                "status": "not_executed_no_runtime_dependency",
                "reported_values": None,
            },
        },
        "semantic_differences": [
            {
                "concept": "group_selection_rate",
                "fairlendkit": "explicit favorable-decision rate per named group",
                "fairlearn": "requires explicit sensitive_features and selection-rate metric configuration",
                "aequitas": "candidate mapping must distinguish predicted prevalence from population share of predicted positives",
                "interop_gate": "do_not_compare_until_denominator_and_favorable_label_match",
            },
            {
                "concept": "selection_rate_ratio",
                "fairlendkit": "directed comparison_group / reference_group",
                "fairlearn": "default between-groups ratio may choose extrema rather than the configured reference group",
                "aequitas": "reference-group disparity configuration must be explicit",
                "interop_gate": "do_not_treat_equal_numbers_as_equal_semantics_without_reference_identity",
            },
            {
                "concept": "undefined_and_constant_score_auc",
                "fairlendkit": "constant scores with both positive-weight classes are defined AUC 0.5; absent or zero-weight class is undefined",
                "fairlearn": "package execution not performed in this dependency-free spike",
                "aequitas": "package execution not performed in this dependency-free spike",
                "interop_gate": "preserve_package_status_and_reason_instead_of_coercing_undefined_to_zero",
            },
        ],
        "limitations": [
            "No Fairlearn or Aequitas package was imported or executed.",
            "This artifact is not a performance benchmark or production-data result.",
            "External version and license identities belong to the separately reviewed comparison document.",
        ],
    }
    artifact["result_sha256"] = sha256_json(
        {key: value for key, value in artifact.items() if key != "result_sha256"}
    )
    return artifact
