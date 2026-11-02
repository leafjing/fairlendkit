from datetime import UTC, datetime

import pytest

import fairlendkit.alternative_data as alternative_data

from fairlendkit.alternative_data import (
    AlternativeDataConfig,
    AlternativeDataReasonCode,
    AlternativeDataSource,
    AggregateReportEvidence,
    AggregateReportRelease,
    CreditCoverage,
    ObservationWindow,
    QualityPopulationEntity,
    SignalRecord,
    build_quality_report_release,
)
from fairlendkit.alternative_data.quality import _calculate_quality_evidence
from fairlendkit.alternative_data.suppression import (
    _atoms,
    _candidate_cells,
    _has_alternative_value,
)


def source(**overrides):
    values = {
        "source_id": "cash-source",
        "signal_family": "cash_flow",
        "provider_id": "provider-a",
        "acquisition_method": "consumer_permissioned",
        "permission_reference": "governance-reference",
        "coverage_start": "2025-01-01T00:00:00Z",
        "coverage_end": "2026-01-01T00:00:00Z",
        "refresh_cadence": "P1D",
        "source_timezone": "UTC",
        "currency_policy": "single_currency",
        "default_currency": "USD",
        "source_version": "v1",
    }
    values.update(overrides)
    return AlternativeDataSource(**values)


def config(**overrides):
    values = {
        "sources": (source(),),
        "observation_window": ObservationWindow(
            as_of_time="2026-01-01T00:00:00Z",
            feature_start="2025-01-01T00:00:00Z",
            feature_end="2026-01-01T00:00:00Z",
            performance_start="2026-01-02T00:00:00Z",
            performance_end="2026-01-31T00:00:00Z",
            label_maturity_time="2026-02-01T00:00:00Z",
            outcome_definition="Explicit observed outcome",
        ),
        "execution_time": "2026-02-01T00:00:00Z",
        "allowed_coverage_strata": ("limited", "established"),
        "minimum_report_cell_count": 10,
    }
    values.update(overrides)
    return AlternativeDataConfig(**values)


def entity(entity_id, group):
    return QualityPopulationEntity(
        entity_id=entity_id,
        audit_groups={"audit_group": group},
    )


def coverage(entity_id, stratum="limited", **overrides):
    values = {
        "entity_id": entity_id,
        "coverage_stratum": stratum,
        "definition_id": "coverage-v1",
        "assessed_at": "2025-12-01T00:00:00Z",
        "evidence_available": True,
    }
    values.update(overrides)
    return CreditCoverage(**values)


def record(record_id, **overrides):
    values = {
        "entity_id": "entity-secret-1",
        "record_id": record_id,
        "source_id": "cash-source",
        "signal_family": "cash_flow",
        "event_type": "inflow",
        "event_time": "2025-12-01T00:00:00Z",
        "observed_at": "2025-12-01T00:00:00Z",
        "amount": "100.00",
        "currency": "USD",
        "status": "posted",
        "source_version": "v1",
    }
    values.update(overrides)
    return SignalRecord(**values)


def reason_map(scope):
    return {reason.code: reason.count for reason in scope.reasons}


def test_quality_engine_assembles_eligibility_coverage_and_group_evidence():
    entities = (
        entity("entity-secret-1", "A"),
        entity("entity-secret-2", "B"),
    )
    records = (
        record("original"),
        record(
            "revision",
            revision_of="original",
            observed_at="2025-12-02T00:00:00Z",
        ),
        record("pending", status="pending"),
        record("late", observed_at="2026-01-02T00:00:00Z"),
        record("wrong-currency", currency="EUR"),
    )
    result = _calculate_quality_evidence(
        entities=entities,
        records=records,
        coverages=(coverage("entity-secret-1"),),
        config=config(),
    )

    overall = result.scopes[0]
    assert result.population_count == 2
    assert overall.input_record_count == 5
    assert overall.authoritative_record_count == 1
    assert overall.eligible_record_count == 2
    assert overall.excluded_record_count == 2
    assert overall.unavailable_record_count == 1
    assert overall.unavailable_entity_count == 1
    assert overall.revision_count == 1
    assert overall.providers[0].entity_coverage_rate == 0.5
    assert overall.providers[0].source_id == "cash-source"
    assert overall.providers[0].signal_family == "cash_flow"
    assert overall.observation_start == datetime(2025, 12, 1, tzinfo=UTC)
    assert overall.refresh_lag_seconds == 30 * 24 * 60 * 60

    reasons = reason_map(overall)
    assert reasons[AlternativeDataReasonCode.OBSERVED_AFTER_DECISION] == 1
    assert reasons[AlternativeDataReasonCode.CURRENCY_INCONSISTENT] == 1
    assert reasons[AlternativeDataReasonCode.PENDING_RECORD] == 1
    assert reasons[AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED] == 1
    assert reasons[AlternativeDataReasonCode.COVERAGE_STRATUM_UNAVAILABLE] == 1
    pending_reason = next(
        item
        for item in overall.reasons
        if item.code == AlternativeDataReasonCode.PENDING_RECORD
    )
    assert pending_reason.unit == "record"
    assert pending_reason.population == "records_in_scope"
    assert pending_reason.denominator == 5
    assert pending_reason.scope_key == "overall"
    assert pending_reason.source_id == "cash-source"
    assert pending_reason.signal_family == "cash_flow"

    scope_keys = tuple(scope.scope_key for scope in result.scopes)
    assert scope_keys[0] == "overall"
    assert len([key for key in scope_keys if key.startswith("coverage.")]) == 3
    assert len([key for key in scope_keys if key.startswith("group.")]) == 2
    assert "family.cash_flow" in scope_keys
    family_scope = next(scope for scope in result.scopes if scope.scope_key == "family.cash_flow")
    assert family_scope.signal_family == "cash_flow"
    assert family_scope.input_record_count == 5


