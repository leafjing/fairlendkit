"""Smoke-only contract tests for the Paper 2 confirmatory execution gate."""

import json
import hashlib
from dataclasses import asdict
from dataclasses import replace
from pathlib import Path

import pytest

import fairlendkit.research.paper2.execution as execution
from fairlendkit.research.paper2.execution import (
    ExecutionWorkspace,
    IntegrityError,
    RawReplicatePayload,
    RawReplicateRecord,
    ResourceCapacity,
    ShardSpec,
    build_manifest,
    benchmark_smoke_resources,
    frozen_confirmatory_shards,
    frozen_execution_scenario_ids,
    smoke_shards,
    validate_complete_set,
    validate_execution_seal,
    validate_resource_preflight,
    validate_shard,
    write_smoke_shard,
)
from fairlendkit.research.paper2.protocol import ProductionRunLockedError


REPO_ROOT = Path(__file__).parents[1]
CODE_COMMIT = "1" * 40


@pytest.fixture
def manifest(monkeypatch):
    environment = (REPO_ROOT / "docs/milestone-3-release-pip-freeze.txt").read_bytes()
    monkeypatch.setattr(execution, "_git_identity", lambda _: (CODE_COMMIT, False))
    monkeypatch.setattr(execution, "_git_has_frozen_base", lambda _: True)
    monkeypatch.setattr(execution, "_installed_environment", lambda: environment)
    return build_manifest(REPO_ROOT)


@pytest.fixture
def workspace(tmp_path):
    return ExecutionWorkspace(tmp_path.resolve(), "smoke")


def _payload(value: float = 0.0):
    key = "overall.selection_rate"
    return RawReplicatePayload(
        schema_version="paper2-raw-replicate-v1",
        metric_values=((key, value),),
        metric_defined=((key, True),),
        reliability=((key, "reliable"),),
        uncertainty=((key, (value, value)),),
        flags=(),
        limitations=(),
    )


def _records(spec):
    return tuple(
        RawReplicateRecord(
            scenario_id=spec.scenario_id,
            replicate_id=replicate_id,
            payload=_payload(float(replicate_id)),
        )
        for replicate_id in range(spec.start_replicate, spec.stop_replicate)
    )


def test_frozen_plan_has_exact_ranges_without_overlap_or_gaps():
    scenario_ids = frozen_execution_scenario_ids()
    specs = frozen_confirmatory_shards()

    assert len(scenario_ids) == 29
    assert len(specs) == len(scenario_ids) * 50
    for scenario_id in scenario_ids:
        ranges = [
            (spec.start_replicate, spec.stop_replicate)
            for spec in specs
            if spec.scenario_id == scenario_id
        ]
        assert ranges == [(start, start + 1_000) for start in range(0, 50_000, 1_000)]


def test_smoke_resume_is_idempotent_and_recovers_interrupted_artifact(
    workspace, manifest
):
    spec = smoke_shards("SEL-AIR081-N025", replicates=2, shard_size=2)[0]
    first = write_smoke_shard(workspace, manifest, spec, _records(spec))
    second = write_smoke_shard(workspace, manifest, spec, _records(spec))
    assert first == second

    records_path = workspace.output_dir / "SEL-AIR081-N025--00000.jsonl"
    metadata_path = workspace.output_dir / "SEL-AIR081-N025--00000.meta.json"
    metadata_path.unlink()
    records_path.write_bytes(b"interrupted")
    recovered = write_smoke_shard(workspace, manifest, spec, _records(spec))
    assert recovered == first
    assert validate_shard(workspace, manifest, spec) == first


