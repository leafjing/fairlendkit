"""A1 SHA-256 counter RNG with closed routing and exact transforms."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite
from struct import pack

from scipy.special import ndtri

UINT64_SCALE = 2**64
ROOT_DOMAIN = "fairlendkit-paper2-v1"
PURPOSE_ROLES = {
    "generate": frozenset(
        {
            "selection_decision_uniform",
            "selection_outcome_uniform",
            "performance_x_normal",
            "performance_outcome_uniform",
            "weight_normal",
            "missingness_uniform",
        }
    ),
    "summary_bootstrap": frozenset({"replicate_index"}),
    "h2_bootstrap": frozenset({"scenario_unit_index"}),
}
PAIR_SHARED_ROLES = {
    "PAIR-C1-N": frozenset({"selection_decision_uniform", "selection_outcome_uniform"}),
    "PAIR-C3-DEC": frozenset({"performance_x_normal", "performance_outcome_uniform"}),
    "PAIR-C5-MISSING": frozenset(
        {"performance_x_normal", "performance_outcome_uniform", "missingness_uniform"}
    ),
    "PAIR-C6-COVERAGE": frozenset(
        {"selection_decision_uniform", "selection_outcome_uniform"}
    ),
}


def uniform_closed_open(value: int) -> float:
    return (value >> 11) * 2.0**-53


def uniform_open(value: int) -> float:
    return ((value >> 12) + 0.5) * 2.0**-52


def normal_from_uint64(value: int) -> float:
    return float(ndtri(uniform_open(value)))


@dataclass
class Sha256CounterRng:
    seed_material: bytes
    counter: int = 0
    candidates_consumed: int = 0
    _candidates: tuple[int, ...] = ()
    _candidate_index: int = 0

    def _refill(self) -> None:
        digest = hashlib.sha256(self.seed_material + pack(">Q", self.counter)).digest()
        self.counter += 1
        self._candidates = tuple(
            int.from_bytes(digest[offset : offset + 8], "big")
            for offset in range(0, 32, 8)
        )
        self._candidate_index = 0

    def uint64(self) -> int:
        if self._candidate_index == len(self._candidates):
            self._refill()
        value = self._candidates[self._candidate_index]
        self._candidate_index += 1
        self.candidates_consumed += 1
        return value

    def uniform(self) -> float:
        return uniform_closed_open(self.uint64())

    def normal(self) -> float:
        return normal_from_uint64(self.uint64())

    def bernoulli(self, probability: float) -> int:
        if not isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("Bernoulli probability must be finite and in [0, 1].")
        return int(self.uniform() < probability)

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise ValueError("randbelow upper bound must be positive.")
        limit = UINT64_SCALE - (UINT64_SCALE % upper)
        while True:
            candidate = self.uint64()
            if candidate < limit:
                return candidate % upper


def rng_stream(
    *,
    master_seed: int,
    purpose: str,
    unit_id: str,
    draw_id: int,
    scope: str,
    role: str,
) -> Sha256CounterRng:
    if purpose not in PURPOSE_ROLES or role not in PURPOSE_ROLES[purpose]:
        raise ValueError("RNG purpose/role is not registered by A1.")
    if purpose == "generate":
        if scope != "shared" and not scope.startswith("scenario:"):
            raise ValueError("Generate scope must be shared or scenario-specific.")
    elif scope != "analysis":
        raise ValueError("Analysis RNG scope must be analysis.")
    fields = (ROOT_DOMAIN, str(master_seed), purpose, unit_id, str(draw_id), scope, role)
    if any("\0" in field or not field.isascii() for field in fields):
        raise ValueError("RNG seed fields must be ASCII without NULs.")
    return Sha256CounterRng("\0".join(fields).encode("ascii"))


def generator_rng(
    *, master_seed: int, pair_id: str, replicate_id: int, scope: str, role: str
) -> Sha256CounterRng:
    return rng_stream(
        master_seed=master_seed,
        purpose="generate",
        unit_id=pair_id,
        draw_id=replicate_id,
        scope=scope,
        role=role,
    )


def generator_scope(pair_id: str, scenario_id: str, role: str) -> str:
    if role not in PURPOSE_ROLES["generate"]:
        raise ValueError("Generator role is not registered by A1.")
    if role in PAIR_SHARED_ROLES.get(pair_id, frozenset()):
        return "shared"
    return f"scenario:{scenario_id}"


def analysis_rng(purpose: str, unit_id: str, master_seed: int, draw_id: int) -> Sha256CounterRng:
    role = "replicate_index" if purpose == "summary_bootstrap" else "scenario_unit_index"
    return rng_stream(
        master_seed=master_seed,
        purpose=purpose,
        unit_id=unit_id,
        draw_id=draw_id,
        scope="analysis",
        role=role,
    )
