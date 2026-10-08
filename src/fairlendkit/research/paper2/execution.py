"""Paper 2 execution-gate primitives; confirmatory execution remains locked."""

from __future__ import annotations

import hashlib
import json
import platform
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from fairlendkit.research.paper2.protocol import (
    CONFIRMATORY_REPLICATES,
    ExecutionMode,
    ProductionRunLockedError,
    load_protocol,
)
from fairlendkit.research.paper2.registry import h2_scenario_units

SHARD_SIZE = 1_000
WORKER_COUNT = 4
CPU_BUDGET = 4
MEMORY_BUDGET_GIB = 16
PROTOCOL_A1_COMMIT = "865a2baf549d691d602334379ed03a7883989d6f"
FORBIDDEN_RESULT_KEYS = frozenset(
    {"estimate", "standard_error", "se", "p_value", "holm", "figure", "plot"}
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class IntegrityError(ValueError):
    """Raised when execution artifacts fail closed validation."""


@dataclass(frozen=True)
class ExecutionManifest:
    code_commit: str
    protocol_commit: str
    protocol_manifest_sha256: str
    rng_fixture_sha256: str
    environment_lock_sha256: str
    shard_size: int = SHARD_SIZE
    worker_count: int = WORKER_COUNT
    cpu_budget: int = CPU_BUDGET
    memory_budget_gib: int = MEMORY_BUDGET_GIB
    parallel_strategy: str = "process-per-shard; deterministic shard queue"
    checkpoint_policy: str = "immutable-success-or-retry-whole-shard"

    def __post_init__(self) -> None:
        if not _COMMIT_RE.fullmatch(self.code_commit):
            raise IntegrityError("Code commit must be a full lowercase Git SHA.")
        if self.protocol_commit != PROTOCOL_A1_COMMIT:
            raise IntegrityError("Protocol/A1 commit does not match the frozen amendment.")
        for value in (
            self.protocol_manifest_sha256,
            self.rng_fixture_sha256,
            self.environment_lock_sha256,
        ):
            if not _SHA256_RE.fullmatch(value):
                raise IntegrityError("Manifest hashes must be lowercase SHA-256 values.")
        if (
            self.shard_size != SHARD_SIZE
            or self.worker_count != WORKER_COUNT
            or self.cpu_budget != CPU_BUDGET
            or self.memory_budget_gib != MEMORY_BUDGET_GIB
        ):
            raise IntegrityError("Execution resource and shard settings are frozen.")


@dataclass(frozen=True, order=True)
class ShardSpec:
    scenario_id: str
    shard_id: int
    start_replicate: int
    stop_replicate: int

    @property
    def expected_rows(self) -> int:
        return self.stop_replicate - self.start_replicate


@dataclass(frozen=True)
class RawReplicateRecord:
    scenario_id: str
    replicate_id: int
    payload: Mapping[str, object]


@dataclass(frozen=True)
class ShardMetadata:
    scenario_id: str
    shard_id: int
    start_replicate: int
    stop_replicate: int
    row_count: int
    records_sha256: str
    code_commit: str
    protocol_commit: str
    protocol_manifest_sha256: str
    rng_fixture_sha256: str
    environment_lock_sha256: str
    python_version: str
    status: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(repo_root: Path, *, code_commit: str) -> ExecutionManifest:
    protocol = load_protocol()
    fixture_sha256 = sha256_file(repo_root / "docs/fixtures/paper2-rng-a1-golden.json")
    if fixture_sha256 != protocol.rng_fixture_sha256:
        raise IntegrityError("Normative A1 fixture hash does not match the protocol manifest.")
    return ExecutionManifest(
        code_commit=code_commit,
        protocol_commit=PROTOCOL_A1_COMMIT,
        protocol_manifest_sha256=sha256_file(
            repo_root / "src/fairlendkit/research/paper2/protocol.json"
        ),
        rng_fixture_sha256=fixture_sha256,
        environment_lock_sha256=sha256_file(repo_root / "requirements-release.txt"),
    )


def confirmatory_shards(scenario_ids: Iterable[str]) -> tuple[ShardSpec, ...]:
    unique = tuple(sorted(set(scenario_ids)))
    if not unique or any(not value for value in unique):
        raise IntegrityError("At least one non-empty scenario ID is required.")
    return tuple(
        ShardSpec(scenario_id, shard_id, start, min(start + SHARD_SIZE, CONFIRMATORY_REPLICATES))
        for scenario_id in unique
        for shard_id, start in enumerate(range(0, CONFIRMATORY_REPLICATES, SHARD_SIZE))
    )


def frozen_execution_scenario_ids() -> tuple[str, ...]:
    scenario_ids = {
        "SEL-AIR080-N025",
        "SEL-AIR080-N1000",
        "PERF-DEC001",
        "PERF-DEC050",
        "SEL-AIR081-N025",
        "MISS-MCAR30",
        "MISS-MNAR30",
        "SEL-AIR081-N050",
        "SEL-AIR081-N1000",
    }
    for unreliable, reliable in h2_scenario_units():
        scenario_ids.add(unreliable)
        scenario_ids.update(reliable)
    return tuple(sorted(scenario_ids))


def frozen_confirmatory_shards() -> tuple[ShardSpec, ...]:
    return confirmatory_shards(frozen_execution_scenario_ids())


def smoke_shards(scenario_id: str, *, replicates: int = 6, shard_size: int = 2) -> tuple[ShardSpec, ...]:
    load_protocol().authorize(ExecutionMode.SMOKE, tuple(range(replicates)))
    if shard_size <= 0 or replicates % shard_size:
        raise IntegrityError("Smoke shard size must divide the replicate count.")
    return tuple(
        ShardSpec(scenario_id, shard_id, start, start + shard_size)
        for shard_id, start in enumerate(range(0, replicates, shard_size))
    )


def _paths(output_dir: Path, spec: ShardSpec) -> tuple[Path, Path]:
    stem = f"{spec.scenario_id}--{spec.shard_id:05d}"
    return output_dir / f"{stem}.jsonl", output_dir / f"{stem}.meta.json"


def _canonical_record(record: RawReplicateRecord) -> bytes:
    forbidden = FORBIDDEN_RESULT_KEYS.intersection(record.payload)
    if forbidden:
        raise IntegrityError(f"Derived-result fields are forbidden: {sorted(forbidden)}")
    return (json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_smoke_shard(
    output_dir: Path,
    manifest: ExecutionManifest,
    spec: ShardSpec,
    records: Iterable[RawReplicateRecord],
) -> ShardMetadata:
    if spec.stop_replicate > 100:
        raise ProductionRunLockedError("Only isolated smoke replicate IDs may be written.")
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path, metadata_path = _paths(output_dir, spec)
    if records_path.exists() and metadata_path.exists():
        return validate_shard(output_dir, manifest, spec)
    if records_path.exists() != metadata_path.exists():
        orphan = records_path if records_path.exists() else metadata_path
        orphan.unlink()

    records_tmp = records_path.with_suffix(records_path.suffix + ".tmp")
    metadata_tmp = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
    records_tmp.unlink(missing_ok=True)
    metadata_tmp.unlink(missing_ok=True)

    ordered = tuple(records)
    expected_ids = tuple(range(spec.start_replicate, spec.stop_replicate))
    if tuple(record.replicate_id for record in ordered) != expected_ids:
        raise IntegrityError("Shard records must cover the exact ordered replicate range.")
    if any(record.scenario_id != spec.scenario_id for record in ordered):
        raise IntegrityError("Shard record scenario does not match its specification.")
    payload = b"".join(_canonical_record(record) for record in ordered)
    records_tmp.write_bytes(payload)
    metadata = ShardMetadata(
        scenario_id=spec.scenario_id,
        shard_id=spec.shard_id,
        start_replicate=spec.start_replicate,
        stop_replicate=spec.stop_replicate,
        row_count=len(ordered),
        records_sha256=hashlib.sha256(payload).hexdigest(),
        code_commit=manifest.code_commit,
        protocol_commit=manifest.protocol_commit,
        protocol_manifest_sha256=manifest.protocol_manifest_sha256,
        rng_fixture_sha256=manifest.rng_fixture_sha256,
        environment_lock_sha256=manifest.environment_lock_sha256,
        python_version=platform.python_version(),
        status="success",
    )
    metadata_tmp.write_text(
        json.dumps(asdict(metadata), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    records_tmp.replace(records_path)
    metadata_tmp.replace(metadata_path)
    return metadata


def validate_shard(
    output_dir: Path, manifest: ExecutionManifest, spec: ShardSpec
) -> ShardMetadata:
    records_path, metadata_path = _paths(output_dir, spec)
    if not records_path.is_file() or not metadata_path.is_file():
        raise IntegrityError("Shard records or metadata are missing.")
    try:
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = ShardMetadata(**raw_metadata)
    except (json.JSONDecodeError, TypeError) as error:
        raise IntegrityError("Shard metadata is invalid.") from error
    expected = {
        "scenario_id": spec.scenario_id,
        "shard_id": spec.shard_id,
        "start_replicate": spec.start_replicate,
        "stop_replicate": spec.stop_replicate,
        "row_count": spec.expected_rows,
        "code_commit": manifest.code_commit,
        "protocol_commit": manifest.protocol_commit,
        "protocol_manifest_sha256": manifest.protocol_manifest_sha256,
        "rng_fixture_sha256": manifest.rng_fixture_sha256,
        "environment_lock_sha256": manifest.environment_lock_sha256,
        "python_version": platform.python_version(),
        "status": "success",
    }
    for field, value in expected.items():
        if getattr(metadata, field) != value:
            raise IntegrityError(f"Shard metadata mismatch: {field}.")
    payload = records_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata.records_sha256:
        raise IntegrityError("Shard records hash mismatch.")
    lines = payload.splitlines()
    if len(lines) != spec.expected_rows:
        raise IntegrityError("Shard row count does not match its range.")
    seen: list[int] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise IntegrityError("Shard record JSON is invalid.") from error
        if set(record) != {"scenario_id", "replicate_id", "payload"}:
            raise IntegrityError("Shard record fields are invalid.")
        if record["scenario_id"] != spec.scenario_id:
            raise IntegrityError("Shard record scenario mismatch.")
        if FORBIDDEN_RESULT_KEYS.intersection(record["payload"]):
            raise IntegrityError("Shard contains a forbidden derived result.")
        seen.append(record["replicate_id"])
    if seen != list(range(spec.start_replicate, spec.stop_replicate)):
        raise IntegrityError("Shard has duplicate, missing, or out-of-order replicate IDs.")
    return metadata


def validate_complete_set(
    output_dir: Path,
    manifest: ExecutionManifest,
    expected_specs: Iterable[ShardSpec],
) -> tuple[ShardMetadata, ...]:
    specs = tuple(expected_specs)
    if len(specs) != len(set(specs)):
        raise IntegrityError("Expected shard plan contains duplicates.")
    metadata = tuple(validate_shard(output_dir, manifest, spec) for spec in specs)
    expected_files = {
        path.name for spec in specs for path in _paths(output_dir, spec)
    }
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise IntegrityError("Output directory has missing or unexpected shard artifacts.")
    return metadata


def validate_confirmatory_complete_set(
    output_dir: Path, manifest: ExecutionManifest
) -> tuple[ShardMetadata, ...]:
    """Validate the entire frozen matrix without calculating any result."""
    return validate_complete_set(output_dir, manifest, frozen_confirmatory_shards())
