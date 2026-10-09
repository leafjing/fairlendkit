"""Machine-readable boundary for the frozen Paper 2 protocol."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

MASTER_SEED = 20261008
PROTOCOL_ID = "fairlendkit-paper2-v1"
SMOKE_SEED_DOMAIN = "fairlendkit-paper2-smoke-v1"
CONFIRMATORY_REPLICATES = 5_000
EXPLORATORY_REPLICATES = 10_000
MONITORING_CHECKPOINTS = (1_000, 2_000, 3_000, 4_000)
CONFIRMATORY_TEST_IDS = (
    "P2-C1-AIR-MAE-N",
    "P2-C3-PRECISION-DEFINED",
    "P2-C4-AIR-FP-GATE",
    "P2-C5-MISSINGNESS-MAE",
    "P2-C6-AIR-COVERAGE",
)
RNG_SCHEMA_VERSION = "paper2-rng-a1-v1"
RNG_FIXTURE_SHA256 = "6e5d99c5531c03e3501dc0be16d68faf5338beb7b6246782f5a7623730577905"
A2_PROTOCOL_COMMIT = "4a83ff8872d3393fad4313927045777f65fd3da4"
A2_SPECIFICATION_COMMIT = "9aa1afe0d48fedebdc5e9f26fecf31f68235838d"


class ExecutionMode(StrEnum):
    SMOKE = "smoke"
    CONFIRMATORY = "confirmatory"


class ProductionRunLockedError(RuntimeError):
    """Raised while phase one intentionally forbids confirmatory execution."""


@dataclass(frozen=True)
class Paper2Protocol:
    protocol_id: str
    status: str
    rng_schema_version: str
    rng_fixture_sha256: str
    a2_protocol_commit: str
    a2_specification_commit: str
    master_seed: int
    confirmatory_replicates: int
    exploratory_replicates: int
    monitoring_checkpoints: tuple[int, ...]
    confirmatory_test_ids: tuple[str, ...]
    smoke_seed_domain: str

    def authorize(self, mode: ExecutionMode, replicate_ids: tuple[int, ...]) -> None:
        if mode is not ExecutionMode.SMOKE:
            raise ProductionRunLockedError(
                "Confirmatory execution remains locked until the implementation "
                "and reproduction gate is independently approved."
            )
        if not replicate_ids or any(value < 0 or value >= 100 for value in replicate_ids):
            raise ValueError("Smoke replicate IDs must be in the isolated range 0..99.")


def load_protocol(path: str | Path | None = None) -> Paper2Protocol:
    manifest_path = Path(path) if path else Path(__file__).with_name("protocol.json")
    raw: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "protocol_id",
        "status",
        "rng_schema_version",
        "rng_fixture_sha256",
        "a2_protocol_commit",
        "a2_specification_commit",
        "master_seed",
        "confirmatory_replicates",
        "exploratory_replicates",
        "monitoring_checkpoints",
        "confirmatory_test_ids",
        "smoke_seed_domain",
    }
    if set(raw) != required:
        raise ValueError("Paper 2 protocol manifest fields do not match the frozen schema.")
    protocol = Paper2Protocol(
        protocol_id=str(raw["protocol_id"]),
        status=str(raw["status"]),
        rng_schema_version=str(raw["rng_schema_version"]),
        rng_fixture_sha256=str(raw["rng_fixture_sha256"]),
        a2_protocol_commit=str(raw["a2_protocol_commit"]),
        a2_specification_commit=str(raw["a2_specification_commit"]),
        master_seed=int(raw["master_seed"]),
        confirmatory_replicates=int(raw["confirmatory_replicates"]),
        exploratory_replicates=int(raw["exploratory_replicates"]),
        monitoring_checkpoints=tuple(int(v) for v in raw["monitoring_checkpoints"]),
        confirmatory_test_ids=tuple(str(v) for v in raw["confirmatory_test_ids"]),
        smoke_seed_domain=str(raw["smoke_seed_domain"]),
    )
    if (
        protocol.protocol_id != PROTOCOL_ID
        or protocol.master_seed != MASTER_SEED
        or protocol.rng_schema_version != RNG_SCHEMA_VERSION
        or protocol.rng_fixture_sha256 != RNG_FIXTURE_SHA256
        or protocol.a2_protocol_commit != A2_PROTOCOL_COMMIT
        or protocol.a2_specification_commit != A2_SPECIFICATION_COMMIT
        or protocol.confirmatory_replicates != CONFIRMATORY_REPLICATES
        or protocol.exploratory_replicates != EXPLORATORY_REPLICATES
        or protocol.monitoring_checkpoints != MONITORING_CHECKPOINTS
        or protocol.confirmatory_test_ids != CONFIRMATORY_TEST_IDS
        or protocol.status != "frozen"
        or protocol.smoke_seed_domain != SMOKE_SEED_DOMAIN
    ):
        raise ValueError("Paper 2 manifest conflicts with the approved protocol constants.")
    return protocol