def test_missing_signal_is_unavailable_and_never_becomes_adverse_behavior():
    result = _calculate_quality_evidence(
        entities=(entity("entity-secret-2", "B"),),
        records=(),
        coverages=(),
        config=config(),
    )
    overall = result.scopes[0]

    assert overall.input_record_count == 0
    assert overall.eligible_record_count == 0
    assert overall.excluded_record_count == 0
    assert overall.unavailable_record_count == 0
    assert overall.unavailable_entity_count == 1
    assert set(reason_map(overall)) == {
        AlternativeDataReasonCode.COVERAGE_STRATUM_UNAVAILABLE,
        AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED,
    }


def test_missing_signal_reasons_are_separate_by_family_with_entity_denominators():
    multi_config = config(
        sources=(
            source(),
            source(
                source_id="rent-source",
                signal_family="rent",
                provider_id="rent-provider",
            ),
            source(
                source_id="utility-source",
                signal_family="utility",
                provider_id="utility-provider",
            ),
        )
    )
    result = _calculate_quality_evidence(
        entities=(entity("entity-secret-1", "A"),),
        records=(record("cash-record"),),
        coverages=(coverage("entity-secret-1"),),
        config=multi_config,
    )
    missing = tuple(
        reason
        for reason in result.scopes[0].reasons
        if reason.code == AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED
    )

    assert tuple(reason.signal_family for reason in missing) == ("rent", "utility")
    assert all(reason.unit == "entity" for reason in missing)
    assert all(reason.population == "entities_in_scope" for reason in missing)
    assert all(reason.scope_key == "overall" for reason in missing)
    assert all(reason.source_id is None for reason in missing)
    assert all(reason.count == 1 and reason.denominator == 1 for reason in missing)


def test_unpublished_quality_models_are_not_in_the_public_api():
    assert not hasattr(alternative_data, "calculate_quality_evidence")
    assert not hasattr(alternative_data, "QualityScopeResult")
    assert not hasattr(alternative_data, "AlternativeDataQualityResult")
    assert not hasattr(alternative_data, "QualityReasonCount")


def test_record_with_multiple_exclusion_reasons_counts_once():
    item = record(
        "late-wrong-currency",
        observed_at="2026-01-02T00:00:00Z",
        currency="EUR",
    )
    result = _calculate_quality_evidence(
        entities=(entity("entity-secret-1", "A"),),
        records=(item,),
        coverages=(coverage("entity-secret-1"),),
        config=config(),
    )
    overall = result.scopes[0]

    assert overall.excluded_record_count == 1
    assert reason_map(overall)[AlternativeDataReasonCode.CURRENCY_INCONSISTENT] == 1
    assert reason_map(overall)[AlternativeDataReasonCode.OBSERVED_AFTER_DECISION] == 1


def test_period_overlap_and_gap_are_typed_observations():
    records = (
        record(
            "period-1",
            event_time=None,
            period_start="2025-01-01T00:00:00Z",
            period_end="2025-01-31T00:00:00Z",
        ),
        record(
            "period-overlap",
            event_time=None,
            period_start="2025-01-15T00:00:00Z",
            period_end="2025-02-15T00:00:00Z",
        ),
        record(
            "period-gap",
            event_time=None,
            period_start="2025-03-01T00:00:00Z",
            period_end="2025-03-31T00:00:00Z",
        ),
    )
    result = _calculate_quality_evidence(
        entities=(entity("entity-secret-1", "A"),),
        records=records,
        coverages=(coverage("entity-secret-1"),),
        config=config(),
    )
    reasons = reason_map(result.scopes[0])

    assert reasons[AlternativeDataReasonCode.PERIOD_OVERLAP] == 2
    assert reasons[AlternativeDataReasonCode.TEMPORAL_GAP] == 1
    assert result.scopes[0].excluded_record_count == 0


