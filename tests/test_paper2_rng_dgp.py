"""Deterministic smoke tests for the preregistered generator."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from fairlendkit.research.paper2.dgp import (
    generate_audit,
    population_auc,
    solve_alpha,
    solve_performance_parameters,
)
from fairlendkit.research.paper2.registry import scenario_registry
from fairlendkit.research.paper2.rng import analysis_rng, generator_rng
from fairlendkit.research.paper2.smoke import run_smoke


def _golden():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "paper2_phase1_golden.json").read_text()
    )


def _canonical_sha256(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_sha256_counter_rng_has_stable_candidates_and_separate_roles():
    row = generator_rng(master_seed=20261008, pairing_id="PAIR", replicate_id=7, role="row")
    missing = generator_rng(
        master_seed=20261008,
        pairing_id="PAIR",
        replicate_id=7,
        role="missingness",
    )

    assert [row.uint64() for _ in range(5)] == [
        13409849704425147760,
        1677555839080287418,
        17770011343145113409,
        16097191126087581247,
        4942100317005081386,
    ]
    assert missing.uint64() != generator_rng(
        master_seed=20261008, pairing_id="PAIR", replicate_id=7, role="row"
    ).uint64()
    assert analysis_rng("fairlendkit-paper2-h2-v1", 20261008, 0).uint64() != row.uint64()


def test_all_generator_and_analysis_streams_match_exact_golden_sequences():
    expected = _golden()["rng_uint64"]
    streams = {
        "generator_row": generator_rng(
            master_seed=20261008, pairing_id="PAIR", replicate_id=7, role="row"
        ),
        "generator_missingness": generator_rng(
            master_seed=20261008, pairing_id="PAIR", replicate_id=7, role="missingness"
        ),
        "analysis_summary": analysis_rng("fairlendkit-paper2-summary-v1", 20261008, 0),
        "analysis_h2": analysis_rng("fairlendkit-paper2-h2-v1", 20261008, 0),
    }
    for role, rng in streams.items():
        assert [rng.uint64() for _ in range(8)] == expected[role]


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

    assert alpha < 0
    assert beta > 0
    assert population_auc(alpha, beta) == pytest.approx(0.70, abs=1e-6)
    assert solve_alpha(0.20, beta) == pytest.approx(alpha, abs=1e-8)


def test_smoke_runner_is_deterministic_and_never_uses_production_seed():
    first = run_smoke(("SEL-AIR081-N025",), (0, 1))
    second = run_smoke(("SEL-AIR081-N025",), (0, 1))

    assert first == second
    production = generate_audit(scenario_registry()["SEL-AIR081-N025"], 0, 20261008)
    assert first.audits[0] != production


def test_unknown_rng_role_and_scenario_fail_closed():
    with pytest.raises(ValueError, match="role"):
        generator_rng(master_seed=1, pairing_id="X", replicate_id=0, role="bootstrap")
    with pytest.raises(ValueError, match="Unknown registered"):
        run_smoke(("NOT-A-SCENARIO",), (0,))
