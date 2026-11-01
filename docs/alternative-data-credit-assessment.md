# Milestone 5 — alternative-data credit assessment

Status: active architecture contract; implementation is not yet a released
capability.

## Purpose

Extend FairLendKit with reproducible validation, credit-risk performance, and
fairness evidence for alternative-data signals used to assess consumers with
limited traditional credit-file coverage. The first supported signal families
are cash flow, rent, and utility payments.

The toolkit evaluates data and model evidence. It does not approve applicants,
train or recommend a production underwriting model, infer protected attributes,
declare a feature lawful or unlawful, or replace model-risk, compliance, legal,
privacy, or consumer-protection review.

## Analytical units and time contract

Alternative-data analysis is longitudinal. Every run must explicitly declare:

- a pseudonymous `entity_id` and unique source-record identity;
- signal family and source/provider identity;
- event or statement period, observation timestamp, and analysis `as_of_time`;
- feature lookback start and end, outcome-performance start and end, and label
  maturity rule;
- currency and amount semantics where monetary values are present; and
- population eligibility, traditional-credit-coverage stratum, protected
  attributes used only for audit, and optional weights.

Feature evidence must end no later than the analysis decision time. Outcome
evidence must begin after that time. Overlapping windows, future-observed source
records, revised records observed only after the decision time, immature labels,
and non-monotonic event histories fail closed or are explicitly excluded with
stable reason codes. The library never converts missing signal coverage into an
unfavorable credit outcome or decision.

## Canonical input boundary

The domain owns framework-neutral contracts for:

- `AlternativeDataSource`: signal family, provider, acquisition method,
  permission/legal-basis reference, coverage dates, refresh cadence, timezone,
  currency policy, and source version;
- `ObservationWindow`: decision time, lookback, performance window, and label
  maturity;
- `SignalRecord`: entity, record identity, signal family, event/period times,
  observed time, amount and currency when applicable, normalized event type,
  status, source version, and revision/reversal linkage; and
- `CreditCoverage`: declared traditional-credit coverage stratum using a
  user-supplied, documented definition. FairLendKit does not infer “thin-file”
  or “credit invisible” status.

Concrete dataframe adapters parse these records but cannot invent categories,
impute missing events, reinterpret an amount, choose an audit population, or
define consumer coverage status.

The normative field-level types, conditional requirements, family vocabularies,
and report-safe projection are defined in the
[alternative-data field dictionary](alternative-data-field-dictionary.md).

Raw transaction descriptions, account numbers, addresses, meter identifiers,
and other direct identifiers are not required by the analytical contract and
must not appear in report artifacts. Reports retain aggregate evidence and
source/provenance references only.

### Disclosure suppression

`minimum_report_cell_count` is required and must be at least `10`. It applies to
raw distinct-entity counts, regardless of weights. Any group, intersection,
provider, coverage-stratum, score-band, or proxy cell below the threshold is
serialized with `state="suppressed"`, null value/numerator/denominator/interval,
and reason `ad_sparse_report_cell`; only the bucket
`0..minimum_report_cell_count-1` is exposed, not the exact count.

If totals and remaining cells could reveal a suppressed value by subtraction,
the smallest otherwise publishable sibling is also suppressed with
`ad_complementary_suppression`; ties use canonical group order. Suppression is
applied to canonical JSON before CSV/HTML rendering, so no renderer has access
to the hidden values. Suppressed evidence cannot create a screening flag or a
reliability pass. Internal calculation may support testing but must not be
logged, placed in exceptions, fingerprints, or report metadata.

## Common data-quality evidence

Each signal family reports, overall and by declared credit-coverage and audit
group where support permits:

- entity and record counts, observation duration, freshness, and refresh lag;
- missing required fields, duplicate identities, revisions, reversals, and
  conflicting records;
- temporal gaps, period overlaps, future timestamps, and window leakage;
- provider/source coverage, source-version changes, and unsupported categories;
- currency consistency, non-finite/invalid amounts, and documented outliers;
- eligible, excluded, and unavailable counts with stable reason codes; and
- coverage, missingness, and exclusion-rate differences between groups.

Quality checks describe observed evidence. They do not assert that an absent
payment occurred, that a consumer was delinquent, or that data are fit for a
particular lending use.

All validation and availability evidence uses the closed
[alternative-data reason-code contract](alternative-data-reason-codes.md).

## Signal-family profiles

### Cash flow

The profile distinguishes inflow, outflow, balance observation, fee, reversal,
and transfer categories supplied by the source contract. It reports account and
calendar coverage, inflow/outflow totals, net cash flow, balance availability,
volatility and concentration, recurring-pattern support, negative-balance or
fee-event counts when explicitly provided, reversals, and missing periods.

Internal transfers and uncertain transaction categories remain separately
identified; they are never silently treated as income or spending. Income
stability or recurring-income measures require a versioned recurrence rule and
must expose the contributing periods and unavailable state.

### Rent

The profile requires an explicit obligation schedule or states that on-time and
missed-payment measures are unavailable. It distinguishes obligation, payment,
partial payment, adjustment, reversal, waiver, and unavailable reporting. It
reports schedule coverage, amount coverage, timing relative to documented due
dates and grace rules, partial-payment behavior, reversals, and reporting gaps.

No record means “not observed,” not unpaid. Provider or landlord nonparticipation
must remain distinguishable from consumer payment behavior.

### Utilities

The profile distinguishes bill, payment, partial payment, adjustment, reversal,
estimated bill, service interruption, and unavailable reporting. It reports
provider and service-type coverage, billing-period continuity, due-date support,
payment timing, partial payments, adjustments, estimated-bill prevalence,
seasonality support, and reporting gaps.

