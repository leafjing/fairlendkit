"""SHA-256 counter RNG and frozen Paper 2 seed domains."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import nextafter
from struct import pack

from scipy.special import ndtri

UINT64_SCALE = 2**64
GENERATOR_DOMAIN = "fairlendkit-paper2-v1"
GENERATOR_ROLES = frozenset({"row", "missingness"})


@dataclass
class Sha256CounterRng:
    seed_material: bytes
    counter: int = 0
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
        return value

    def uniform(self) -> float:
        return self.uint64() / UINT64_SCALE

    def interior_uniform(self) -> float:
        value = self.uniform()
        if value == 0.0:
            return nextafter(0.0, 1.0)
        if value == 1.0:
            return nextafter(1.0, 0.0)
        return value

    def normal(self) -> float:
        return float(ndtri(self.interior_uniform()))

    def bernoulli(self, probability: float) -> int:
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Bernoulli probability must be in [0, 1].")
        return int(self.uniform() < probability)

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise ValueError("randbelow upper bound must be positive.")
        limit = UINT64_SCALE - (UINT64_SCALE % upper)
        while True:
            candidate = self.uint64()
            if candidate < limit:
                return candidate % upper


def generator_rng(
    *, master_seed: int, pairing_id: str, replicate_id: int, role: str
) -> Sha256CounterRng:
    if role not in GENERATOR_ROLES:
        raise ValueError(f"Unknown generator role: {role}")
    material = (
        f"{GENERATOR_DOMAIN}\0{master_seed}\0{pairing_id}\0{replicate_id}\0{role}"
    ).encode("utf-8")
    return Sha256CounterRng(material)


def analysis_rng(domain: str, *parts: object) -> Sha256CounterRng:
    if domain not in {"fairlendkit-paper2-summary-v1", "fairlendkit-paper2-h2-v1"}:
        raise ValueError("Analysis RNG domain is not registered.")
    return Sha256CounterRng(
        "\0".join((domain, *(str(part) for part in parts))).encode("utf-8")
    )
