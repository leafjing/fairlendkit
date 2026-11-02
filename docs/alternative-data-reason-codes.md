# Alternative-data reason-code contract

These codes are stable machine identities. User text may be localized, but code
meaning, trigger, and disposition cannot change within a schema version. A
record or entity may carry multiple codes; excluded totals are de-duplicated.
Codes never encode a credit outcome, decision, legal conclusion, or consumer
blame.

The exact sentence in each table's `Trigger` column is also the canonical
English message, with the leading article retained and terminal period as
shown. Implementations store that fixed message; they do not interpolate source,
provider, entity, record, category, or field values into it.

Disposition meanings:

- `error`: reject the run because safe interpretation is impossible;
- `exclude`: omit only the affected record from the stated calculation and
  preserve its count;
- `unavailable`: retain the entity/period in the population and mark the
  measure unavailable, never zero or adverse; and
- `observe`: retain the evidence and emit a typed quality observation.

## Structural and provenance codes

| Code | Default | Trigger |
|---|---|---|
| `ad_missing_required_field` | error | A conditionally required field is absent. |
| `ad_unknown_field` | error | Strict domain input contains an undeclared field. |
| `ad_duplicate_record_identity` | error | Source/version contains the same record identity twice. |
| `ad_source_not_declared` | error | `source_id` does not resolve to a source contract. |
| `ad_source_family_mismatch` | error | Record family differs from its source family. |
| `ad_source_version_mismatch` | error | Record and declared interpretation versions differ. |
| `ad_unsupported_event_type` | error | Event type is outside the exact family vocabulary. |
| `ad_invalid_identifier` | error | Required opaque identifier is blank or malformed. |
| `ad_permission_reference_unavailable` | error | Source lacks the required governance reference. |

## Time and leakage codes

| Code | Default | Trigger |
|---|---|---|
| `ad_invalid_window_order` | error | Window boundaries violate their required ordering. |
| `ad_feature_performance_overlap` | error | Feature and performance windows overlap. |
| `ad_feature_after_decision` | error | Feature period or event ends after `as_of_time`. |
| `ad_observed_after_decision` | exclude | A pre-decision event version first became observable after `as_of_time`. |
| `ad_revision_after_decision` | exclude | A revision was first observable after `as_of_time`; the last eligible prior version remains authoritative. |
| `ad_outcome_not_post_decision` | error | Outcome evidence starts at or before `as_of_time`. |
| `ad_outcome_outside_window` | exclude | Outcome evidence falls outside the configured performance window. |
| `ad_label_immature` | unavailable | Execution precedes `label_maturity_time`. |
| `ad_unrecognized_outcome_label` | error | Mature outcome value is outside the explicit binary label mapping. |
| `ad_non_monotonic_history` | error | Revision/reversal chain moves backward, cycles, or targets a later record. |
| `ad_period_overlap` | observe | Same source/entity has overlapping asserted coverage periods. |
| `ad_temporal_gap` | observe | Declared cadence expects but does not observe a period. |
| `ad_future_timestamp` | error | Evidence claimed as observed or completed asserts knowledge after run execution; a future configured label-maturity date does not trigger this code. |

## Amount and linkage codes

| Code | Default | Trigger |
|---|---|---|
| `ad_invalid_amount` | error | Amount is non-decimal, non-finite, or violates event sign rules. |
| `ad_currency_missing` | error | Monetary record lacks currency. |
| `ad_currency_inconsistent` | exclude | Currency violates source policy and no explicit conversion contract exists. |
| `ad_revision_target_missing` | error | `revision_of` target does not exist in the same source history. |
| `ad_reversal_target_missing` | error | `reversal_of` target does not exist in the same source history. |
| `ad_linkage_family_mismatch` | error | Revision, reversal, payment, or obligation link crosses entity, source, family, or currency. |
| `ad_unmatched_obligation` | unavailable | Rent/utility payment cannot resolve its explicit obligation. |
| `ad_uncertain_transfer` | observe | Cash-flow transfer scope is uncertain; it is excluded from income/spending totals. |

## Coverage and availability codes

