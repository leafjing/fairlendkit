"""Deterministic smoke tests for the preregistered generator."""

import hashlib
import json
from dataclasses import asdict
from math import log
from pathlib import Path
from struct import pack

import pytest
from scipy.special import ndtr

from fairlendkit.research.paper2.dgp import (
    generate_audit,
    population_auc,
    solve_alpha,
    solve_performance_parameters,
    solve_score_threshold,
)
from fairlendkit.research.paper2.registry import Calibration, scenario_registry
from fairlendkit.research.paper2.rng import (
    generator_rng,
    generator_scope,
    normal_from_uint64,
    rng_stream,
    uniform_closed_open,
    uniform_open,
)
from fairlendkit.research.paper2.smoke import run_smoke


def _golden():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "paper2_phase1_golden.json").read_text()
    )


def _a1_golden():
    path = Path(__file__).parents[1] / "docs" / "fixtures" / "paper2-rng-a1-golden.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "6e5d99c5531c03e3501dc0be16d68faf5338beb7b6246782f5a7623730577905"
    )
    return json.loads(path.read_text())


def _canonical_sha256(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reference_uint64(seed: bytes, count: int) -> list[int]:
    values: list[int] = []
    counter = 0
    while len(values) < count:
        digest = hashlib.sha256(seed + pack(">Q", counter)).digest()
        values.extend(
            int.from_bytes(digest[offset : offset + 8], "big")
            for offset in range(0, 32, 8)
        )
        counter += 1
    return values[:count]


def _reference_indices(seed: bytes, bound: int, count: int) -> list[int]:
    limit = 2**64 - (2**64 % bound)
    accepted: list[int] = []
    counter = 0
    while len(accepted) < count:
        digest = hashlib.sha256(seed + pack(">Q", counter)).digest()
        counter += 1
        for offset in range(0, 32, 8):
            candidate = int.from_bytes(digest[offset : offset + 8], "big")
            if candidate < limit:
                accepted.append(candidate % bound)
                if len(accepted) == count:
                    break
    return accepted


def test_a1_shared_stream_matches_normative_fixture_and_independent_reference():
    expected = _a1_golden()["shared_generator"]
    rng = rng_stream(
        master_seed=20261008,
        purpose="generate",
        unit_id="PAIR-C1-N",
        draw_id=0,
        scope="shared",
        role="selection_decision_uniform",
    )
    assert rng.seed_material.hex() == expected["seed_hex"]
    assert hashlib.sha256(rng.seed_material + pack(">Q", 0)).hexdigest() == expected["counter_0_sha256"]
    words = [rng.uint64() for _ in range(8)]
    assert words == expected["first_uint64"]
    assert words == _reference_uint64(bytes.fromhex(expected["seed_hex"]), 8)
    assert [uniform_closed_open(word).hex() for word in words] == expected["uniform_binary64_hex"]
    assert [int(uniform_closed_open(word) < 0.5) for word in words] == expected["bernoulli_p_0_5"]


def test_a1_normal_endpoints_and_scenario_stream_match_exact_binary64():
    expected = _a1_golden()
    for endpoint in expected["uint64_endpoint_transforms"]:
        value = endpoint["uint64"]
        assert uniform_closed_open(value).hex() == endpoint["uniform_closed_open_binary64_hex"]
        assert uniform_open(value).hex() == endpoint["uniform_open_binary64_hex"]
        assert normal_from_uint64(value).hex() == endpoint["normal_binary64_hex"]
        assert pack(">d", normal_from_uint64(value)).hex() == endpoint["normal_binary64_be"]

    vector = expected["scenario_specific_normal"]
    rng = rng_stream(
        master_seed=20261008,
        purpose="generate",
        unit_id="REG",
        draw_id=0,
        scope="scenario:REG",
        role="performance_x_normal",
    )
    words = [rng.uint64() for _ in range(8)]
    assert words == vector["first_uint64"]
    assert [pack(">d", normal_from_uint64(word)).hex() for word in words] == vector["normal_binary64_be"]


def test_a1_bounded_integer_indices_and_rejection_consumption_are_exact():
    expected = _a1_golden()
    for key, purpose, unit_id, role in (
        ("h2_exact_indices", "h2_bootstrap", "H2", "scenario_unit_index"),
        ("summary_exact_indices", "summary_bootstrap", "REG:adverse_impact_ratio:50000", "replicate_index"),
        ("rejection_sampling_stress", "h2_bootstrap", "H2", "scenario_unit_index"),
    ):
        case = expected[key]
        rng = rng_stream(
            master_seed=20261008,
            purpose=purpose,
            unit_id=unit_id,
            draw_id=0,
            scope="analysis",
            role=role,
        )
        assert [rng.randbelow(case["bound"]) for _ in case["indices"]] == case["indices"]
        assert rng.candidates_consumed == case["candidates_consumed"]


def test_a1_complete_h2_and_small_summary_index_bytes_match_checked_in_hashes():
    expected = _golden()["bootstrap_index_bytes"]
    cases = (
        ("h2_bootstrap", "H2", "scenario_unit_index", 5, 5, "h2_2000_by_5_sha256"),
        (
            "summary_bootstrap",
            "REG:adverse_impact_ratio:50000",
            "replicate_index",
            17,
            17,
            "summary_2000_by_17_sha256",
        ),
    )
    for purpose, unit_id, role, bound, width, hash_key in cases:
        payload = bytearray()
        reference = bytearray()
        for draw_id in range(2_000):
            rng = rng_stream(
                master_seed=20261008,
                purpose=purpose,
                unit_id=unit_id,
                draw_id=draw_id,
                scope="analysis",
                role=role,
            )
            for _ in range(width):
                payload.extend(pack(">Q", rng.randbelow(bound)))
            for index in _reference_indices(rng.seed_material, bound, width):
                reference.extend(pack(">Q", index))
        assert bytes(payload) == bytes(reference)
        assert hashlib.sha256(payload).hexdigest() == expected[hash_key]


def test_a1_pair_routing_shares_only_registered_roles_without_collisions():
    registry = scenario_registry()
    pair_cases = {
        "PAIR-C1-N": ("SEL-AIR080-N025", "SEL-AIR080-N1000"),
        "PAIR-C3-DEC": ("PERF-DEC001", "PERF-DEC050"),
        "PAIR-C5-MISSING": ("MISS-MCAR30", "MISS-MNAR30"),
        "PAIR-C6-COVERAGE": ("SEL-AIR081-N050", "SEL-AIR081-N1000"),
    }
    roles = {
        "PAIR-C1-N": ("selection_decision_uniform", "selection_outcome_uniform"),
        "PAIR-C3-DEC": ("performance_x_normal", "performance_outcome_uniform"),
        "PAIR-C5-MISSING": (
            "performance_x_normal",
            "performance_outcome_uniform",
            "missingness_uniform",
        ),
        "PAIR-C6-COVERAGE": ("selection_decision_uniform", "selection_outcome_uniform"),
    }
    shared_seeds: set[bytes] = set()
    for pair_id, scenario_ids in pair_cases.items():
        assert {registry[item].effective_pair_id for item in scenario_ids} == {pair_id}
        for role in roles[pair_id]:
            scopes = {generator_scope(pair_id, scenario_id, role) for scenario_id in scenario_ids}
            assert scopes == {"shared"}
            seed = generator_rng(
                master_seed=20261008,
                pair_id=pair_id,
                replicate_id=0,
                scope="shared",
                role=role,
            ).seed_material
            assert seed not in shared_seeds
            shared_seeds.add(seed)

    scenario_a = generator_rng(
        master_seed=20261008,
        pair_id="REG",
        replicate_id=0,
        scope=generator_scope("REG", "REG", "performance_x_normal"),
        role="performance_x_normal",
    ).seed_material
    scenario_b = generator_rng(
        master_seed=20261008,
        pair_id="PERF-AUC070",
        replicate_id=0,
        scope=generator_scope("PERF-AUC070", "PERF-AUC070", "performance_x_normal"),
        role="performance_x_normal",
    ).seed_material
    assert scenario_a != scenario_b
    assert scenario_a not in shared_seeds
    assert scenario_b not in shared_seeds


def test_registry_and_dgp_match_checked_in_golden_hashes():
    golden = _golden()
    registry = scenario_registry()
    registry_payload = [asdict(registry[key]) for key in registry]

    assert len(registry) == golden["registry"]["scenario_count"]
    assert _canonical_sha256(registry_payload) == golden["registry"]["canonical_sha256"]
    for case in golden["dgp"]:
        audit = generate_audit(
            registry[case["scenario_id"]], case["replicate_id"], case["master_seed"]
        )
        assert len(audit.rows) == case["row_count"]
        assert _canonical_sha256(asdict(audit)) == case["canonical_sha256"]


def test_paired_size_scenarios_use_prefixes_of_the_same_row_stream():
    registry = scenario_registry()
    small = generate_audit(registry["SEL-AIR080-N025"], 3, 20261008)
    large = generate_audit(registry["SEL-AIR080-N1000"], 3, 20261008)

    assert small.rows[:25] == large.rows[:25]
    assert small.rows[25:] == large.rows[1000:1025]


def test_selection_dgp_obeys_score_decision_rule_and_group_counts():
    scenario = scenario_registry()["SEL-AIR081-N025"]
    audit = generate_audit(scenario, 1, 999)

    assert len(audit.rows) == 50
    assert sum(row.group == 0 for row in audit.rows) == 25
    assert all(row.decision == int(row.score >= 0.5) for row in audit.rows)
    assert {row.score for row in audit.rows} <= {0.25, 0.75}


def test_performance_solver_hits_prevalence_and_auc_targets():
    alpha, beta = solve_performance_parameters(0.20, 0.70)
    threshold = solve_score_threshold(alpha, beta, Calibration.CALIBRATED, 0.20)
    x_threshold = (log(threshold / (1.0 - threshold)) - alpha) / beta

    assert alpha < 0
    assert beta > 0
    assert population_auc(alpha, beta) == pytest.approx(0.70, abs=1e-6)
    assert solve_alpha(0.20, beta) == pytest.approx(alpha, abs=1e-10)
    assert 1.0 - float(ndtr(x_threshold)) == pytest.approx(0.20, abs=1e-10)


def test_smoke_runner_is_deterministic_and_never_uses_production_seed():
    first = run_smoke(("SEL-AIR081-N025",), (0, 1))
    second = run_smoke(("SEL-AIR081-N025",), (0, 1))

    assert first == second
    production = generate_audit(scenario_registry()["SEL-AIR081-N025"], 0, 20261008)
    assert first.audits[0] != production


def test_unknown_rng_role_and_scenario_fail_closed():
    with pytest.raises(ValueError, match="role"):
        generator_rng(
            master_seed=1,
            pair_id="X",
            replicate_id=0,
            scope="shared",
            role="bootstrap",
        )
    with pytest.raises(ValueError, match="Unknown registered"):
        run_smoke(("NOT-A-SCENARIO",), (0,))
