"""Primary and cross-table complementary suppression for AD-1 counts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from typing import Iterable

from fairlendkit.alternative_data.contracts import (
    AggregateReportEvidence,
    AggregateReportRelease,
    AlternativeDataConfig,
    CreditCoverage,
    DisclosureState,
    SignalRecord,
)
from fairlendkit.alternative_data.quality import (
    QualityPopulationEntity,
    _typed_equal,
    _typed_sort_key,
    _typed_token,
    _calculate_quality_evidence,
)
from fairlendkit.alternative_data.leakage import (
    GateDisposition,
    evaluate_feature_record,
)


@dataclass(frozen=True)
class _CountCell:
    table_id: str
    cell_id: str
    entities: frozenset[str]
    is_total: bool = False

    @property
    def identity(self) -> tuple[str, str]:
        return self.table_id, self.cell_id


def build_quality_report_release(
    *,
    entities: Iterable[QualityPopulationEntity],
    records: Iterable[SignalRecord],
    coverages: Iterable[CreditCoverage],
    config: AlternativeDataConfig,
    previous_release: AggregateReportRelease | None = None,
) -> AggregateReportRelease:
    """Publish only counts that remain safe across every proposed quality view."""

    entity_items = tuple(entities)
    record_items = tuple(records)
    coverage_items = tuple(coverages)
    entity_ids = tuple(entity.entity_id for entity in entity_items)
    if len(set(entity_ids)) != len(entity_ids):
        raise ValueError("population entity identities must be unique")
    if any(record.entity_id not in set(entity_ids) for record in record_items):
        raise ValueError("every signal record must belong to the declared population")
    _calculate_quality_evidence(
        entities=entity_items,
        records=record_items,
        coverages=coverage_items,
        config=config,
    )
    available_records = tuple(
        record
        for record in record_items
        if evaluate_feature_record(
            record,
            config.observation_window,
            config.execution_time,
        ).disposition
        != GateDisposition.EXCLUDE
    )
    cells = _candidate_cells(entity_items, available_records, coverage_items, config)
    known = {cell.identity for cell in cells}
    locked = set()
    if previous_release is not None:
        current_counts = {cell.identity: len(cell.entities) for cell in cells}
        for cell in previous_release.cells:
            identity = (cell.table_id, cell.cell_id)
            if cell.state == DisclosureState.PUBLISHED and identity in known:
                if cell.entity_count is None:
                    raise ValueError("previously published cells require an exact count")
                if current_counts[identity] != cell.entity_count:
                    raise ValueError(
                        "current cell conflicts with a previously published exact value"
                    )
                locked.add(identity)
    return _apply_suppression(
        cells,
        config.minimum_report_cell_count,
        frozenset(locked),
    )


def _candidate_cells(
    entities: tuple[QualityPopulationEntity, ...],
    records: tuple[SignalRecord, ...],
    coverages: tuple[CreditCoverage, ...],
    config: AlternativeDataConfig,
) -> tuple[_CountCell, ...]:
    population = frozenset(entity.entity_id for entity in entities)
    cells = [_CountCell("quality.population", "overall", population, True)]

    supplied_by_family = {
        family: frozenset(
            record.entity_id for record in records if record.signal_family == family
        )
        for family in sorted(
            {source.signal_family for source in config.sources},
            key=lambda item: item.value,
        )
    }
    for family, members in supplied_by_family.items():
        cells.append(
            _CountCell("quality.signal_family", family.value, members)
        )

    coverage_map = {coverage.entity_id: coverage for coverage in coverages}
    coverage_cells: dict[str, frozenset[str]] = {}
    for value in sorted(config.allowed_coverage_strata, key=_typed_sort_key):
        key = _typed_token(value)
        members = frozenset(
            entity_id
            for entity_id, coverage in coverage_map.items()
            if coverage.evidence_available
            and coverage.assessed_at <= config.observation_window.as_of_time
            and _typed_equal(coverage.coverage_stratum, value)
        )
        coverage_cells[key] = members
        cells.append(_CountCell("quality.coverage", key, members))
    unavailable = population - frozenset().union(*coverage_cells.values())
    coverage_cells["unavailable"] = unavailable
    cells.append(_CountCell("quality.coverage", "unavailable", unavailable))

    group_cells: dict[tuple[str, str], frozenset[str]] = {}
    group_names = sorted({name for entity in entities for name in entity.audit_groups})
    for name in group_names:
        values = sorted(
            {
                _typed_token(entity.audit_groups[name]): entity.audit_groups[name]
                for entity in entities
                if name in entity.audit_groups
            }.values(),
            key=_typed_sort_key,
        )
        for value in values:
            name_token = _typed_token(name)
            value_token = _typed_token(value)
            members = frozenset(
                entity.entity_id
                for entity in entities
                if name in entity.audit_groups
                and _typed_equal(entity.audit_groups[name], value)
            )
            group_cells[(name_token, value_token)] = members
            cells.append(
                _CountCell(
                    f"quality.group.{name_token}",
                    value_token,
                    members,
                )
            )

    for coverage_key, coverage_members in sorted(coverage_cells.items()):
        for (name_token, value_token), group_members in sorted(group_cells.items()):
            cells.append(
                _CountCell(
                    f"quality.intersection.coverage.{name_token}",
                    f"{coverage_key}.{value_token}",
                    coverage_members & group_members,
                )
            )

    source_map = {source.source_id: source for source in config.sources}
    for source_id in sorted(source_map):
        members = frozenset(
            record.entity_id for record in records if record.source_id == source_id
        )
        cells.append(_CountCell("quality.source", _typed_token(source_id), members))

    for provider_id in sorted({source.provider_id for source in config.sources}):
        provider_sources = {
            source.source_id
            for source in config.sources
            if source.provider_id == provider_id
        }
        members = frozenset(
            record.entity_id
            for record in records
            if record.source_id in provider_sources
        )
        cells.append(
            _CountCell("quality.provider", _typed_token(provider_id), members)
        )

    identities = tuple(cell.identity for cell in cells)
    if len(set(identities)) != len(identities):
        raise ValueError("quality disclosure cell identities must be unique")
    return tuple(cells)


def _apply_suppression(
    cells: tuple[_CountCell, ...],
    minimum: int,
    locked: frozenset[tuple[str, str]],
) -> AggregateReportRelease:
    primary = {cell.identity for cell in cells if len(cell.entities) < minimum}
    if primary & locked:
        raise ValueError(
            "a previously published equivalent count now violates the disclosure minimum"
        )
    hidden = set(primary)
    complementary: set[tuple[str, str]] = set()
    atoms, actual = _atoms(cells)

    while True:
        published = tuple(cell for cell in cells if cell.identity not in hidden)
        unsafe = next(
            (
                cell
                for cell in cells
                if cell.identity in hidden
                and not _has_alternative_value(cell, cells, published, atoms, actual)
            ),
            None,
        )
        if unsafe is None:
            break
        candidates = [
            cell
            for cell in published
            if cell.identity not in locked
            and not cell.is_total
            and _has_alternative_value(
                unsafe,
                cells,
                tuple(item for item in published if item.identity != cell.identity),
                atoms,
                actual,
            )
        ]
        if not candidates:
            # Redundant cross-table equations can each preserve the same
            # disclosure. Remove them deterministically until one becomes
            # independently decisive under the exact system.
            candidates = [
                cell
                for cell in published
                if cell.identity not in locked and not cell.is_total
            ]
        if not candidates:
            candidates = [
                cell
                for cell in published
                if cell.identity not in locked
                and cell.is_total
                and _has_alternative_value(
                    unsafe,
                    cells,
                    tuple(
                        item for item in published if item.identity != cell.identity
                    ),
                    atoms,
                    actual,
                )
            ]
        if not candidates:
            raise ValueError("suppression cannot protect a previously exposed sparse cell")
        chosen = min(
            candidates,
            key=lambda cell: (len(cell.entities), cell.table_id, cell.cell_id),
        )
        hidden.add(chosen.identity)
        complementary.add(chosen.identity)

    output = []
    for cell in cells:
        count = len(cell.entities)
        if cell.identity in hidden:
            is_primary = cell.identity in primary
            output.append(
                AggregateReportEvidence(
                    table_id=cell.table_id,
                    cell_id=cell.cell_id,
                    state=DisclosureState.SUPPRESSED,
                    minimum_report_cell_count=minimum,
                    count_bucket=f"0..{minimum - 1}" if is_primary else "hidden",
                    reason_code=(
                        "ad_sparse_report_cell"
                        if is_primary
                        else "ad_complementary_suppression"
                    ),
                )
            )
        else:
            output.append(
                AggregateReportEvidence(
                    table_id=cell.table_id,
                    cell_id=cell.cell_id,
                    state=DisclosureState.PUBLISHED,
                    minimum_report_cell_count=minimum,
                    entity_count=count,
                    value=float(count),
                    numerator=float(count),
                )
            )
    return AggregateReportRelease(cells=tuple(output))


def _atoms(
    cells: tuple[_CountCell, ...],
) -> tuple[tuple[tuple[bool, ...], ...], tuple[int, ...]]:
    universe = sorted(set().union(*(cell.entities for cell in cells)))
    buckets: dict[tuple[bool, ...], int] = {}
    for entity_id in universe:
        signature = tuple(entity_id in cell.entities for cell in cells)
        buckets[signature] = buckets.get(signature, 0) + 1
    signatures = tuple(sorted(buckets))
    return signatures, tuple(buckets[signature] for signature in signatures)


def _has_alternative_value(
    hidden_cell: _CountCell,
    all_cells: tuple[_CountCell, ...],
    published: tuple[_CountCell, ...],
    atoms: tuple[tuple[bool, ...], ...],
    actual: tuple[int, ...],
) -> bool:
    if not published:
        # With no released equations, the bounded bucket itself leaves at
        # least 0 and 1 feasible; raw population metadata is never emitted.
        return True
    cell_index = {cell.identity: index for index, cell in enumerate(all_cells)}
    rows = [
        tuple(Fraction(int(atom[cell_index[cell.identity]])) for atom in atoms)
        for cell in published
    ]
    basis = _integer_nullspace(rows, len(atoms))
    hidden_vector = tuple(
        int(atom[cell_index[hidden_cell.identity]]) for atom in atoms
    )
    for direction in basis:
        if sum(a * b for a, b in zip(hidden_vector, direction)) == 0:
            continue
        for sign in (1, -1):
            candidate = tuple(
                value + sign * delta for value, delta in zip(actual, direction)
            )
            if min(candidate, default=0) >= 0:
                return True
    return False


def _integer_nullspace(
    rows: list[tuple[Fraction, ...]], width: int
) -> tuple[tuple[int, ...], ...]:
    if width == 0:
        return ()
    matrix = [list(row) for row in rows if any(row)]
    pivots: list[int] = []
    pivot_row = 0
    for column in range(width):
        found = next(
            (index for index in range(pivot_row, len(matrix)) if matrix[index][column]),
            None,
        )
        if found is None:
            continue
        matrix[pivot_row], matrix[found] = matrix[found], matrix[pivot_row]
        divisor = matrix[pivot_row][column]
        matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for index, row in enumerate(matrix):
            if index == pivot_row or not row[column]:
                continue
            factor = row[column]
            matrix[index] = [
                value - factor * pivot
                for value, pivot in zip(row, matrix[pivot_row])
            ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    free = [column for column in range(width) if column not in pivots]
    basis = []
    for free_column in free:
        vector = [Fraction(0) for _ in range(width)]
        vector[free_column] = Fraction(1)
        for row_index, pivot_column in reversed(list(enumerate(pivots))):
            vector[pivot_column] = -sum(
                matrix[row_index][column] * vector[column]
                for column in free
            )
        scale = math.lcm(*(value.denominator for value in vector))
        integers = [int(value * scale) for value in vector]
        divisor = reduce(math.gcd, (abs(value) for value in integers if value), 0) or 1
        basis.append(tuple(value // divisor for value in integers))
    return tuple(basis)
