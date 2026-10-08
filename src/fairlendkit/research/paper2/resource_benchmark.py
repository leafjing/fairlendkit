"""Isolated full-chain smoke benchmark without confirmatory result disclosure."""

from __future__ import annotations

import resource
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from fairlendkit import AuditConfig, run_audit
from fairlendkit.metrics.contracts import MetricNameV2
from fairlendkit.research.paper2.execution import (
    DISK_SAFETY_FACTOR,
    MEMORY_BUDGET_GIB,
    MEMORY_SAFETY_FACTOR,
    RUNTIME_SAFETY_FACTOR,
    WORKER_COUNT,
    ExecutionManifest,
    ExecutionWorkspace,
    IntegrityError,
    RawReplicatePayload,
    RawReplicateRecord,
    SmokeBenchmarkEvidence,
    frozen_execution_scenario_ids,
    smoke_shards,
    validate_shard,
    write_smoke_shard,
)
from fairlendkit.research.paper2.protocol import CONFIRMATORY_REPLICATES
from fairlendkit.research.paper2.registry import scenario_registry
from fairlendkit.research.paper2.smoke import run_smoke


BENCHMARK_SCENARIO_IDS = (
    "REG",
    "SEL-AIR081-N1000",
    "MISS-MCAR30",
    "MISS-MNAR30",
)


def benchmark_full_smoke_pipeline(manifest: ExecutionManifest) -> SmokeBenchmarkEvidence:
    """Measure representative DGP→audit/reliability smoke replicates conservatively."""
    scenario_ids = BENCHMARK_SCENARIO_IDS
    registry = scenario_registry()
    _validate_benchmark_coverage(registry, scenario_ids)
    wall_measurements: list[float] = []
    cpu_measurements: list[float] = []
    observed_metric_names: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="paper2-full-smoke-") as directory:
        workspace = ExecutionWorkspace(Path(directory).resolve(), "smoke")
        for scenario_id in scenario_ids:
            scenario = registry[scenario_id]
            cpu_start = time.process_time()
            wall_start = time.perf_counter()
            generated = run_smoke((scenario_id,), (0,)).audits[0]
            frame = pd.DataFrame(
                (
                    {
                        "outcome": row.outcome,
                        "score": row.score,
                        "decision": row.decision,
                        "group": row.group,
                    }
                    for row in generated.rows
                )
            )
            result = run_audit(frame, _audit_config(scenario))
            observed_metric_names.update(item.metric.value for item in result.observed_metrics)
            spec = smoke_shards(scenario_id, replicates=1, shard_size=1)[0]
            write_smoke_shard(
                workspace,
                manifest,
                spec,
                (RawReplicateRecord(scenario_id, 0, _raw_payload(result)),),
            )
            validate_shard(workspace, manifest, spec)
            wall_measurements.append(time.perf_counter() - wall_start)
            cpu_measurements.append(time.process_time() - cpu_start)
        expected_metric_names = {item.value for item in MetricNameV2}
        if observed_metric_names != expected_metric_names:
            raise IntegrityError("Resource benchmark does not cover every frozen metric path.")
        artifact_bytes = sum(path.stat().st_size for path in workspace.output_dir.iterdir())
    wall_seconds = max(wall_measurements)
    cpu_seconds = max(cpu_measurements)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if sys.platform == "darwin" else peak_rss * 1024
    projected_records = len(frozen_execution_scenario_ids()) * CONFIRMATORY_REPLICATES
    return SmokeBenchmarkEvidence(
        schema_version="paper2-resource-benchmark-v1",
        smoke_records=len(scenario_ids),
        wall_seconds=wall_seconds,
        cpu_seconds=cpu_seconds,
        peak_rss_bytes=peak_rss_bytes,
        artifact_bytes=artifact_bytes,
        projected_records=projected_records,
        projected_cpu_hours=cpu_seconds * projected_records * RUNTIME_SAFETY_FACTOR / 3600,
        projected_wall_hours=wall_seconds * projected_records * RUNTIME_SAFETY_FACTOR / 3600 / WORKER_COUNT,
        projected_disk_bytes=int(artifact_bytes / len(scenario_ids) * projected_records * DISK_SAFETY_FACTOR),
        required_memory_bytes=max(
            MEMORY_BUDGET_GIB * 1024**3,
            int(peak_rss_bytes * MEMORY_SAFETY_FACTOR),
        ),
        safety_factor=RUNTIME_SAFETY_FACTOR,
    )