def test_complete_set_fails_closed_for_missing_duplicate_and_tampered_shards(
    workspace, manifest
):
    specs = smoke_shards("SEL-AIR081-N025")
    for spec in specs:
        write_smoke_shard(workspace, manifest, spec, _records(spec))
    assert len(validate_complete_set(workspace, manifest, specs)) == 3

    with pytest.raises(IntegrityError, match="duplicates"):
        validate_complete_set(workspace, manifest, (*specs, specs[0]))

    missing_path = workspace.output_dir / "SEL-AIR081-N025--00001.meta.json"
    original_metadata = missing_path.read_bytes()
    missing_path.unlink()
    with pytest.raises(IntegrityError, match="missing"):
        validate_complete_set(workspace, manifest, specs)
    missing_path.write_bytes(original_metadata)

    records_path = workspace.output_dir / "SEL-AIR081-N025--00002.jsonl"
    original_records = records_path.read_bytes()
    records_path.write_bytes(original_records + b"tampered\n")
    with pytest.raises(IntegrityError, match="hash"):
        validate_complete_set(workspace, manifest, specs)


def test_metadata_identity_and_forbidden_derived_results_fail_closed(
    workspace, manifest
):
    spec = smoke_shards("REG", replicates=2, shard_size=2)[0]
    with pytest.raises(TypeError):
        RawReplicatePayload(
            schema_version="paper2-raw-replicate-v1",
            metric_values=(("overall.selection_rate", 0.5),),
            metric_defined=(("overall.selection_rate", True),),
            reliability=(("overall.selection_rate", "reliable"),),
            uncertainty=(("overall.selection_rate", None),),
            flags=(),
            limitations=(),
            p_value=0.01,
        )
    with pytest.raises(IntegrityError, match="frozen raw-record"):
        write_smoke_shard(
            workspace,
            manifest,
            spec,
            (
                RawReplicateRecord("REG", 0, {"p_value": 0.01}),
                RawReplicateRecord("REG", 1, {"raw_value": 1}),
            ),
        )

    write_smoke_shard(workspace, manifest, spec, _records(spec))
    with pytest.raises(IntegrityError, match="code_commit"):
        validate_shard(workspace, replace(manifest, code_commit="2" * 40), spec)


def test_writer_cannot_accept_confirmatory_replicate_range(workspace, manifest):
    spec = frozen_confirmatory_shards()[0]
    assert spec.stop_replicate == 1_000
    with pytest.raises(ProductionRunLockedError):
        write_smoke_shard(workspace, manifest, spec, ())


def test_metadata_schema_is_raw_and_contains_environment_evidence(workspace, manifest):
    spec = smoke_shards("REG", replicates=2, shard_size=2)[0]
    write_smoke_shard(workspace, manifest, spec, _records(spec))
    metadata = json.loads((workspace.output_dir / "REG--00000.meta.json").read_text())

    assert metadata["row_count"] == 2
    assert metadata["start_replicate"] == 0
    assert metadata["stop_replicate"] == 2
    assert metadata["status"] == "success"
    assert metadata["python_version"]
    assert metadata["records_sha256"]
    assert metadata["environment_lock_sha256"] == manifest.environment_lock_sha256
    assert metadata["pip_freeze_sha256"] == manifest.pip_freeze_sha256
    assert metadata["python_executable_sha256"] == manifest.python_executable_sha256


def test_manifest_requires_real_clean_head_environment_and_frozen_strategies(
    monkeypatch,
):
    environment = (REPO_ROOT / "docs/milestone-3-release-pip-freeze.txt").read_bytes()
    monkeypatch.setattr(execution, "_installed_environment", lambda: environment)
    monkeypatch.setattr(execution, "_git_has_frozen_base", lambda _: True)
    monkeypatch.setattr(execution, "_git_identity", lambda _: (CODE_COMMIT, True))
    with pytest.raises(IntegrityError, match="clean"):
        build_manifest(REPO_ROOT)

    monkeypatch.setattr(execution, "_git_identity", lambda _: (CODE_COMMIT, False))
    built = build_manifest(REPO_ROOT)
    assert built.code_commit == CODE_COMMIT
    with pytest.raises(IntegrityError, match="frozen"):
        replace(built, parallel_strategy="dynamic")
    with pytest.raises(IntegrityError, match="frozen"):
        replace(built, checkpoint_policy="partial")

    monkeypatch.setattr(execution, "_git_has_frozen_base", lambda _: False)
    with pytest.raises(IntegrityError, match="approved phase-one"):
        build_manifest(REPO_ROOT)

    monkeypatch.setattr(execution, "_git_has_frozen_base", lambda _: True)
    monkeypatch.setattr(execution, "_installed_environment", lambda: b"not-the-lock\n")
    with pytest.raises(IntegrityError, match="pip lock"):
        build_manifest(REPO_ROOT)


