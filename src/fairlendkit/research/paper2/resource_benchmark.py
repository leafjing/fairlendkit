"""Isolated full-chain smoke benchmark without confirmatory result disclosure."""

from __future__ import annotations

import resource
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from fairlendkit import AuditConfig, run_audit
from fairlendkit.research.paper2.execution import (
    DISK_SAFETY_FACTOR,
    MEMORY_BUDGET_GIB,
    MEMORY_SAFETY_FACTOR,
    RUNTIME_SAFETY_FACTOR,
    WORKER_COUNT,
    ExecutionManifest,
    ExecutionWorkspace,
    SmokeBenchmarkEvidence,
    benchmark_smoke_resources,
    frozen_execution_scenario_ids,
)
from fairlendkit.research.paper2.protocol import CONFIRMATORY_REPLICATES
from fairlendkit.research.paper2.registry import scenario_registry
from fairlendkit.research.paper2.smoke import run_smoke


def benchmark_full_smoke_pipeline(manifest: ExecutionManifest) -> SmokeBenchmarkEvidence:
    """Measure representative DGP→audit/reliability smoke replicates conservatively."""
    scenario_ids = ("REG", "SEL-AIR081-N1000", "MISS-MNAR30")
    registry = scenario_registry()
    wall_measurements: list[float] = []
    cpu_measurements: list[float] = []
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
        run_audit(frame, _audit_config(scenario))
        wall_measurements.append(time.perf_counter() - wall_start)
        cpu_measurements.append(time.process_time() - cpu_start)
    with tempfile.TemporaryDirectory(prefix="paper2-full-smoke-") as directory:
        raw = benchmark_smoke_resources(
            ExecutionWorkspace(Path(directory).resolve(), "smoke"), manifest
        )
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
        artifact_bytes=raw.artifact_bytes,
        projected_records=projected_records,
        projected_cpu_hours=cpu_seconds * projected_records * RUNTIME_SAFETY_FACTOR / 3600,
        projected_wall_hours=wall_seconds * projected_records * RUNTIME_SAFETY_FACTOR / 3600 / WORKER_COUNT,
        projected_disk_bytes=int(raw.artifact_bytes / raw.smoke_records * projected_records * DISK_SAFETY_FACTOR),
        required_memory_bytes=max(
            MEMORY_BUDGET_GIB * 1024**3,
            int(peak_rss_bytes * MEMORY_SAFETY_FACTOR),
        ),
        safety_factor=RUNTIME_SAFETY_FACTOR,
    )


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