def _validate_benchmark_coverage(registry, scenario_ids: tuple[str, ...]) -> None:
    """Fail closed unless every frozen scenario has a measured cost dominator."""
    frozen = tuple(registry[item] for item in frozen_execution_scenario_ids())
    representatives = tuple(registry[item] for item in scenario_ids)
    if {item.family for item in representatives} != {item.family for item in frozen}:
        raise IntegrityError("Resource benchmark does not cover every scenario family.")
    if {item.missingness for item in representatives} != {item.missingness for item in frozen}:
        raise IntegrityError("Resource benchmark does not cover every missingness path.")
    if {item.calibration for item in representatives} != {item.calibration for item in frozen}:
        raise IntegrityError("Resource benchmark does not cover every calibration path.")

    maxima = (
        (lambda item: item.comparison_n + item.reference_n, "sample-size"),
        (lambda item: item.missing_fraction, "missing-fraction"),
        (lambda item: item.bootstrap_resamples, "bootstrap-resamples"),
        (lambda item: item.minimum_valid_resamples, "valid-resample"),
    )
    for value, label in maxima:
        if max(map(value, representatives)) < max(map(value, frozen)):
            raise IntegrityError(f"Resource benchmark does not cover the maximum {label} workload.")

    coverage = _benchmark_coverage_matrix(registry, scenario_ids)
    if set(coverage) != set(frozen_execution_scenario_ids()):
        raise IntegrityError("Resource benchmark cost coverage matrix is incomplete.")


def _benchmark_coverage_matrix(
    registry, scenario_ids: tuple[str, ...]
) -> dict[str, str]:
    """Map every execution scenario to a measured scenario that dominates its cost axes."""
    representatives = tuple(registry[item] for item in scenario_ids)
    coverage: dict[str, str] = {}
    for frozen_id in frozen_execution_scenario_ids():
        frozen = registry[frozen_id]
        candidates = tuple(
            representative
            for representative in representatives
            if representative.family == frozen.family
            and representative.missingness == frozen.missingness
            and representative.calibration == frozen.calibration
            and representative.comparison_n + representative.reference_n
            >= frozen.comparison_n + frozen.reference_n
            and representative.missing_fraction >= frozen.missing_fraction
            and representative.bootstrap_resamples >= frozen.bootstrap_resamples
            and representative.minimum_valid_resamples
            >= frozen.minimum_valid_resamples
        )
        if not candidates:
            raise IntegrityError(
                f"Resource benchmark has no measured cost dominator for {frozen_id}."
            )
        coverage[frozen_id] = min(item.scenario_id for item in candidates)
    return coverage


def _audit_config(scenario) -> AuditConfig:
    return AuditConfig(
        outcome_column="outcome",
        score_column="score",
        decision_column="decision",
        population_definition="Paper 2 isolated smoke benchmark",
        sampling_definition=f"One non-confirmatory {scenario.scenario_id} smoke replicate",
        score_type="probability",
        dataset_version="paper2-smoke-v1",
        model_version="paper2-smoke-v1",
        data_as_of="2026-10-08T00:00:00Z",
        execution_timestamp="2026-10-08T00:00:00Z",
        favorable_label=1,
        favorable_decision_label=1,
        score_direction="higher_is_more_favorable",
        protected_attributes=("group",),
        reference_groups={"group": 0},
        allowed_groups={"group": (0, 1)},
        minimum_group_size=scenario.minimum_group_size,
        bootstrap_seed=7,
        bootstrap_resamples=scenario.bootstrap_resamples,
        minimum_valid_resamples=scenario.minimum_valid_resamples,
        confidence_level=scenario.confidence_level,
        air_screening_threshold=scenario.air_threshold,
        missing_value_policy="exclude",
        duplicate_policy="allow",
    )


def _raw_payload(result) -> RawReplicatePayload:
    intervals = {item.metric_key: (item.lower, item.upper) for item in result.uncertainty}
    metrics = tuple(result.observed_metrics)
    return RawReplicatePayload(
        schema_version="paper2-raw-replicate-v1",
        metric_values=tuple(sorted((item.key, item.value.value) for item in metrics)),
        metric_defined=tuple(sorted((item.key, item.value.is_defined) for item in metrics)),
        reliability=tuple(sorted((item.key, item.reliability.value) for item in metrics)),
        uncertainty=tuple(sorted((item.key, intervals.get(item.key)) for item in metrics)),
        flags=tuple(
            sorted(
                (item.code, item.related_metric_key)
                for item in result.screening_flags
                if item.related_metric_key is not None
            )
        ),
        limitations=tuple(
            sorted(
                (str(item.code), key)
                for item in result.limitations
                for key in item.affected_metric_keys
            )
        ),
    )