@pytest.mark.parametrize(
    "spec",
    (
        ("confirmatory", "../REG", 0, 0, 1_000),
        ("confirmatory", "REG", -1, -1_000, 0),
        ("confirmatory", "REG", 0, 1, 1_001),
        ("confirmatory", "REG", 50, 50_000, 51_000),
        ("smoke", "REG", 0, 0, 101),
        ("smoke", "UNKNOWN", 0, 0, 2),
    ),
)
def test_invalid_shard_boundaries_and_paths_fail_closed(spec):
    with pytest.raises(IntegrityError):
        ShardSpec(*spec)


@pytest.mark.parametrize("value", (True, 0.0, 1.0))
def test_shard_identity_requires_exact_integers(value):
    with pytest.raises(IntegrityError, match="exact integers"):
        ShardSpec("smoke", "REG", value, 0, 2)


def test_workspace_rejects_relative_root_namespace_mismatch_and_symlink_escape(
    tmp_path, manifest
):
    with pytest.raises(IntegrityError, match="absolute resolved"):
        ExecutionWorkspace(Path("relative"), "smoke")

    workspace = ExecutionWorkspace(tmp_path.resolve(), "smoke")
    confirmatory = frozen_confirmatory_shards()[0]
    with pytest.raises(ProductionRunLockedError):
        write_smoke_shard(workspace, manifest, confirmatory, ())

    target = tmp_path / "outside"
    target.mkdir()
    workspace.output_dir.symlink_to(target, target_is_directory=True)
    with pytest.raises(IntegrityError, match="symlink"):
        _ = workspace.output_dir


def test_raw_schema_is_versioned_recursive_and_rejects_unknown_or_nonfinite_values():
    with pytest.raises(IntegrityError, match="schema version"):
        replace(_payload(), schema_version="paper2-raw-replicate-v2")
    with pytest.raises(IntegrityError, match="finite"):
        replace(_payload(), metric_values=(("overall.selection_rate", float("nan")),))

    raw = json.loads(execution._canonical_record(RawReplicateRecord("REG", 0, _payload())))
    raw["payload"]["metric_values"][0].append({"p_value": 0.01})
    with pytest.raises(IntegrityError, match="invalid"):
        execution._validate_raw_payload(raw["payload"])


def test_metric_key_grammar_and_state_associations_fail_closed():
    with pytest.raises(IntegrityError, match="unknown metric key"):
        replace(_payload(), metric_values=(("evil.selection_rate", 0.5),),
                metric_defined=(("evil.selection_rate", True),),
                reliability=(("evil.selection_rate", "reliable"),),
                uncertainty=(("evil.selection_rate", None),))
    with pytest.raises(IntegrityError, match="inconsistent state"):
        replace(_payload(), metric_defined=(("overall.selection_rate", False),))
    with pytest.raises(IntegrityError, match="not eligible"):
        replace(_payload(), reliability=(("overall.selection_rate", "unreliable"),))
    with pytest.raises(IntegrityError, match="flag association"):
        replace(_payload(), flags=(("air_below_threshold", "overall.selection_rate"),))


def test_final_and_temporary_artifact_symlinks_fail_closed(tmp_path, manifest):
    workspace = ExecutionWorkspace(tmp_path.resolve(), "smoke")
    spec = smoke_shards("REG", replicates=2, shard_size=2)[0]
    workspace.output_dir.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    records_path = workspace.output_dir / "REG--00000.jsonl"
    records_path.symlink_to(outside)
    with pytest.raises(IntegrityError, match="symlink"):
        write_smoke_shard(workspace, manifest, spec, _records(spec))
    records_path.unlink()
    temp_path = workspace.output_dir / "REG--00000.jsonl.tmp"
    temp_path.symlink_to(outside)
    with pytest.raises(IntegrityError, match="symlink"):
        write_smoke_shard(workspace, manifest, spec, _records(spec))


