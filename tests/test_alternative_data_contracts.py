from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fairlendkit.alternative_data import (
    AlternativeDataConfig,
    AggregateReportEvidence,
    AggregateReportRelease,
    AlternativeDataReasonCode,
    AlternativeDataSource,
    CreditCoverage,
    ObservationWindow,
    SignalRecord,
    make_evidence,
)


def source_values(**overrides):
    values = {
        "source_id": "source-v1",
        "signal_family": "cash_flow",
        "provider_id": "provider-1",
        "acquisition_method": "consumer_permissioned",
        "permission_reference": "governance-42",
        "coverage_start": "2025-01-01T00:00:00Z",
        "coverage_end": "2026-01-31T00:00:00Z",
        "refresh_cadence": "P1D",
        "source_timezone": "America/New_York",
        "currency_policy": "single_currency",
        "default_currency": "USD",
        "source_version": "v1",
    }
    values.update(overrides)
    return values


def record_values(**overrides):
    values = {
        "entity_id": "consumer-secret-17",
        "record_id": "record-secret-9",
        "source_id": "source-v1",
        "signal_family": "cash_flow",
        "event_type": "inflow",
        "event_time": "2025-12-31T12:00:00Z",
        "observed_at": "2025-12-31T13:00:00Z",
        "amount": "1250.50",
        "currency": "USD",
        "status": "posted",
        "source_version": "v1",
    }
    values.update(overrides)
    return values


def test_source_contract_is_strict_and_normalizes_times():
    source = AlternativeDataSource(**source_values())

    assert source.coverage_start.tzinfo is UTC
    assert source.model_dump(mode="json")["signal_family"] == "cash_flow"

    with pytest.raises(ValidationError, match="Extra inputs"):
        AlternativeDataSource(**source_values(consumer_name="not allowed"))

    assert AlternativeDataSource(
        **source_values(refresh_cadence="P1M")
    ).refresh_cadence == "P1M"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"source_id": " source-v1"}, "surrounding whitespace"),
        ({"refresh_cadence": "P0D"}, "positive"),
        ({"source_timezone": "Not/AZone"}, "IANA"),
        ({"default_currency": "usd"}, "ISO 4217"),
        ({"currency_policy": "record_currency"}, "required only"),
    ],
)
def test_source_contract_rejects_ambiguous_metadata(overrides, message):
    with pytest.raises(ValidationError, match=message):
        AlternativeDataSource(**source_values(**overrides))


def test_observation_window_enforces_leakage_order_and_maturity():
    window = ObservationWindow(
        as_of_time="2026-01-01T00:00:00Z",
        feature_start="2025-07-01T00:00:00Z",
        feature_end="2026-01-01T00:00:00Z",
        performance_start="2026-01-02T00:00:00Z",
        performance_end="2026-01-31T00:00:00Z",
        label_maturity_time="2026-02-15T00:00:00Z",
        outcome_definition="Explicit 30-day observed outcome",
    )

    assert not window.label_is_mature(datetime(2026, 2, 14, tzinfo=UTC))
    assert window.label_is_mature(datetime(2026, 2, 15, tzinfo=UTC))

    with pytest.raises(ValidationError, match="window order"):
        ObservationWindow(
            **{
                **window.model_dump(),
                "performance_start": "2026-01-01T00:00:00Z",
            }
        )


def test_credit_coverage_never_infers_a_stratum_from_missing_evidence():
    unavailable = CreditCoverage(
        entity_id="entity-1",
        coverage_stratum=None,
        definition_id="coverage-policy-v1",
        assessed_at="2026-01-01T00:00:00Z",
        evidence_available=False,
    )

    assert unavailable.coverage_stratum is None
    with pytest.raises(ValidationError, match="required exactly"):
        CreditCoverage(
            entity_id="entity-1",
            coverage_stratum="limited_file",
            definition_id="coverage-policy-v1",
            assessed_at="2026-01-01T00:00:00Z",
            evidence_available=False,
        )


