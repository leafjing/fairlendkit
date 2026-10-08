"""Smoke-only engineering orchestration; confirmatory execution is locked."""

from __future__ import annotations

from dataclasses import dataclass

from fairlendkit.research.paper2.dgp import GeneratedAudit, generate_audit
from fairlendkit.research.paper2.protocol import ExecutionMode, load_protocol
from fairlendkit.research.paper2.registry import scenario_registry


@dataclass(frozen=True)
class SmokeRun:
    scenario_ids: tuple[str, ...]
    replicate_ids: tuple[int, ...]
    audits: tuple[GeneratedAudit, ...]


def run_smoke(
    scenario_ids: tuple[str, ...], replicate_ids: tuple[int, ...]
) -> SmokeRun:
    protocol = load_protocol()
    protocol.authorize(ExecutionMode.SMOKE, replicate_ids)
    registry = scenario_registry()
    unknown = sorted(set(scenario_ids) - registry.keys())
    if unknown:
        raise ValueError(f"Unknown registered scenarios: {unknown}")
    # Smoke runs use a separate master-seed namespace and cannot overlap the
    # frozen production generator stream.
    smoke_master_seed = protocol.master_seed + 10_000_000
    audits = tuple(
        generate_audit(registry[scenario_id], replicate_id, smoke_master_seed)
        for scenario_id in scenario_ids
        for replicate_id in replicate_ids
    )
    return SmokeRun(scenario_ids, replicate_ids, audits)
