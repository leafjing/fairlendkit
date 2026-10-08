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
BENCHMARK_COST_COVERAGE = (
    ("MISS-MCAR30", "MISS-MCAR30"),
    ("MISS-MNAR30", "MISS-MNAR30"),
    ("PERF-DEC001", "REG"),
    ("PERF-DEC050", "REG"),
    *((scenario_id, "SEL-AIR081-N1000") for scenario_id in (
        "SEL-AIR060-N025", "SEL-AIR060-N050", "SEL-AIR060-N100", "SEL-AIR060-N1000", "SEL-AIR060-N250",
        "SEL-AIR079-N025", "SEL-AIR079-N050", "SEL-AIR079-N100", "SEL-AIR079-N1000", "SEL-AIR079-N250",
        "SEL-AIR080-N025", "SEL-AIR080-N050", "SEL-AIR080-N100", "SEL-AIR080-N1000", "SEL-AIR080-N250",
        "SEL-AIR081-N025", "SEL-AIR081-N050", "SEL-AIR081-N100", "SEL-AIR081-N1000", "SEL-AIR081-N250",
        "SEL-AIR100-N025", "SEL-AIR100-N050", "SEL-AIR100-N100", "SEL-AIR100-N1000", "SEL-AIR100-N250",
    )),
)


def benchmark_full_smoke_pipeline(manifest: ExecutionManifest) -> SmokeBenchmarkEvidence:
    """Measure representative DGP→audit/reliability smoke replicates conservatively."""
    scenario_ids = BENCHMARK_SCENARIO_IDS
    registry = scenario_registry()
    coverage = _validate_benchmark_coverage(registry, scenario_ids)
    wall_measurements: dict[str, float] = {}
    cpu_measurements: dict[str, float] = {}
    artifact_measurements: dict[str, int] = {}
    expected_metric_names = {item.value for item in MetricNameV2}
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
            payload = _raw_payload(result)
            _validate_representative_output(result, payload, expected_metric_names)
            spec = smoke_shards(scenario_id, replicates=1, shard_size=1)[0]
            write_smoke_shard(
                workspace,
                manifest,
                spec,
                (RawReplicateRecord(scenario_id, 0, payload),),
            )
            validate_shard(workspace, manifest, spec)
            wall_measurements[scenario_id] = time.perf_counter() - wall_start
            cpu_measurements[scenario_id] = time.process_time() - cpu_start
            artifact_measurements[scenario_id] = sum(
                path.stat().st_size
                for path in workspace.output_dir.glob(f"{scenario_id}--00000*")
            )
        artifact_bytes = sum(path.stat().st_size for path in workspace.output_dir.iterdir())
    wall_seconds = max(wall_measurements.values())
    cpu_seconds = max(cpu_measurements.values())
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if sys.platform == "darwin" else peak_rss * 1024
    projected_records = len(frozen_execution_scenario_ids()) * CONFIRMATORY_REPLICATES
    projected_cpu_hours, projected_wall_hours, projected_disk_bytes = (
        _project_benchmark_costs(
            coverage,
            cpu_measurements,
            wall_measurements,
            artifact_measurements,
        )
    )
    return SmokeBenchmarkEvidence(
        schema_version="paper2-resource-benchmark-v1",
        smoke_records=len(scenario_ids),
        wall_seconds=wall_seconds,
        cpu_seconds=cpu_seconds,
        peak_rss_bytes=peak_rss_bytes,
        artifact_bytes=artifact_bytes,
        projected_records=projected_records,
        projected_cpu_hours=projected_cpu_hours,
        projected_wall_hours=projected_wall_hours,
        projected_disk_bytes=projected_disk_bytes,
        required_memory_bytes=max(
            MEMORY_BUDGET_GIB * 1024**3,
            int(peak_rss_bytes * MEMORY_SAFETY_FACTOR),
        ),
        safety_factor=RUNTIME_SAFETY_FACTOR,
    )


def _validate_benchmark_coverage(registry, scenario_ids: tuple[str, ...]) -> dict[str, str]:
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

    return _benchmark_coverage_matrix(registry, scenario_ids)


def _benchmark_coverage_matrix(
    registry,
    scenario_ids: tuple[str, ...],
    entries: tuple[tuple[str, str], ...] = BENCHMARK_COST_COVERAGE,
) -> dict[str, str]:
    """Validate the frozen scenario-to-measurement cost coverage matrix."""
    if len({item[0] for item in entries}) != len(entries):
        raise IntegrityError("Resource benchmark cost coverage matrix has duplicate scenarios.")
    coverage = dict(entries)
    if set(coverage) != set(frozen_execution_scenario_ids()):
        raise IntegrityError("Resource benchmark cost coverage matrix is incomplete or unknown.")
    if not set(coverage.values()).issubset(set(scenario_ids)):
        raise IntegrityError("Resource benchmark cost coverage matrix names an unmeasured representative.")
    for frozen_id, representative_id in coverage.items():
        frozen = registry[frozen_id]
        representative = registry[representative_id]
        dominates = (
            representative.family == frozen.family
            and representative.missingness == frozen.missingness
            and representative.calibration == frozen.calibration
            and representative.comparison_n + representative.reference_n
            >= frozen.comparison_n + frozen.reference_n
            and representative.missing_fraction >= frozen.missing_fraction
            and representative.bootstrap_resamples >= frozen.bootstrap_resamples
            and representative.minimum_valid_resamples >= frozen.minimum_valid_resamples
        )
        if not dominates:
            raise IntegrityError(
                f"Resource benchmark representative does not dominate {frozen_id}."
            )
    return coverage


def _project_benchmark_costs(
    coverage: dict[str, str],
    cpu_seconds: dict[str, float],
    wall_seconds: dict[str, float],
    artifact_bytes: dict[str, int],
) -> tuple[float, float, int]:
    """Sum measured representative costs per frozen scenario without averaging."""
    representatives = set(coverage.values())
    for measurements in (cpu_seconds, wall_seconds, artifact_bytes):
        if set(measurements) != representatives:
            raise IntegrityError("Resource benchmark measurements do not match coverage representatives.")
    multiplier = CONFIRMATORY_REPLICATES
    cpu_total = sum(cpu_seconds[coverage[item]] * multiplier for item in coverage)
    wall_total = sum(wall_seconds[coverage[item]] * multiplier for item in coverage)
    disk_total = sum(artifact_bytes[coverage[item]] * multiplier for item in coverage)
    return (
        cpu_total * RUNTIME_SAFETY_FACTOR / 3600,
        wall_total * RUNTIME_SAFETY_FACTOR / 3600 / WORKER_COUNT,
        int(disk_total * DISK_SAFETY_FACTOR),
    )


def _validate_representative_output(
    result, payload: RawReplicatePayload, expected_metric_names: set[str]
) -> None:
    """Require each cost representative to exercise the full frozen output schema."""
    observed = {item.metric.value for item in result.observed_metrics}
    if observed != expected_metric_names:
        raise IntegrityError(
            "Each resource benchmark representative must cover every frozen metric path."
        )
    if payload.schema_version != "paper2-raw-replicate-v1":
        raise IntegrityError("Resource benchmark artifact schema is not frozen.")
    payload_keys = {key for key, _ in payload.metric_values}
    if payload_keys != {item.key for item in result.observed_metrics}:
        raise IntegrityError("Resource benchmark artifact does not preserve all metric keys.")


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