| Code | Default | Trigger |
|---|---|---|
| `ad_signal_not_provided` | unavailable | Entity has no supplied source for the family. |
| `ad_provider_reporting_gap` | unavailable | Source explicitly reports a provider/period gap. |
| `ad_obligation_schedule_unavailable` | unavailable | Rent schedule is absent, so timeliness/nonpayment measures cannot be computed. |
| `ad_due_date_unavailable` | unavailable | An obligation lacks usable due-date evidence. |
| `ad_balance_history_unavailable` | unavailable | Cash-flow records contain no eligible balance observations. |
| `ad_insufficient_calendar_coverage` | unavailable | Eligible coverage is shorter than the configured minimum. |
| `ad_coverage_stratum_unavailable` | unavailable | User did not supply valid traditional-credit coverage evidence. |
| `ad_provider_nonparticipation` | unavailable | Provider/landlord does not supply the relevant period. |
| `ad_pending_record` | unavailable | Record is pending at `as_of_time` and cannot enter behavior totals. |
| `ad_small_group` | observe | Group support is below the configured reliability minimum. |
| `ad_sparse_report_cell` | unavailable | Distinct-entity count is below the configured disclosure minimum. |
| `ad_complementary_suppression` | unavailable | An additional cell is hidden to prevent recovery of a sparse value. |
| `ad_insufficient_fold_support` | unavailable | Proxy-screening folds do not meet configured entity and class support. |
| `ad_high_cardinality_unsupported` | unavailable | Candidate categories exceed the configured supported maximum after rare-level mapping. |
| `ad_proxy_model_nonconvergence` | unavailable | The versioned proxy-screening model did not converge. |
| `ad_proxy_holdout_unstable` | observe | Temporal-holdout evidence exceeds the configured stability tolerance. |
| `ad_proxy_strata_not_comparable` | unavailable | Provider or coverage stability lacks at least two nonempty supported strata in both development and holdout. |
| `ad_proxy_stratum_support` | unavailable | A required provider or coverage stratum lacks configured entity, class, or bootstrap support. |
| `ad_proxy_stratum_unstable` | observe | Supported provider or coverage evidence exceeds the configured stability tolerance. |

## Proxy-screening boundary codes

| Code | Default | Trigger |
|---|---|---|
| `ad_proxy_weighting_unsupported` | error | Proxy-screening configuration requests weighted eligibility, fitting, metrics, bootstrap, or suppression. |
| `ad_proxy_candidate_prohibited` | error | A candidate or baseline field is protected-derived, outcome, decision, post-decision, identifier, free text, exact geolocation, fold, weight, provider key, leakage-rejected, or otherwise prohibited by the proxy contract. |
| `ad_proxy_entity_conflict` | error | One proxy-screening entity has conflicting protected, candidate, baseline, provider, coverage, or reducer values after authoritative reduction. |
| `ad_proxy_window_conflict` | error | Proxy-screening development and temporal-holdout windows are not strictly forward and non-overlapping. |
| `ad_proxy_isolation_failure` | error | An entity, fitted transform, category vocabulary, or target-derived value crosses a proxy-screening fold or development/holdout boundary. |
| `ad_proxy_protected_missing` | exclude | An entity lacks the user-supplied protected attribute required by this proxy screen. |
| `ad_proxy_statistic_undefined` | unavailable | A proxy statistic has no defined denominator, required class comparison, finite value, or corrected contingency dimension. |
| `ad_proxy_paired_population_mismatch` | error | Baseline and baseline-plus-candidate proxy evidence do not contain the exact same canonically ordered entity population. |

These mappings are exhaustive for the named AD-4 boundary failures. They are
asserted before generic validation codes: a forbidden candidate cannot become
`ad_unknown_field`, an entity/window conflict cannot become an unavailable
metric, and a paired-population mismatch cannot be silently intersected. The
canonical message is exactly the Trigger sentence in this table, with no field,
entity, provider, protected label, or source value interpolated.

`ad_signal_not_provided`, `ad_provider_nonparticipation`, and
`ad_provider_reporting_gap` are availability facts. They must not increment a
late, missed, delinquent, adverse, or unfavorable numerator and must not be
imputed as zero-valued behavior.

## Family quality codes

| Code | Default | Trigger |
|---|---|---|
| `ad_cashflow_reversal_observed` | observe | Eligible cash-flow event has an explicit reversal. |
| `ad_cashflow_category_unresolved` | observe | Category is absent or unresolved; record stays outside category-specific measures. |
| `ad_rent_partial_payment_observed` | observe | Explicit linked partial rent payment exists. |
| `ad_rent_waiver_observed` | observe | Explicit waiver changes the obligation denominator under the configured policy. |
| `ad_utility_estimated_bill_observed` | observe | Bill is explicitly estimated. |
| `ad_utility_adjustment_observed` | observe | Linked adjustment changes an obligation amount. |
| `ad_service_interruption_observed` | observe | Explicit service interruption exists; no credit interpretation is attached. |

## Serialization and extension

Evidence records contain `code`, `disposition`, `scope`, `count`, source/family
references, affected window, and a canonical neutral message. They contain no
raw entity or record IDs. New codes are additive; changing an existing trigger
or disposition requires schema-version review and migration notes. Adapters may
not create source-specific codes by concatenating provider or category values.