def test_external_execution_seal_binds_bytes_and_runtime_identity(tmp_path, manifest):
    seal = {
        "schema_version": "paper2-execution-seal-v1",
        "code_commit": manifest.code_commit,
        "protocol_commit": manifest.protocol_commit,
        "manifest_sha256": execution.manifest_sha256(manifest),
        "shard_plan_sha256": execution.shard_plan_sha256(),
        "protocol_manifest_sha256": manifest.protocol_manifest_sha256,
        "rng_fixture_sha256": manifest.rng_fixture_sha256,
        "environment_lock_sha256": manifest.environment_lock_sha256,
    }
    seal_path = tmp_path / "execution-seal.json"
    seal_bytes = (json.dumps(seal, sort_keys=True, separators=(",", ":")) + "\n").encode()
    seal_path.write_bytes(seal_bytes)
    seal_hash = hashlib.sha256(seal_bytes).hexdigest()
    assert validate_execution_seal(seal_path, seal_hash, manifest).code_commit == CODE_COMMIT
    with pytest.raises(IntegrityError, match="external seal hash"):
        validate_execution_seal(seal_path, "0" * 64, manifest)
    seal["code_commit"] = "2" * 40
    modified = (json.dumps(seal, sort_keys=True, separators=(",", ":")) + "\n").encode()
    seal_path.write_bytes(modified)
    with pytest.raises(IntegrityError, match="runtime identity"):
        validate_execution_seal(seal_path, hashlib.sha256(modified).hexdigest(), manifest)
    raw = json.loads(execution._canonical_record(RawReplicateRecord("REG", 0, _payload())))
    raw["payload"]["nested_result"] = {"p_value": 0.01}
    with pytest.raises(IntegrityError, match="frozen raw-record"):
        execution._validate_raw_payload(raw["payload"])


def test_complete_set_rejects_reused_identity_or_range(workspace, manifest):
    reused_identity = (
        ShardSpec("smoke", "REG", 0, 0, 2),
        ShardSpec("smoke", "REG", 0, 2, 4),
    )
    with pytest.raises(IntegrityError, match="identities or ranges overlap"):
        validate_complete_set(workspace, manifest, reused_identity)

    reused_range = (
        ShardSpec("smoke", "REG", 0, 0, 2),
        ShardSpec("smoke", "REG", 1, 0, 2),
    )
    with pytest.raises(IntegrityError, match="identities or ranges overlap"):
        validate_complete_set(workspace, manifest, reused_range)


def test_smoke_benchmark_is_raw_only_and_resource_preflight_fails_closed(
    workspace, manifest
):
    evidence = benchmark_smoke_resources(workspace, manifest)

    assert evidence.schema_version == "paper2-resource-benchmark-v1"
    assert evidence.smoke_records == 100
    assert evidence.projected_records == 29 * 50_000
    assert evidence.safety_factor == 2.0
    assert evidence.projected_cpu_hours > 0
    assert evidence.projected_wall_hours > 0
    assert evidence.projected_disk_bytes > 0
    assert not any(
        forbidden in path.name.lower()
        for path in workspace.output_dir.iterdir()
        for forbidden in ("estimate", "p-value", "holm", "plot", "figure")
    )

    sufficient = ResourceCapacity(
        cpu_count=4,
        memory_bytes=evidence.required_memory_bytes,
        disk_free_bytes=evidence.projected_disk_bytes,
    )
    validate_resource_preflight(sufficient, evidence)
    with pytest.raises(IntegrityError, match="CPU"):
        validate_resource_preflight(replace(sufficient, cpu_count=3), evidence)
    with pytest.raises(IntegrityError, match="memory"):
        validate_resource_preflight(
            replace(sufficient, memory_bytes=evidence.required_memory_bytes - 1), evidence
        )
    with pytest.raises(IntegrityError, match="disk"):
        validate_resource_preflight(
            replace(sufficient, disk_free_bytes=evidence.projected_disk_bytes - 1), evidence
        )
