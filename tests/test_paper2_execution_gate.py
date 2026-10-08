"""Smoke-only contract tests for the Paper 2 confirmatory execution gate."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

import fairlendkit.research.paper2.execution as execution
from fairlendkit.research.paper2.execution import (
    IntegrityError,
    RawReplicatePayload,
    RawReplicateRecord,
    ShardSpec,
    build_manifest,
    frozen_confirmatory_shards,
    frozen_execution_scenario_ids,
    smoke_shards,
    validate_complete_set,
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


def _payload(value: float = 0.0):
    key = "overall.selection_rate"
    return RawReplicatePayload(
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


def test_smoke_resume_is_idempotent_and_recovers_interrupted_artifact(tmp_path, manifest):
    spec = smoke_shards("SEL-AIR081-N025", replicates=2, shard_size=2)[0]
    first = write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    second = write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    assert first == second

    records_path = tmp_path / "SEL-AIR081-N025--00000.jsonl"
    metadata_path = tmp_path / "SEL-AIR081-N025--00000.meta.json"
    metadata_path.unlink()
    records_path.write_bytes(b"interrupted")
    recovered = write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    assert recovered == first
    assert validate_shard(tmp_path, manifest, spec) == first


def test_complete_set_fails_closed_for_missing_duplicate_and_tampered_shards(
    tmp_path, manifest
):
    specs = smoke_shards("SEL-AIR081-N025")
    for spec in specs:
        write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    assert len(validate_complete_set(tmp_path, manifest, specs)) == 3

    with pytest.raises(IntegrityError, match="duplicates"):
        validate_complete_set(tmp_path, manifest, (*specs, specs[0]))

    missing_path = tmp_path / "SEL-AIR081-N025--00001.meta.json"
    original_metadata = missing_path.read_bytes()
    missing_path.unlink()
    with pytest.raises(IntegrityError, match="missing"):
        validate_complete_set(tmp_path, manifest, specs)
    missing_path.write_bytes(original_metadata)

    records_path = tmp_path / "SEL-AIR081-N025--00002.jsonl"
    original_records = records_path.read_bytes()
    records_path.write_bytes(original_records + b"tampered\n")
    with pytest.raises(IntegrityError, match="hash"):
        validate_complete_set(tmp_path, manifest, specs)


def test_metadata_identity_and_forbidden_derived_results_fail_closed(tmp_path, manifest):
    spec = smoke_shards("REG", replicates=2, shard_size=2)[0]
    with pytest.raises(TypeError):
        RawReplicatePayload(
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
            tmp_path,
            manifest,
            spec,
            (
                RawReplicateRecord("REG", 0, {"p_value": 0.01}),
                RawReplicateRecord("REG", 1, {"raw_value": 1}),
            ),
        )

    write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    with pytest.raises(IntegrityError, match="code_commit"):
        validate_shard(tmp_path, replace(manifest, code_commit="2" * 40), spec)


def test_writer_cannot_accept_confirmatory_replicate_range(tmp_path, manifest):
    spec = frozen_confirmatory_shards()[0]
    assert spec.stop_replicate == 1_000
    with pytest.raises(ProductionRunLockedError):
        write_smoke_shard(tmp_path, manifest, spec, ())


def test_metadata_schema_is_raw_and_contains_environment_evidence(tmp_path, manifest):
    spec = smoke_shards("REG", replicates=2, shard_size=2)[0]
    write_smoke_shard(tmp_path, manifest, spec, _records(spec))
    metadata = json.loads((tmp_path / "REG--00000.meta.json").read_text())

    assert metadata["row_count"] == 2
    assert metadata["start_replicate"] == 0
    assert metadata["stop_replicate"] == 2
    assert metadata["status"] == "success"
    assert metadata["python_version"]
    assert metadata["records_sha256"]
    assert metadata["environment_lock_sha256"] == manifest.environment_lock_sha256


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
