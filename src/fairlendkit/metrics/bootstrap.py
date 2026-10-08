"""Project-owned deterministic SHA-256 counter bootstrap primitives."""

from __future__ import annotations

import hashlib
import math
from typing import Callable

import numpy as np

from fairlendkit.metrics.contracts import (
    BootstrapInterval,
    ComparisonUncertaintyRequest,
    UncertaintyEstimate,
    UncertaintyRequest,
)


RNG_NAME = "fairlendkit-sha256-counter-v1"
_DOMAIN_TAG = b"fairlendkit-bootstrap-v1\0"
_MAX_UINT64 = 2**64


class Sha256PercentileBootstrap:
    """Concrete adapter implementing the inner uncertainty protocol."""

    def estimate(
        self, request: UncertaintyRequest | ComparisonUncertaintyRequest
    ) -> UncertaintyEstimate:
        if isinstance(request, ComparisonUncertaintyRequest):
            return UncertaintyEstimate(
                comparison_bootstrap_interval(
                    request.comparison_size,
                    request.reference_size,
                    request.evaluator,
                    seed=request.seed,
                    metric_key=request.metric_key,
                    resamples=request.resamples,
                    minimum_valid_resamples=request.minimum_valid_resamples,
                    confidence_level=request.confidence_level,
                )
            )
        return UncertaintyEstimate(
            bootstrap_interval(
                request.population_size,
                request.evaluator,
                seed=request.seed,
                metric_key=request.metric_key,
                resamples=request.resamples,
                minimum_valid_resamples=request.minimum_valid_resamples,
                confidence_level=request.confidence_level,
                stream_role=request.stream_role,
            )
        )


class Sha256CounterSampler:
    """Version-independent unsigned integers from the frozen counter stream."""

    def __init__(self, seed: int, metric_key: str, stream_role: str) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < _MAX_UINT64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        if stream_role not in {"scope", "comparison", "reference"}:
            raise ValueError("stream_role must be scope, comparison, or reference")
        self._seed_material = (
            _DOMAIN_TAG
            + str(seed).encode("ascii")
            + b"\0"
            + metric_key.encode("utf-8")
            + b"\0"
            + stream_role.encode("ascii")
        )
        self._counter = 0
        self._candidates: list[int] = []

    def index(self, population_size: int) -> int:
        if population_size <= 0:
            raise ValueError("population_size must be positive")
        limit = _MAX_UINT64 - (_MAX_UINT64 % population_size)
        while True:
            if not self._candidates:
                if self._counter >= _MAX_UINT64:
                    raise OverflowError("SHA-256 counter overflow")
                digest = hashlib.sha256(
                    self._seed_material + self._counter.to_bytes(8, "big")
                ).digest()
                self._counter += 1
                self._candidates.extend(
                    int.from_bytes(digest[offset : offset + 8], "big")
                    for offset in range(0, 32, 8)
                )
            candidate = self._candidates.pop(0)
            if candidate < limit:
                return candidate % population_size


def bootstrap_index_draws(
    population_size: int,
    draws: int,
    *,
    seed: int,
    metric_key: str,
    stream_role: str,
) -> tuple[tuple[int, ...], ...]:
    """Return draw-major sampled positions without resetting the stream."""

    if draws < 1:
        raise ValueError("draws must be positive")
    matrix = _bootstrap_index_matrix(
        population_size,
        draws,
        seed=seed,
        metric_key=metric_key,
        stream_role=stream_role,
    )
    return tuple(tuple(int(value) for value in row) for row in matrix)


def _bootstrap_index_matrix(
    population_size: int,
    draws: int,
    *,
    seed: int,
    metric_key: str,
    stream_role: str,
) -> np.ndarray:
    """Return the frozen stream as a draw-major uint64 matrix."""
    if population_size <= 0:
        raise ValueError("population_size must be positive")
    if draws < 1:
        raise ValueError("draws must be positive")
    sampler = Sha256CounterSampler(seed, metric_key, stream_role)
    total = population_size * draws
    limit = _MAX_UINT64 - (_MAX_UINT64 % population_size)
    indices: list[int] = []
    counter = 0
    seed_material = sampler._seed_material
    while len(indices) < total:
        remaining_blocks = (total - len(indices) + 3) // 4
        block_count = min(4096, remaining_blocks + 8)
        if counter + block_count - 1 > _MAX_UINT64:
            raise OverflowError("SHA-256 counter overflow")
        digest_bytes = b"".join(
            hashlib.sha256(
                seed_material + value.to_bytes(8, "big")
            ).digest()
            for value in range(counter, counter + block_count)
        )
        counter += block_count
        candidates = np.frombuffer(digest_bytes, dtype=">u8")
        accepted = candidates[candidates < limit] % population_size
        indices.extend(accepted.tolist())
    del indices[total:]
    return np.asarray(indices, dtype=np.uint64).reshape(draws, population_size)


