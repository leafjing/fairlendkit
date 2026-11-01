"""Closed alternative-data reason codes and report-safe evidence."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlternativeDataDisposition(StrEnum):
    ERROR = "error"
    EXCLUDE = "exclude"
    UNAVAILABLE = "unavailable"
    OBSERVE = "observe"


class AlternativeDataReasonCode(StrEnum):
    MISSING_REQUIRED_FIELD = "ad_missing_required_field"
    UNKNOWN_FIELD = "ad_unknown_field"
    DUPLICATE_RECORD_IDENTITY = "ad_duplicate_record_identity"
    SOURCE_NOT_DECLARED = "ad_source_not_declared"
    SOURCE_FAMILY_MISMATCH = "ad_source_family_mismatch"
    SOURCE_VERSION_MISMATCH = "ad_source_version_mismatch"
    UNSUPPORTED_EVENT_TYPE = "ad_unsupported_event_type"
    INVALID_IDENTIFIER = "ad_invalid_identifier"
    PERMISSION_REFERENCE_UNAVAILABLE = "ad_permission_reference_unavailable"
    INVALID_WINDOW_ORDER = "ad_invalid_window_order"
    FEATURE_PERFORMANCE_OVERLAP = "ad_feature_performance_overlap"
    FEATURE_AFTER_DECISION = "ad_feature_after_decision"
    OBSERVED_AFTER_DECISION = "ad_observed_after_decision"
    REVISION_AFTER_DECISION = "ad_revision_after_decision"
    OUTCOME_NOT_POST_DECISION = "ad_outcome_not_post_decision"
    OUTCOME_OUTSIDE_WINDOW = "ad_outcome_outside_window"
    LABEL_IMMATURE = "ad_label_immature"
    UNRECOGNIZED_OUTCOME_LABEL = "ad_unrecognized_outcome_label"
    NON_MONOTONIC_HISTORY = "ad_non_monotonic_history"
    PERIOD_OVERLAP = "ad_period_overlap"
    TEMPORAL_GAP = "ad_temporal_gap"
    FUTURE_TIMESTAMP = "ad_future_timestamp"
    INVALID_AMOUNT = "ad_invalid_amount"
    CURRENCY_MISSING = "ad_currency_missing"
    CURRENCY_INCONSISTENT = "ad_currency_inconsistent"
    REVISION_TARGET_MISSING = "ad_revision_target_missing"
    REVERSAL_TARGET_MISSING = "ad_reversal_target_missing"
    LINKAGE_FAMILY_MISMATCH = "ad_linkage_family_mismatch"
    UNMATCHED_OBLIGATION = "ad_unmatched_obligation"
    UNCERTAIN_TRANSFER = "ad_uncertain_transfer"
    SIGNAL_NOT_PROVIDED = "ad_signal_not_provided"
    PROVIDER_REPORTING_GAP = "ad_provider_reporting_gap"
    OBLIGATION_SCHEDULE_UNAVAILABLE = "ad_obligation_schedule_unavailable"
    DUE_DATE_UNAVAILABLE = "ad_due_date_unavailable"
    BALANCE_HISTORY_UNAVAILABLE = "ad_balance_history_unavailable"
    INSUFFICIENT_CALENDAR_COVERAGE = "ad_insufficient_calendar_coverage"
    COVERAGE_STRATUM_UNAVAILABLE = "ad_coverage_stratum_unavailable"
    PROVIDER_NONPARTICIPATION = "ad_provider_nonparticipation"
    PENDING_RECORD = "ad_pending_record"
    SMALL_GROUP = "ad_small_group"
    SPARSE_REPORT_CELL = "ad_sparse_report_cell"
    COMPLEMENTARY_SUPPRESSION = "ad_complementary_suppression"
    INSUFFICIENT_FOLD_SUPPORT = "ad_insufficient_fold_support"
    HIGH_CARDINALITY_UNSUPPORTED = "ad_high_cardinality_unsupported"
    PROXY_MODEL_NONCONVERGENCE = "ad_proxy_model_nonconvergence"
    PROXY_HOLDOUT_UNSTABLE = "ad_proxy_holdout_unstable"
    CASHFLOW_REVERSAL_OBSERVED = "ad_cashflow_reversal_observed"
    CASHFLOW_CATEGORY_UNRESOLVED = "ad_cashflow_category_unresolved"
    RENT_PARTIAL_PAYMENT_OBSERVED = "ad_rent_partial_payment_observed"
    RENT_WAIVER_OBSERVED = "ad_rent_waiver_observed"
    UTILITY_ESTIMATED_BILL_OBSERVED = "ad_utility_estimated_bill_observed"
    UTILITY_ADJUSTMENT_OBSERVED = "ad_utility_adjustment_observed"
    SERVICE_INTERRUPTION_OBSERVED = "ad_service_interruption_observed"


REASON_CONTRACT = {
    AlternativeDataReasonCode.MISSING_REQUIRED_FIELD: (
        AlternativeDataDisposition.ERROR,
        "A conditionally required field is absent.",
    ),
    AlternativeDataReasonCode.UNKNOWN_FIELD: (
        AlternativeDataDisposition.ERROR,
        "Strict domain input contains an undeclared field.",
    ),
    AlternativeDataReasonCode.DUPLICATE_RECORD_IDENTITY: (
        AlternativeDataDisposition.ERROR,
        "Source/version contains the same record identity twice.",
    ),
    AlternativeDataReasonCode.SOURCE_NOT_DECLARED: (
        AlternativeDataDisposition.ERROR,
        "`source_id` does not resolve to a source contract.",
    ),
    AlternativeDataReasonCode.SOURCE_FAMILY_MISMATCH: (
        AlternativeDataDisposition.ERROR,
        "Record family differs from its source family.",
    ),
    AlternativeDataReasonCode.SOURCE_VERSION_MISMATCH: (
        AlternativeDataDisposition.ERROR,
        "Record and declared interpretation versions differ.",
    ),
    AlternativeDataReasonCode.UNSUPPORTED_EVENT_TYPE: (
        AlternativeDataDisposition.ERROR,
        "Event type is outside the exact family vocabulary.",
    ),
    AlternativeDataReasonCode.INVALID_IDENTIFIER: (
        AlternativeDataDisposition.ERROR,
        "Required opaque identifier is blank or malformed.",
    ),
    AlternativeDataReasonCode.PERMISSION_REFERENCE_UNAVAILABLE: (
        AlternativeDataDisposition.ERROR,
        "Source lacks the required governance reference.",
    ),
    AlternativeDataReasonCode.INVALID_WINDOW_ORDER: (
        AlternativeDataDisposition.ERROR,
        "Window boundaries violate their required ordering.",
    ),
    AlternativeDataReasonCode.FEATURE_PERFORMANCE_OVERLAP: (
        AlternativeDataDisposition.ERROR,
        "Feature and performance windows overlap.",
    ),
    AlternativeDataReasonCode.FEATURE_AFTER_DECISION: (
        AlternativeDataDisposition.ERROR,
        "Feature period or event ends after `as_of_time`.",
    ),
    AlternativeDataReasonCode.OBSERVED_AFTER_DECISION: (
        AlternativeDataDisposition.EXCLUDE,
        "A pre-decision event version first became observable after `as_of_time`.",
    ),
    AlternativeDataReasonCode.REVISION_AFTER_DECISION: (
        AlternativeDataDisposition.EXCLUDE,
        "A revision was first observable after `as_of_time`; the last eligible prior version remains authoritative.",
    ),
    AlternativeDataReasonCode.OUTCOME_NOT_POST_DECISION: (
        AlternativeDataDisposition.ERROR,
        "Outcome evidence starts at or before `as_of_time`.",
    ),
    AlternativeDataReasonCode.OUTCOME_OUTSIDE_WINDOW: (
        AlternativeDataDisposition.EXCLUDE,
        "Outcome evidence falls outside the configured performance window.",
    ),
    AlternativeDataReasonCode.LABEL_IMMATURE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Execution precedes `label_maturity_time`.",
    ),
    AlternativeDataReasonCode.FUTURE_TIMESTAMP: (
        AlternativeDataDisposition.ERROR,
        "Evidence claimed as observed or completed asserts knowledge after run execution; a future configured label-maturity date does not trigger this code.",
    ),
    AlternativeDataReasonCode.UNRECOGNIZED_OUTCOME_LABEL: (
        AlternativeDataDisposition.ERROR,
        "Mature outcome value is outside the explicit binary label mapping.",
    ),
    AlternativeDataReasonCode.NON_MONOTONIC_HISTORY: (
        AlternativeDataDisposition.ERROR,
        "Revision/reversal chain moves backward, cycles, or targets a later record.",
    ),
    AlternativeDataReasonCode.PERIOD_OVERLAP: (
        AlternativeDataDisposition.OBSERVE,
        "Same source/entity has overlapping asserted coverage periods.",
    ),
    AlternativeDataReasonCode.TEMPORAL_GAP: (
        AlternativeDataDisposition.OBSERVE,
        "Declared cadence expects but does not observe a period.",
    ),
    AlternativeDataReasonCode.INVALID_AMOUNT: (
        AlternativeDataDisposition.ERROR,
        "Amount is non-decimal, non-finite, or violates event sign rules.",
    ),
    AlternativeDataReasonCode.CURRENCY_MISSING: (
        AlternativeDataDisposition.ERROR,
        "Monetary record lacks currency.",
    ),
    AlternativeDataReasonCode.CURRENCY_INCONSISTENT: (
        AlternativeDataDisposition.EXCLUDE,
        "Currency violates source policy and no explicit conversion contract exists.",
    ),
    AlternativeDataReasonCode.REVISION_TARGET_MISSING: (
        AlternativeDataDisposition.ERROR,
        "`revision_of` target does not exist in the same source history.",
    ),
    AlternativeDataReasonCode.REVERSAL_TARGET_MISSING: (
        AlternativeDataDisposition.ERROR,
        "`reversal_of` target does not exist in the same source history.",
    ),
    AlternativeDataReasonCode.LINKAGE_FAMILY_MISMATCH: (
        AlternativeDataDisposition.ERROR,
        "Revision, reversal, payment, or obligation link crosses entity, source, family, or currency.",
    ),
    AlternativeDataReasonCode.UNMATCHED_OBLIGATION: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Rent/utility payment cannot resolve its explicit obligation.",
    ),
    AlternativeDataReasonCode.UNCERTAIN_TRANSFER: (
        AlternativeDataDisposition.OBSERVE,
        "Cash-flow transfer scope is uncertain; it is excluded from income/spending totals.",
    ),
    AlternativeDataReasonCode.SIGNAL_NOT_PROVIDED: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Entity has no supplied source for the family.",
    ),
    AlternativeDataReasonCode.PROVIDER_REPORTING_GAP: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Source explicitly reports a provider/period gap.",
    ),
    AlternativeDataReasonCode.OBLIGATION_SCHEDULE_UNAVAILABLE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Rent schedule is absent, so timeliness/nonpayment measures cannot be computed.",
    ),
    AlternativeDataReasonCode.DUE_DATE_UNAVAILABLE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "An obligation lacks usable due-date evidence.",
    ),
    AlternativeDataReasonCode.BALANCE_HISTORY_UNAVAILABLE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Cash-flow records contain no eligible balance observations.",
    ),
    AlternativeDataReasonCode.INSUFFICIENT_CALENDAR_COVERAGE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Eligible coverage is shorter than the configured minimum.",
    ),
    AlternativeDataReasonCode.COVERAGE_STRATUM_UNAVAILABLE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "User did not supply valid traditional-credit coverage evidence.",
    ),
    AlternativeDataReasonCode.PROVIDER_NONPARTICIPATION: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Provider/landlord does not supply the relevant period.",
    ),
    AlternativeDataReasonCode.PENDING_RECORD: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Record is pending at `as_of_time` and cannot enter behavior totals.",
    ),
    AlternativeDataReasonCode.SMALL_GROUP: (
        AlternativeDataDisposition.OBSERVE,
        "Group support is below the configured reliability minimum.",
    ),
    AlternativeDataReasonCode.SPARSE_REPORT_CELL: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Distinct-entity count is below the configured disclosure minimum.",
    ),
    AlternativeDataReasonCode.COMPLEMENTARY_SUPPRESSION: (
        AlternativeDataDisposition.UNAVAILABLE,
        "An additional cell is hidden to prevent recovery of a sparse value.",
    ),
    AlternativeDataReasonCode.INSUFFICIENT_FOLD_SUPPORT: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Proxy-screening folds do not meet configured entity and class support.",
    ),
    AlternativeDataReasonCode.HIGH_CARDINALITY_UNSUPPORTED: (
        AlternativeDataDisposition.UNAVAILABLE,
        "Candidate categories exceed the configured supported maximum after rare-level mapping.",
    ),
    AlternativeDataReasonCode.PROXY_MODEL_NONCONVERGENCE: (
        AlternativeDataDisposition.UNAVAILABLE,
        "The versioned proxy-screening model did not converge.",
    ),
    AlternativeDataReasonCode.PROXY_HOLDOUT_UNSTABLE: (
        AlternativeDataDisposition.OBSERVE,
        "Temporal-holdout evidence exceeds the configured stability tolerance.",
    ),
    AlternativeDataReasonCode.CASHFLOW_REVERSAL_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Eligible cash-flow event has an explicit reversal.",
    ),
    AlternativeDataReasonCode.CASHFLOW_CATEGORY_UNRESOLVED: (
        AlternativeDataDisposition.OBSERVE,
        "Category is absent or unresolved; record stays outside category-specific measures.",
    ),
    AlternativeDataReasonCode.RENT_PARTIAL_PAYMENT_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Explicit linked partial rent payment exists.",
    ),
    AlternativeDataReasonCode.RENT_WAIVER_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Explicit waiver changes the obligation denominator under the configured policy.",
    ),
    AlternativeDataReasonCode.UTILITY_ESTIMATED_BILL_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Bill is explicitly estimated.",
    ),
    AlternativeDataReasonCode.UTILITY_ADJUSTMENT_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Linked adjustment changes an obligation amount.",
    ),
    AlternativeDataReasonCode.SERVICE_INTERRUPTION_OBSERVED: (
        AlternativeDataDisposition.OBSERVE,
        "Explicit service interruption exists; no credit interpretation is attached.",
    ),
}


class AlternativeDataEvidence(BaseModel):
    """Aggregate-only evidence; raw record and entity identifiers are impossible."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    code: AlternativeDataReasonCode
    disposition: AlternativeDataDisposition
    scope: str = Field(min_length=1)
    count: int = Field(ge=1)
    source_id: str | None = None
    signal_family: str | None = None
    message: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_canonical_contract(self) -> "AlternativeDataEvidence":
        contract = REASON_CONTRACT.get(self.code)
        if contract is not None and (self.disposition, self.message) != contract:
            raise ValueError("disposition and message must match the reason contract")
        return self


def make_evidence(
    code: AlternativeDataReasonCode,
    *,
    scope: str,
    count: int = 1,
    source_id: str | None = None,
    signal_family: str | None = None,
) -> AlternativeDataEvidence:
    disposition, message = REASON_CONTRACT[code]
    return AlternativeDataEvidence(
        code=code,
        disposition=disposition,
        scope=scope,
        count=count,
        source_id=source_id,
        signal_family=signal_family,
        message=message,
    )
