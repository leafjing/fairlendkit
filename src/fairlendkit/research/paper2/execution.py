"""Paper 2 execution-gate primitives; confirmatory execution remains locked."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Iterable

from fairlendkit.metrics.contracts import LimitationCode, MetricNameV2

from fairlendkit.research.paper2.protocol import (
    CONFIRMATORY_REPLICATES,
    ExecutionMode,
    ProductionRunLockedError,
    load_protocol,
)
from fairlendkit.research.paper2.registry import h2_scenario_units, scenario_registry

SHARD_SIZE = 1_000
WORKER_COUNT = 4
CPU_BUDGET = 4
MEMORY_BUDGET_GIB = 16
PROTOCOL_A1_COMMIT = "865a2baf549d691d602334379ed03a7883989d6f"
IMPLEMENTATION_BASE_COMMIT = "1143d0e5795eefa1abb3de4bf52fdc9eaf8f9b91"
PARALLEL_STRATEGY = "process-per-shard; deterministic shard queue"
CHECKPOINT_POLICY = "immutable-success-or-retry-whole-shard"
RELIABILITY_STATES = frozenset(
    {"reliable", "unreliable", "undefined", "not_applicable"}
)
FLAG_CODES = frozenset({"air_below_threshold"})
LIMITATION_CODES = frozenset(code.value for code in LimitationCode)
METRIC_NAMES = tuple(metric.value for metric in MetricNameV2)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class IntegrityError(ValueError):
    """Raised when execution artifacts fail closed validation."""


@dataclass(frozen=True)
class ExecutionManifest:
    code_commit: str
    implementation_base_commit: str
    protocol_commit: str
    protocol_manifest_sha256: str
    rng_fixture_sha256: str
    environment_lock_sha256: str
    pip_freeze_sha256: str
    python_executable_sha256: str
    python_version: str
    shard_size: int = SHARD_SIZE
    worker_count: int = WORKER_COUNT
    cpu_budget: int = CPU_BUDGET
    memory_budget_gib: int = MEMORY_BUDGET_GIB
    parallel_strategy: str = PARALLEL_STRATEGY
    checkpoint_policy: str = CHECKPOINT_POLICY

    def __post_init__(self) -> None:
        if not _COMMIT_RE.fullmatch(self.code_commit):
            raise IntegrityError("Code commit must be a full lowercase Git SHA.")
        if self.implementation_base_commit != IMPLEMENTATION_BASE_COMMIT:
            raise IntegrityError("Implementation base commit is not frozen.")
        if self.protocol_commit != PROTOCOL_A1_COMMIT:
            raise IntegrityError("Protocol/A1 commit does not match the frozen amendment.")
        for value in (
            self.protocol_manifest_sha256,
            self.rng_fixture_sha256,
            self.environment_lock_sha256,
            self.pip_freeze_sha256,
            self.python_executable_sha256,
        ):
            if not _SHA256_RE.fullmatch(value):
                raise IntegrityError("Manifest hashes must be lowercase SHA-256 values.")
        if (
            self.shard_size != SHARD_SIZE
            or self.worker_count != WORKER_COUNT
            or self.cpu_budget != CPU_BUDGET
            or self.memory_budget_gib != MEMORY_BUDGET_GIB
            or self.parallel_strategy != PARALLEL_STRATEGY
            or self.checkpoint_policy != CHECKPOINT_POLICY
        ):
            raise IntegrityError("Execution resource and shard settings are frozen.")


@dataclass(frozen=True, order=True)
class ShardSpec:
    namespace: str
    scenario_id: str
    shard_id: int
    start_replicate: int
    stop_replicate: int

    def __post_init__(self) -> None:
        if self.namespace not in {"confirmatory", "smoke"}:
            raise IntegrityError("Shard namespace must be confirmatory or smoke.")
        if not re.fullmatch(r"[A-Z0-9-]+", self.scenario_id):
            raise IntegrityError("Scenario ID is not path-safe.")
        allowed_scenarios = (
            frozen_execution_scenario_ids()
            if self.namespace == "confirmatory"
            else tuple(scenario_registry())
        )
        if self.scenario_id not in allowed_scenarios:
            raise IntegrityError("Shard scenario is not registered for its namespace.")
        if self.shard_id < 0 or self.start_replicate < 0:
            raise IntegrityError("Shard IDs and ranges cannot be negative.")
        if self.stop_replicate <= self.start_replicate:
            raise IntegrityError("Shard range must be non-empty and increasing.")
        if self.namespace == "confirmatory":
            if (
                self.shard_id >= CONFIRMATORY_REPLICATES // SHARD_SIZE
                or self.start_replicate != self.shard_id * SHARD_SIZE
                or self.stop_replicate != self.start_replicate + SHARD_SIZE
                or self.stop_replicate > CONFIRMATORY_REPLICATES
            ):
                raise IntegrityError("Confirmatory shard boundaries are frozen.")
        elif self.stop_replicate > 100:
            raise IntegrityError("Smoke shard range must remain within 0..99.")

    @property
    def expected_rows(self) -> int:
        return self.stop_replicate - self.start_replicate


@dataclass(frozen=True)
class RawReplicateRecord:
    scenario_id: str
    replicate_id: int
    payload: "RawReplicatePayload"


@dataclass(frozen=True)
class RawReplicatePayload:
    schema_version: str
    metric_values: tuple[tuple[str, float | None], ...]
    metric_defined: tuple[tuple[str, bool], ...]
    reliability: tuple[tuple[str, str], ...]
    uncertainty: tuple[tuple[str, tuple[float, float] | None], ...]
    flags: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "paper2-raw-replicate-v1":
            raise IntegrityError("Raw payload schema version is not frozen.")
        keyed = (self.metric_values, self.metric_defined, self.reliability, self.uncertainty)
        key_sets: list[tuple[str, ...]] = []
        for entries in keyed:
            keys = tuple(key for key, _ in entries)
            if keys != tuple(sorted(set(keys))):
                raise IntegrityError("Raw metric keys must be unique and canonically sorted.")
            if any(not any(key.endswith(f".{metric}") for metric in METRIC_NAMES) for key in keys):
                raise IntegrityError("Raw payload contains an unknown metric key.")
            key_sets.append(keys)
        if len(set(key_sets)) != 1:
            raise IntegrityError("Raw payload metric sections must use identical keys.")
        if any(
            value is not None
            and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            )
            for _, value in self.metric_values
        ):
            raise IntegrityError("Raw metric values must be finite or None.")
        if any(not isinstance(value, bool) for _, value in self.metric_defined):
            raise IntegrityError("Raw definedness values must be booleans.")
        if any(value not in RELIABILITY_STATES for _, value in self.reliability):
            raise IntegrityError("Raw reliability state is invalid.")
        for _, interval in self.uncertainty:
            if interval is not None and (
                len(interval) != 2
                or not all(isfinite(value) for value in interval)
                or interval[0] > interval[1]
            ):
                raise IntegrityError("Raw uncertainty interval is invalid.")
        if tuple(sorted(set(self.flags))) != self.flags or not set(self.flags) <= FLAG_CODES:
            raise IntegrityError("Raw flags must be unique, sorted, and registered.")
        if (
            tuple(sorted(set(self.limitations))) != self.limitations
            or not set(self.limitations) <= LIMITATION_CODES
        ):
            raise IntegrityError("Raw limitations must be unique, sorted, and registered.")


@dataclass(frozen=True)
class ShardMetadata:
    scenario_id: str
    shard_id: int
    start_replicate: int
    stop_replicate: int
    row_count: int
    records_sha256: str
    code_commit: str
    implementation_base_commit: str
    protocol_commit: str
    protocol_manifest_sha256: str
    rng_fixture_sha256: str
    environment_lock_sha256: str
    pip_freeze_sha256: str
    python_executable_sha256: str
    python_version: str
    status: str


@dataclass(frozen=True)
class ExecutionWorkspace:
    root: Path
    namespace: str

    def __post_init__(self) -> None:
        if self.namespace not in {"confirmatory", "smoke"}:
            raise IntegrityError("Workspace namespace is invalid.")
        if not self.root.is_absolute() or self.root != self.root.resolve():
            raise IntegrityError("Workspace root must be an absolute resolved path.")
        if self.root.is_symlink():
            raise IntegrityError("Workspace root cannot be a symlink.")

    @property
    def output_dir(self) -> Path:
        name = (
            "paper2-confirmatory-raw-v1"
            if self.namespace == "confirmatory"
            else "paper2-smoke-raw-v1"
        )
        candidate = self.root / name
        if candidate.exists() and candidate.is_symlink():
            raise IntegrityError("Workspace output cannot be a symlink.")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise IntegrityError("Workspace output escapes its fixed root.")
        return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_identity(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def _git_has_frozen_base(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", IMPLEMENTATION_BASE_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _installed_environment() -> bytes:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
    )
    lines = result.stdout.decode("utf-8").splitlines()
    normalized = (
        "fairlendkit==0.1.0.dev0" if line.startswith("fairlendkit @ ") else line
        for line in lines
    )
    return ("\n".join(normalized) + "\n").encode("utf-8")


def build_manifest(repo_root: Path) -> ExecutionManifest:
    protocol = load_protocol()
    code_commit, dirty = _git_identity(repo_root)
    if dirty:
        raise IntegrityError("Execution manifest requires a clean Git worktree.")
    if not _git_has_frozen_base(repo_root):
        raise IntegrityError("Execution code is not based on the approved phase-one merge.")
    fixture_sha256 = sha256_file(repo_root / "docs/fixtures/paper2-rng-a1-golden.json")
    if fixture_sha256 != protocol.rng_fixture_sha256:
        raise IntegrityError("Normative A1 fixture hash does not match the protocol manifest.")
    expected_environment = (repo_root / "docs/milestone-3-release-pip-freeze.txt").read_bytes()
    actual_environment = _installed_environment()
    if actual_environment != expected_environment:
        raise IntegrityError("Installed environment does not match the frozen pip lock.")
    return ExecutionManifest(
        code_commit=code_commit,
        implementation_base_commit=IMPLEMENTATION_BASE_COMMIT,
        protocol_commit=PROTOCOL_A1_COMMIT,
        protocol_manifest_sha256=sha256_file(
            repo_root / "src/fairlendkit/research/paper2/protocol.json"
        ),
        rng_fixture_sha256=fixture_sha256,
        environment_lock_sha256=sha256_file(repo_root / "requirements-release.txt"),
        pip_freeze_sha256=hashlib.sha256(actual_environment).hexdigest(),
        python_executable_sha256=sha256_file(Path(sys.executable).resolve()),
        python_version=platform.python_version(),
    )


def confirmatory_shards(scenario_ids: Iterable[str]) -> tuple[ShardSpec, ...]:
    unique = tuple(sorted(set(scenario_ids)))
    if not unique or any(not value for value in unique):
        raise IntegrityError("At least one non-empty scenario ID is required.")
    return tuple(
        ShardSpec(
            "confirmatory",
            scenario_id,
            shard_id,
            start,
            min(start + SHARD_SIZE, CONFIRMATORY_REPLICATES),
        )
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
        ShardSpec("smoke", scenario_id, shard_id, start, start + shard_size)
        for shard_id, start in enumerate(range(0, replicates, shard_size))
    )


def _paths(workspace: ExecutionWorkspace, spec: ShardSpec) -> tuple[Path, Path]:
    if workspace.namespace != spec.namespace:
        raise IntegrityError("Shard namespace does not match its workspace.")
    output_dir = workspace.output_dir
    stem = f"{spec.scenario_id}--{spec.shard_id:05d}"
    return output_dir / f"{stem}.jsonl", output_dir / f"{stem}.meta.json"


def _canonical_record(record: RawReplicateRecord) -> bytes:
    if not isinstance(record.payload, RawReplicatePayload):
        raise IntegrityError("Record payload must use the frozen raw-record schema.")
    return (json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _validate_raw_payload(raw: object) -> None:
    if not isinstance(raw, dict) or set(raw) != {
        "metric_values",
        "metric_defined",
        "reliability",
        "uncertainty",
        "flags",
        "limitations",
        "schema_version",
    }:
        raise IntegrityError("Shard payload does not match the frozen raw-record schema.")
    try:
        RawReplicatePayload(
            schema_version=raw["schema_version"],
            metric_values=tuple((key, value) for key, value in raw["metric_values"]),
            metric_defined=tuple((key, value) for key, value in raw["metric_defined"]),
            reliability=tuple((key, value) for key, value in raw["reliability"]),
            uncertainty=tuple(
                (key, None if value is None else tuple(value))
                for key, value in raw["uncertainty"]
            ),
            flags=tuple(raw["flags"]),
            limitations=tuple(raw["limitations"]),
        )
    except (TypeError, ValueError) as error:
        raise IntegrityError("Shard raw-record payload is invalid.") from error


def write_smoke_shard(
    workspace: ExecutionWorkspace,
    manifest: ExecutionManifest,
    spec: ShardSpec,
    records: Iterable[RawReplicateRecord],
) -> ShardMetadata:
    if spec.namespace != "smoke":
        raise ProductionRunLockedError("Only isolated smoke replicate IDs may be written.")
    output_dir = workspace.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path, metadata_path = _paths(workspace, spec)
    if records_path.exists() and metadata_path.exists():
        return validate_shard(workspace, manifest, spec)
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
        implementation_base_commit=manifest.implementation_base_commit,
        protocol_commit=manifest.protocol_commit,
        protocol_manifest_sha256=manifest.protocol_manifest_sha256,
        rng_fixture_sha256=manifest.rng_fixture_sha256,
        environment_lock_sha256=manifest.environment_lock_sha256,
        pip_freeze_sha256=manifest.pip_freeze_sha256,
        python_executable_sha256=manifest.python_executable_sha256,
        python_version=manifest.python_version,
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
    workspace: ExecutionWorkspace, manifest: ExecutionManifest, spec: ShardSpec
) -> ShardMetadata:
    records_path, metadata_path = _paths(workspace, spec)
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
        "implementation_base_commit": manifest.implementation_base_commit,
        "protocol_commit": manifest.protocol_commit,
        "protocol_manifest_sha256": manifest.protocol_manifest_sha256,
        "rng_fixture_sha256": manifest.rng_fixture_sha256,
        "environment_lock_sha256": manifest.environment_lock_sha256,
        "pip_freeze_sha256": manifest.pip_freeze_sha256,
        "python_executable_sha256": manifest.python_executable_sha256,
        "python_version": manifest.python_version,
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
        _validate_raw_payload(record["payload"])
        seen.append(record["replicate_id"])
    if seen != list(range(spec.start_replicate, spec.stop_replicate)):
        raise IntegrityError("Shard has duplicate, missing, or out-of-order replicate IDs.")
    return metadata


def validate_complete_set(
    workspace: ExecutionWorkspace,
    manifest: ExecutionManifest,
    expected_specs: Iterable[ShardSpec],
) -> tuple[ShardMetadata, ...]:
    specs = tuple(expected_specs)
    if len(specs) != len(set(specs)):
        raise IntegrityError("Expected shard plan contains duplicates.")
    identities = {(spec.namespace, spec.scenario_id, spec.shard_id) for spec in specs}
    ranges = {
        (spec.namespace, spec.scenario_id, spec.start_replicate, spec.stop_replicate)
        for spec in specs
    }
    if len(identities) != len(specs) or len(ranges) != len(specs):
        raise IntegrityError("Expected shard identities or ranges overlap.")
    metadata = tuple(validate_shard(workspace, manifest, spec) for spec in specs)
    expected_files = {
        path.name for spec in specs for path in _paths(workspace, spec)
    }
    output_dir = workspace.output_dir
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise IntegrityError("Output directory has missing or unexpected shard artifacts.")
    return metadata


def validate_confirmatory_complete_set(
    workspace: ExecutionWorkspace, manifest: ExecutionManifest
) -> tuple[ShardMetadata, ...]:
    """Validate the entire frozen matrix without calculating any result."""
    if workspace.namespace != "confirmatory":
        raise IntegrityError("Confirmatory validation requires its fixed workspace.")
    return validate_complete_set(workspace, manifest, frozen_confirmatory_shards())