def test_run_config_requires_disclosure_floor_and_type_sensitive_strata():
    observation_window = ObservationWindow(
        as_of_time="2026-01-01T00:00:00Z",
        feature_start="2025-07-01T00:00:00Z",
        feature_end="2026-01-01T00:00:00Z",
        performance_start="2026-01-02T00:00:00Z",
        performance_end="2026-01-31T00:00:00Z",
        label_maturity_time="2026-02-15T00:00:00Z",
        outcome_definition="Explicit 30-day observed outcome",
    )
    config = AlternativeDataConfig(
        sources=(AlternativeDataSource(**source_values()),),
        observation_window=observation_window,
        execution_time="2026-02-01T00:00:00Z",
        allowed_coverage_strata=(True, 1, "1"),
        minimum_report_cell_count=10,
    )

    assert config.minimum_report_cell_count == 10
    with pytest.raises(ValidationError, match="greater than or equal to 10"):
        AlternativeDataConfig(
            **{
                **config.model_dump(),
                "minimum_report_cell_count": 9,
            }
        )


def test_every_reason_code_has_canonical_report_safe_evidence():
    for code in AlternativeDataReasonCode:
        evidence = make_evidence(code, scope="overall")
        serialized = evidence.model_dump(mode="json")
        assert serialized["code"] == code.value
        assert serialized["message"].endswith(".")
        assert "entity_id" not in serialized
        assert "record_id" not in serialized


def test_signal_amount_is_decimal_string_and_temporal_form_is_exclusive():
    record = SignalRecord(**record_values())

    assert record.model_dump(mode="json")["amount"] == "1250.50"
    with pytest.raises(ValidationError, match="decimal string"):
        SignalRecord(**record_values(amount=1250.50))
    with pytest.raises(ValidationError, match="exactly event_time"):
        SignalRecord(
            **record_values(
                period_start="2025-12-01T00:00:00Z",
                period_end="2025-12-31T00:00:00Z",
            )
        )

    with pytest.raises(ValidationError, match="same temporal type"):
        SignalRecord(
            **record_values(
                event_time=None,
                period_start="2025-12-01",
                period_end="2025-12-31T00:00:00Z",
            )
        )


def test_signal_family_payload_and_exact_vocabulary_are_enforced():
    with pytest.raises(ValidationError, match="does not belong"):
        SignalRecord(**record_values(event_type="bill"))
    with pytest.raises(ValidationError, match="transfer_scope"):
        SignalRecord(**record_values(event_type="transfer"))

    utility_payment = SignalRecord(
        **record_values(
            signal_family="utility",
            event_type="payment",
            obligation_id="utility-obligation-1",
        )
    )
    assert utility_payment.event_type == "payment"

    with pytest.raises(ValidationError, match="reversal_of"):
        SignalRecord(
            **record_values(
                event_type="reversal",
                amount=None,
                currency="USD",
            )
        )


def test_report_boundary_accepts_only_aggregate_suppressed_evidence():
    sparse = AggregateReportEvidence(
        cell_id="cell-a",
        table_id="provider-by-group",
        state="suppressed",
        minimum_report_cell_count=10,
        count_bucket="0..9",
        reason_code="ad_sparse_report_cell",
    )
    complementary = AggregateReportEvidence(
        cell_id="cell-b",
        table_id="coverage-by-group",
        state="suppressed",
        minimum_report_cell_count=10,
        count_bucket="hidden",
        reason_code="ad_complementary_suppression",
    )
    release = AggregateReportRelease(cells=(sparse, complementary))
    rendered = release.model_dump_json()
    assert "entity_id" not in rendered and "record_id" not in rendered
    assert "numerator" in rendered and '"numerator":null' in rendered

    with pytest.raises(ValidationError, match="cannot expose"):
        AggregateReportEvidence(
            **{**sparse.model_dump(), "entity_count": 3}
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        AggregateReportRelease(
            cells=(sparse,),
            raw_record=record_values(),
        )


def test_validation_errors_hide_sensitive_input_values():
    with pytest.raises(ValidationError) as error:
        SignalRecord(**record_values(unexpected_secret="consumer-secret-17"))

    assert "consumer-secret-17" not in str(error.value)