def type7_quantile(values: tuple[float, ...], probability: float) -> float:
    """Return the explicitly specified Hyndman-Fan Type 7 quantile."""

    if not values:
        raise ValueError("quantile values must not be empty")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be within [0, 1]")
    ordered = sorted(values)
    h = (len(ordered) - 1) * probability
    lower = math.floor(h)
    upper = math.ceil(h)
    return ordered[lower] + (h - lower) * (ordered[upper] - ordered[lower])


def bootstrap_interval(
    population_size: int,
    evaluator: Callable[[tuple[int, ...]], float | None],
    *,
    seed: int,
    metric_key: str,
    resamples: int,
    minimum_valid_resamples: int,
    confidence_level: float,
    stream_role: str = "scope",
) -> BootstrapInterval | None:
    """Evaluate one scope stream and return an interval only when sufficient."""

    draw_matrix = _bootstrap_index_matrix(
        population_size,
        resamples,
        seed=seed,
        metric_key=metric_key,
        stream_role=stream_role,
    )
    evaluate_batch = getattr(evaluator, "evaluate_batch", None)
    batch_values = None if evaluate_batch is None else evaluate_batch(draw_matrix)
    if batch_values is None:
        draws = (
            tuple(int(value) for value in row) for row in draw_matrix
        )
        candidates = (evaluator(indices) for indices in draws)
    else:
        candidates = iter(batch_values)
    valid = tuple(
        float(value)
        for value in candidates
        if value is not None and math.isfinite(value)
    )
    if len(valid) < minimum_valid_resamples:
        return None
    alpha = (1.0 - confidence_level) / 2.0
    return BootstrapInterval(
        metric_key=metric_key,
        confidence_level=confidence_level,
        lower=type7_quantile(valid, alpha),
        upper=type7_quantile(valid, 1.0 - alpha),
        valid_resamples=len(valid),
    )


def comparison_bootstrap_interval(
    comparison_size: int,
    reference_size: int,
    evaluator: Callable[[tuple[int, ...], tuple[int, ...]], float | None],
    *,
    seed: int,
    metric_key: str,
    resamples: int,
    minimum_valid_resamples: int,
    confidence_level: float,
) -> BootstrapInterval | None:
    """Evaluate independent comparison/reference streams for a directed metric."""

    comparison_matrix = _bootstrap_index_matrix(
        comparison_size,
        resamples,
        seed=seed,
        metric_key=metric_key,
        stream_role="comparison",
    )
    reference_matrix = _bootstrap_index_matrix(
        reference_size,
        resamples,
        seed=seed,
        metric_key=metric_key,
        stream_role="reference",
    )
    evaluate_batch = getattr(evaluator, "evaluate_comparison_batch", None)
    if evaluate_batch is None:
        comparison_draws = (
            tuple(int(value) for value in row) for row in comparison_matrix
        )
        reference_draws = (
            tuple(int(value) for value in row) for row in reference_matrix
        )
        candidates = (
            evaluator(comparison, reference)
            for comparison, reference in zip(comparison_draws, reference_draws)
        )
    else:
        candidates = iter(evaluate_batch(comparison_matrix, reference_matrix))
    valid = tuple(
        float(value)
        for value in candidates
        if value is not None and math.isfinite(value)
    )
    if len(valid) < minimum_valid_resamples:
        return None
    alpha = (1.0 - confidence_level) / 2.0
    return BootstrapInterval(
        metric_key=metric_key,
        confidence_level=confidence_level,
        lower=type7_quantile(valid, alpha),
        upper=type7_quantile(valid, 1.0 - alpha),
        valid_resamples=len(valid),
    )
