"""Contract tests for the frozen Paper 2 phase-one manifest and registry."""

import json

import pytest

from fairlendkit.research.paper2.protocol import (
    ExecutionMode,
    ProductionRunLockedError,
    load_protocol,
)
from fairlendkit.research.paper2.registry import h2_scenario_units, scenario_registry


def test_protocol_manifest_matches_frozen_contract():
    protocol = load_protocol()

    assert protocol.status == "frozen"
    assert protocol.rng_schema_version == "paper2-rng-a1-v1"
    assert protocol.rng_fixture_sha256 == (
        "6e5d99c5531c03e3501dc0be16d68faf5338beb7b6246782f5a7623730577905"
    )
    assert protocol.a2_protocol_commit == "4a83ff8872d3393fad4313927045777f65fd3da4"
    assert protocol.a2_specification_commit == "9aa1afe0d48fedebdc5e9f26fecf31f68235838d"
    assert protocol.master_seed == 20261008
    assert protocol.confirmatory_replicates == 5_000
    assert protocol.monitoring_checkpoints == (1_000, 2_000, 3_000, 4_000)
    assert len(protocol.confirmatory_test_ids) == 5


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("confirmatory_replicates", 50_000),
        ("a2_protocol_commit", "0" * 40),
        ("a2_specification_commit", "0" * 40),
        ("protocol_id", "forged-paper2"),
        ("smoke_seed_domain", "forged-smoke-domain"),
    ),
)
def test_protocol_parser_fails_closed_on_extra_or_changed_fields(
    tmp_path, field, replacement
):
    source = {
        "protocol_id": "fairlendkit-paper2-v1",
        "status": "frozen",
        "rng_schema_version": "paper2-rng-a1-v1",
        "rng_fixture_sha256": "6e5d99c5531c03e3501dc0be16d68faf5338beb7b6246782f5a7623730577905",
        "a2_protocol_commit": "4a83ff8872d3393fad4313927045777f65fd3da4",
        "a2_specification_commit": "9aa1afe0d48fedebdc5e9f26fecf31f68235838d",
        "master_seed": 20261008,
        "confirmatory_replicates": 5_000,
        "exploratory_replicates": 10_000,
        "monitoring_checkpoints": [1_000, 2_000, 3_000, 4_000],
        "confirmatory_test_ids": [
            "P2-C1-AIR-MAE-N",
            "P2-C3-PRECISION-DEFINED",
            "P2-C4-AIR-FP-GATE",
            "P2-C5-MISSINGNESS-MAE",
            "P2-C6-AIR-COVERAGE",
        ],
        "smoke_seed_domain": "fairlendkit-paper2-smoke-v1",
    }
    source[field] = replacement
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(source))

    with pytest.raises(ValueError, match="conflicts"):
        load_protocol(path)


def test_confirmatory_execution_is_locked_while_smoke_ids_are_isolated():
    protocol = load_protocol()
    protocol.authorize(ExecutionMode.SMOKE, (0, 1, 99))

    with pytest.raises(ProductionRunLockedError):
        protocol.authorize(ExecutionMode.CONFIRMATORY, tuple(range(100)))
    with pytest.raises(ValueError, match="0..99"):
        protocol.authorize(ExecutionMode.SMOKE, (100,))


def test_registry_is_deterministic_exhaustive_and_has_frozen_pairing():
    registry = scenario_registry()

    assert list(registry) == sorted(registry)
    assert len(registry) == 124
    assert len(registry) == len(set(registry))
    for required in (
        "REG",
        "SEL-AIR081-N025",
        "SEL-AIR081-N050",
        "SEL-AIR081-N1000",
        "PERF-DEC001",
        "PERF-DEC050",
        "MISS-MCAR30",
        "MISS-MNAR30",
        "STRESS-N025-MNAR30",
    ):
        assert required in registry
    assert registry["SEL-AIR080-N025"].effective_pair_id == "PAIR-C1-N"
    assert registry["SEL-AIR080-N1000"].effective_pair_id == "PAIR-C1-N"
    assert registry["PERF-DEC001"].effective_pair_id == "PAIR-C3-DEC"
    assert registry["MISS-MNAR30"].effective_pair_id == "PAIR-C5-MISSING"


def test_h2_has_exactly_five_air_keyed_units_and_25_unique_ids():
    units = h2_scenario_units()
    scenario_ids = [unreliable for unreliable, _ in units]
    scenario_ids.extend(item for _, reliable in units for item in reliable)

    assert len(units) == 5
    assert len(scenario_ids) == 25
    assert len(set(scenario_ids)) == 25
    assert set(scenario_ids) <= scenario_registry().keys()