Service interruption, geographic availability, household composition, climate,
provider practices, subsidies, and billing cadence are potential context or
proxy pathways; the toolkit does not interpret them as consumer creditworthiness.

The three profiles are fixed by independently reproducible
[hand-calculated examples](alternative-data-hand-calculated-examples.md). These
examples define denominators and unavailable states as well as arithmetic.

## Credit-risk performance

Risk evaluation consumes a user-supplied score or model prediction and a mature,
explicitly defined observed outcome. It reuses existing AUC, Brier score,
accuracy, error-rate, uncertainty, and reliability contracts and adds, under
separate reviewed metric contracts:

- score-band count and observed bad/outcome rate;
- calibration-in-the-large and calibration slope when estimable;
- KS and Gini with direction and weighting semantics fixed;
- lift/capture at explicitly configured population fractions; and
- performance by signal availability, credit-coverage stratum, provider, and
  protected group where sample and label support are reliable.

The report records outcome definition, observation/performance windows, label
maturity, censoring/unavailable counts, and population denominators. It does not
compare models trained on different populations without an explicit compatible
evaluation population.

The normative [alternative-data credit-risk metric contract](alternative-data-risk-metrics.md)
fixes applicability, direction, weighting, ties, formulas, and gates. AD-3 must
not begin until that independent contract is approved.

## Fairness and coverage analysis

Fairness evidence covers three distinct stages and never collapses them:

1. **Data access and coverage:** signal availability, observation duration,
   missingness, exclusion, provider coverage, and usable-feature rates.
2. **Risk performance:** score distribution, calibration, ranking, error, and
   reliability differences on a common eligible evaluation population.
3. **Decision outcomes:** existing selection and error disparities only when an
   explicit observed or configured decision is present.

Results are stratified by user-declared traditional-credit coverage so that an
aggregate result cannot hide lack of support for limited-file consumers.
Intersectional analysis is allowed only through explicitly configured groups;
small or sparse cells remain visible as unreliable or undefined rather than
being silently pooled.

## Potential proxy-risk screening

Proxy screening is exploratory evidence, not a causation, intent, legality, or
feature-removal decision. Candidate features must be explicitly configured and
screened only after eligibility and leakage checks.

The first contract must include:

- univariate association appropriate to feature type, with missingness treated
  as a separate state rather than silently imputed;
- protected-group predictability evaluated out of sample against a declared
  baseline, with deterministic folds and uncertainty;
- incremental predictability when a documented baseline feature set is
  supplied;
- stability across providers, time periods, and credit-coverage strata; and
- traceable screening flags whose rules, thresholds, supporting evidence,
  limitations, and human review prompts are versioned.

No single association statistic is labeled a proxy verdict. Features derived
from geography, service availability, payment channel, household context, or
provider identity require explicit contextual limitations.

The normative [potential proxy-risk screening contract](alternative-data-proxy-screening.md)
fixes candidate exclusions, entity/time isolation, baselines, metrics,
thresholds, folds, high-cardinality behavior, and flags. AD-4 proxy work must
not begin until that independent contract is approved.

## Result and reporting boundary

Alternative-data results are a new versioned section of the typed audit result.
JSON is canonical; CSV and HTML render the same typed evidence without
recalculation. Reports separate source quality, signal profile, risk performance,
coverage fairness, proxy screening, limitations, and review prompts.

Every value links to population, time window, source identity/version, metric or
check definition, numerator/denominator where applicable, reliability state,
and limitation codes. Raw consumer-level records and direct identifiers never
appear in generated artifacts.

## Delivery slices

0. **AD-D0 — source discovery and admission:** candidate inventory, provenance,
   license/redistribution matrix, signal/outcome/time coverage, privacy and
   representation review, and `repository` / `external_only` / `reject`
   decisions under the
   [data-source admission contract](alternative-data-source-admission.md). No
   external data or downloader enters the repository before approval.
1. **AD-0 — contracts and leakage gate:** domain models, time windows,
   provenance, coverage strata, reason codes, privacy boundary, and fixtures.
2. **AD-1 — common quality engine:** eligibility, temporal integrity,
   completeness, source coverage, exclusions, and grouped quality evidence.
3. **AD-2 — signal profiles:** cash-flow, rent, and utility adapters and typed
   family-specific profiles with hand-calculated fixtures.
4. **AD-3 — credit-risk diagnostics:** mature-label evaluation, score bands,
   calibration, KS/Gini, lift/capture, uncertainty, and subgroup reliability.
5. **AD-4 — coverage fairness and proxy screening:** staged fairness evidence,
   association and out-of-sample predictability, stability, flags, and limits.
6. **AD-5 — workflow and release gate:** public API, CLI, JSON/CSV/HTML,
   synthetic end-to-end examples for all three families, documentation,
   architecture checks, privacy tests, golden artifacts, and Python 3.11/3.12
   CI with independent review.

Threshold scanning, mitigation, feature selection, model training, reject
inference, and production decisioning are outside AD-0 through AD-5.

## Definition of done

- Missing coverage is never converted into negative behavior or outcome.
- No post-decision information can enter a feature profile.
- Every family-specific measure has explicit availability prerequisites and a
  hand-calculated fixture.
- Group results preserve denominators, exclusions, reliability, uncertainty,
  and direction.
- Proxy flags expose reproducible rules and never state a legal conclusion.
- Synthetic examples include limited-file, no-signal, provider-gap, reversal,
  immature-label, sparse-group, and time-leakage cases.
- All formats derive from one typed result and contain no raw identifiers.
- Independent review and both supported Python runtimes pass before release.