def test_quality_output_is_deterministic_and_contains_no_consumer_identity():
    entities = (
        entity("entity-secret-1", "A"),
        entity("entity-secret-2", "B"),
    )
    records = (record("one"),)
    coverages = (coverage("entity-secret-1"),)
    first = _calculate_quality_evidence(
        entities=entities,
        records=records,
        coverages=coverages,
        config=config(),
    )
    second = _calculate_quality_evidence(
        entities=reversed(entities),
        records=reversed(records),
        coverages=reversed(coverages),
        config=config(),
    )

    assert first.model_dump_json() == second.model_dump_json()
    serialized = first.model_dump_json()
    assert "entity-secret-1" not in serialized
    assert "entity-secret-2" not in serialized
    assert "record_id" not in serialized


def test_quality_engine_fails_closed_on_future_evidence():
    with pytest.raises(ValueError, match="ad_future_timestamp"):
        _calculate_quality_evidence(
            entities=(entity("entity-secret-1", "A"),),
            records=(
                record(
                    "future",
                    event_time="2026-02-02T00:00:00Z",
                    observed_at="2026-02-02T00:00:00Z",
                ),
            ),
            coverages=(coverage("entity-secret-1"),),
            config=config(),
        )


def test_cross_table_suppression_prevents_sparse_cell_reconstruction():
    entities = tuple(
        entity(f"entity-secret-{index}", "rare" if index == 0 else "common")
        for index in range(20)
    )
    records = tuple(
        record(f"record-{index}", entity_id=item.entity_id)
        for index, item in enumerate(entities)
    )
    coverages = tuple(coverage(item.entity_id) for item in entities)

    release = build_quality_report_release(
        entities=entities,
        records=records,
        coverages=coverages,
        config=config(),
    )
    rare = next(
        cell
        for cell in release.cells
        if cell.table_id.startswith("quality.group.")
        and cell.cell_id.endswith("7261726522")
    )
    assert rare.state == "suppressed"
    assert rare.count_bucket == "0..9"
    assert rare.reason_code == "ad_sparse_report_cell"
    assert rare.entity_count is None
    assert any(
        cell.reason_code == "ad_complementary_suppression"
        for cell in release.cells
    )

    serialized = release.model_dump_json()
    assert "entity-secret-0" not in serialized
    assert '"entity_count":1' not in serialized

    candidate_cells = _candidate_cells(entities, records, coverages, config())
    published_ids = {
        (cell.table_id, cell.cell_id)
        for cell in release.cells
        if cell.state == "published"
    }
    published = tuple(
        cell for cell in candidate_cells if cell.identity in published_ids
    )
    atoms, actual = _atoms(candidate_cells)
    for released_cell in release.cells:
        if released_cell.state == "suppressed":
            hidden = next(
                cell
                for cell in candidate_cells
                if cell.identity == (released_cell.table_id, released_cell.cell_id)
            )
            assert _has_alternative_value(
                hidden,
                candidate_cells,
                published,
                atoms,
                actual,
            )


def test_primary_suppression_handles_zero_count_configured_cells():
    entities = tuple(entity(f"entity-secret-{index}", "A") for index in range(12))
    release = build_quality_report_release(
        entities=entities,
        records=(),
        coverages=tuple(coverage(item.entity_id) for item in entities),
        config=config(),
    )
    established = next(
        cell
        for cell in release.cells
        if cell.table_id == "quality.coverage"
        and cell.cell_id.endswith("65737461626c697368656422")
    )
    assert established.state == "suppressed"
    assert established.count_bucket == "0..9"


def test_public_release_never_serializes_exact_sparse_values_or_intervals():
    release = build_quality_report_release(
        entities=(entity("entity-secret-1", "rare"),),
        records=(record("record-1"),),
        coverages=(coverage("entity-secret-1"),),
        config=config(),
    )

    assert release.__class__.__name__ == "AggregateReportRelease"
    assert any(cell.table_id == "quality.provider" for cell in release.cells)
    for cell in release.cells:
        assert cell.state == "suppressed"
        assert cell.entity_count is None
        assert cell.value is None
        assert cell.numerator is None
        assert cell.denominator is None
        assert cell.interval_lower is None
        assert cell.interval_upper is None


def test_previous_published_exact_value_is_an_enforced_release_constraint():
    entities = tuple(entity(f"entity-secret-{index}", "A") for index in range(12))
    records = tuple(
        record(f"record-{index}", entity_id=item.entity_id)
        for index, item in enumerate(entities)
    )
    coverages = tuple(coverage(item.entity_id) for item in entities)
    previous = AggregateReportRelease(
        cells=(
            AggregateReportEvidence(
                table_id="quality.population",
                cell_id="overall",
                state="published",
                minimum_report_cell_count=10,
                entity_count=12,
                value=12.0,
                numerator=12.0,
            ),
        )
    )

    with pytest.raises(ValueError, match="previously published exact value"):
        build_quality_report_release(
            entities=entities[:-1],
            records=records[:-1],
            coverages=coverages[:-1],
            config=config(),
            previous_release=previous,
        )
