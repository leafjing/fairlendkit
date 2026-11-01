# AD-D0 outcome and temporal-fitness contract

This contract determines whether a candidate can support credit-risk evaluation
or only data-quality/profile research. It does not transform a convenient label
into a credit outcome.

## Required outcome record

For every proposed outcome, document:

- stable `outcome_id` and definition version;
- exact publisher field(s) and allowed raw categories;
- event being measured, responsible product/obligation, and unit of observation;
- favorable and unfavorable meanings without collapsing unknown categories;
- outcome source and collection method;
- decision/index time available to the study;
- performance-window start and end;
- minimum follow-up and label-maturity time;
- censoring, attrition, missing, pending, disputed, cured, restructured, and
  unknown states;
- whether revisions are published and when each version became observable;
- population eligible for the label; and
- known measurement, selection, and survivorship limitations.

Raw categories map only to one of `favorable`, `unfavorable`, `censored`,
`pending`, `unknown`, or `invalid`. The mapping is explicit and versioned.
`censored`, `pending`, and `unknown` never become favorable or unfavorable.

## Credit-outcome admission

An outcome is eligible for AD-3 only when it is an observed, mature result of a
documented credit obligation or performance definition and both classes are
unambiguous. Examples may include publisher-defined loan repayment/default or
delinquency at a stated horizon. The contract does not decide legal or business
appropriateness; human reviewers do.

The following do not become loan default or credit performance merely by
renaming:

- rent or utility arrears, late bills, partial payments, hardship, waiver,
  service interruption, or provider nonparticipation;
- low balance, overdraft, fee, income volatility, cash-flow gap, or missing bank
  account coverage;
- survey responses, financial stress, benefit receipt, or household hardship;
- absence from a dataset, loss to follow-up, or an unavailable provider; and
- a score, model prediction, collection flag, or downstream decision.

These may be signal/context fields or separately named outcomes for descriptive
research if the publisher defines them, but reports must retain that meaning and
must not claim credit-default performance.

## Temporal truth record

For each candidate, complete this evidence table from official documentation:

| Boundary | Exact field/source | Inclusive rule | Availability evidence |
|---|---|---|---|
| Feature start |  |  |  |
| Feature end |  |  |  |
| Decision/index time |  |  |  |
| Outcome start |  |  |  |
| Outcome end |  |  |  |
| Label maturity |  |  |  |
| Record observed/revision time |  |  |  |

Risk use requires `feature_end <= decision_time < outcome_start <= outcome_end`
and execution at or after label maturity. Event time without observation or
release time is insufficient when retrospective corrections could leak future
knowledge. If the official data cannot establish the ordering, disposition is
`quality_only`, never “assumed leakage-free.”

## Decision classes

- `risk_eligible`: exact outcome mapping, mature binary classes, censoring,
  decision/index time, feature window, performance window, and observation-time
  semantics are all verified.
- `quality_only`: signal data is documented and lawfully usable, but outcome or
  temporal separation is absent, ambiguous, immature, or non-credit.
- `ineligible`: provenance, permission, privacy, integrity, or semantics fail.

The decision is source-version-specific. Combining one dataset's signals with a
different dataset's outcome is prohibited unless an authorized common cohort
and entity linkage are supplied by the original source, documented in one
approved manifest, and separately privacy-reviewed. Similar distributions or
shared column names are never linkage evidence.

## Review evidence

The candidate record cites the exact data dictionary, methodology, codebook,
license, and version supporting every mapping. Reviewer sign-off records both
approved and prohibited claims. A later paper may not broaden the outcome
meaning beyond this record without re-review.
