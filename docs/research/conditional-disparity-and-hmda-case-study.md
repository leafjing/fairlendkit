# Conditional disparity and HMDA case-study contract

Status: `design_only / no_results`

This document freezes the research questions, analysis stages, cohort rules,
interpretation boundaries, and reproducibility evidence for a conditional
disparity study and a 2024 HMDA case study. It does not report findings,
identify causes, determine discrimination, or state a legal conclusion.

The public-data cohort follows the authoritative rules in
[Paper 2 experiment protocol](../paper-2-experiment-protocol.md#primary-candidate-2024-hmda-snapshot).
If a later reviewed protocol changes those rules, this contract must be
versioned and reviewed before any result is regenerated.

## 1. Research questions

The study asks four bounded questions:

1. What unadjusted differences in favorable action rates are observed between
   prespecified groups in the frozen cohort?
2. How do those differences change after prespecified stratification and
   regression adjustment using observed, pre-decision covariates?
3. Are adjusted comparisons supported by adequate covariate overlap, sample
   size, and stable estimates?
4. How sensitive are the descriptive conclusions to cohort, missing-data,
   outcome-mapping, geography, time, and model-specification choices?

The study does **not** ask which factor caused a disparity. A change after
adjustment is a conditional association under stated assumptions, not a
decomposition of intent, business necessity, underwriting quality, or unlawful
discrimination.

## 2. Estimands and reporting order

Every result artifact must keep the following estimands separate:

- Unadjusted disparity: the difference and ratio of observed favorable-action
  rates in the frozen cohort.
- Standardized disparity: the group contrast after direct standardization over
  prespecified risk/covariate strata with common support.
- Regression-adjusted disparity: the average marginal contrast predicted from
  a prespecified model over the eligible common-support population.

For each estimand, report group denominators, favorable counts, rates, the
absolute difference, ratio where defined, confidence interval, excluded-row
count, missingness summary, and support diagnostics. Undefined estimates remain
undefined with a stable reason code; they must not be converted to zero.

Unadjusted results appear first. Adjusted results may supplement but never
replace them. The report must not describe an adjusted contrast as the
"explained" or "unexplained" share of discrimination.

## 3. Control-variable selection contract

The analysis plan must register every control before outcome analysis and give
each variable a role, source field, coding rule, missingness rule, and rationale.
Controls must satisfy all of the following:

- available at or before the application decision;
- defined consistently enough for the frozen cohort and period;
- plausibly related to the outcome or selection process without being selected
  only because it reduces the protected-group coefficient;
- not a post-decision event, denial reason, action-taken derivative, or other
  direct outcome leakage;
- not an unsupported proxy for an unavailable underwriting concept; and
- not silently recoded across years, geographies, or disclosure-avoidance
  regimes.

Protected attributes define comparison groups and are not treated as ordinary
"risk controls." Geography, lender, loan purpose, product, amount, income,
debt-to-income category, loan-to-value category, occupancy, property type, and
other available fields are candidates only after field-level review. Inclusion
does not assert that a variable is legitimate, causally prior, measured without
error, or sufficient for underwriting adjustment.

The preregistered control manifest must distinguish:

- core controls used in every adjusted specification;
- optional controls used only in named sensitivity analyses;
- variables excluded for leakage, semantic ambiguity, sparse support, excessive
  missingness, or prohibited interpretation; and
- unavailable concepts, including complete credit history, verified assets,
  lender model score, pricing exceptions, fraud indicators, and detailed
  underwriting judgment.

No stepwise selection, outcome-driven control removal, coefficient-sign hunting,
or unregistered interaction search is permitted in the primary analysis.

## 4. Conditional disparity analysis

### 4.1 Stratified standardization

The first adjusted analysis uses prespecified, coarsened strata. Exact stratum
keys, bin boundaries, reference population, minimum cell size, and pooling rules
must be frozen before results are inspected.

Within each supported stratum, compute group-specific favorable rates and their
contrast. Standardize the stratum contrasts to one declared target distribution.
Report how many rows and strata are excluded for lack of common support. Sparse
or one-group-only strata are not imputed into a favorable result.

### 4.2 Regression adjustment

The second adjusted analysis uses a preregistered binary-outcome model and
reports average marginal predictions and contrasts, not only a protected-group
coefficient. The model specification must freeze transformations, interactions,
regularization, cluster/stratum handling, convergence checks, and variance
estimation.

Model fit does not validate causal interpretation. Report calibration and
discrimination diagnostics only as model diagnostics; they do not establish
that the available controls are complete or legally appropriate.

### 4.3 Uncertainty and multiplicity

Primary contrasts use two-sided 95% confidence intervals with a declared
resampling or sandwich-variance method. Resampling units must respect any lender,
geographic, or repeated-record dependence assumed by the design. If multiple
protected dimensions, outcomes, or primary specifications are confirmatory, the
multiplicity family and adjustment method must be registered. Exploratory
results are labeled as such.

### 4.4 Overlap and estimability

Before adjusted results are interpreted, the artifact must report:

- group-specific covariate and propensity summaries;
- common-support bounds and retained/excluded counts;
- effective sample size where weighting is used;
- the largest standardized differences before and after adjustment;
- influential or high-leverage observations; and
- stable failure reasons for separation, non-convergence, empty cells,
  positivity violations, or insufficient support.

When overlap is inadequate, the result is limited to the supported population
or marked not estimable. Extrapolation must not be presented as a population
finding.

## 5. Sensitivity-analysis registry

The implementation must assign stable IDs and freeze parameters for at least
these analyses:

- `HMDA-SENS-ACTION-13`: originated (`1`) versus denied (`3`) only;
- `HMDA-SENS-MISSING-COMPLETE`: prespecified complete-case analysis;
- `HMDA-SENS-MISSING-CATEGORY`: explicit missing/unknown categories where
  semantically valid;
- `HMDA-SENS-CONTROL-CORE`: core controls only;
- `HMDA-SENS-CONTROL-EXTENDED`: reviewed optional controls added;
- `HMDA-SENS-BINS`: alternate preregistered coarsening boundaries;
- `HMDA-SENS-GEOGRAPHY`: statewide versus supported county strata;
- `HMDA-SENS-LENDER`: lender fixed/cluster structure where identifiers and
  support permit;
- `HMDA-SENS-OVERLAP`: alternate prespecified common-support restrictions; and
- `HMDA-SENS-YEAR`: an adjacent-year replication only after separate source and
  schema admission.

Each sensitivity result reports the same estimand, denominator, uncertainty,
support diagnostics, and exclusions as its primary counterpart. Direction or
sign changes, loss of estimability, and material interval widening must be
prominent; they may not be hidden in an appendix-only success summary.

## 6. HMDA 2024 case-study cohort

### 6.1 Source and freeze

- Official source: FFIEC/CFPB 2024 Snapshot National Loan-Level Dataset.
- Primary geography: complete California subset (`state_code=CA`).
- Unit: one eligible application record after deterministic cleaning.
- Raw person-level rows are not committed to Git.
- Before retrieval, the manifest records official URL, retrieval time,
  version/freeze date, terms or public-domain basis, byte size, SHA-256, schema
  digest, and redistribution boundary.

Mirrors and manually modified extracts are not acceptable source substitutes.

### 6.2 Primary sample rules

The primary cohort includes conventional, first-lien, home-purchase applications
for owner-occupied, one-unit dwellings. Exact official field codes must be copied
from the reviewed 2024 data dictionary into a checked-in rule table; prose alone
is not executable evidence.

Primary outcome mapping:

- favorable: action-taken `1` (originated) or `2` (approved but not accepted);
- unfavorable: action-taken `3` (denied);
- excluded from the primary decision contrast: all other action codes.

The `HMDA-SENS-ACTION-13` sensitivity retains only codes `1` and `3`.
Withdrawal, incompleteness, preapproval, purchased-loan, and other excluded
states must not be silently relabeled as denial or approval.

Deduplication, invalid-code handling, numeric parsing, range checks, and every
exclusion are deterministic and counted in a cohort flow artifact. The flow must
reconcile exactly from source rows to final analytical rows.

### 6.3 Group definitions

Race/ethnicity and sex use reviewed public-file fields and official combination
rules frozen before analysis. Primary analyses evaluate each protected dimension
separately. Intersectional analyses are exploratory and use the same support and
minimum-count safeguards.

Unknown, not provided, free-form, and not applicable values remain explicit in
the descriptive flow. Any exclusion or regrouping appears only in a named
sensitivity analysis. Reference-group selection is prespecified and must not be
changed to maximize or minimize a disparity.

### 6.4 Missing data and special values

The field manifest distinguishes structural not-applicable values, respondent
nonresponse, disclosure-avoidance recoding, invalid values, and ordinary
missingness. Special codes are never merged into generic nulls without a
field-specific rule.

Primary missing-data handling is specified per variable before modeling. No
single imputation is treated as observed truth. If multiple imputation is later
proposed, its model, predictors, number of imputations, pooling rule, diagnostics,
and compatibility with protected-group analysis require a separately reviewed
amendment.

### 6.5 Weights and geography

The snapshot is analyzed according to its official design and documentation;
the study must not invent survey weights. Statewide summaries may retain rows
without county. County-stratified analyses exclude missing county only from that
specific analysis and report the exclusion count.

## 7. Reproducible pipeline and evidence

The case study must produce, without committing row-level public data:

- source manifest and raw-file SHA-256;
- complete ordered schema and schema digest;
- executable cohort-rule table and code commit;
- cohort-flow counts and exclusion reason codes;
- control manifest and sensitivity registry;
- deterministic configuration, seed policy, command, environment, and input
  hashes;
- unadjusted, standardized, and regression-adjusted artifacts;
- confidence intervals, support diagnostics, convergence status, and stable
  undefined reasons;
- aggregate tables checked against minimum-cell and disclosure rules; and
- a data card recording permitted use, limitations, and non-claims.

Every published number must trace to one machine-readable artifact field and one
formula/version identifier. Manual spreadsheet edits are not an evidence path.

## 8. Interpretation and non-claims

The report must use language such as "observed disparity," "conditional
association," and "difference after adjustment." It must not claim that:

- a protected attribute, control variable, lender, model feature, or human rule
  caused the observed disparity;
- adjustment proves that a disparity is explained, justified, unjustified,
  discriminatory, compliant, legal, or illegal;
- HMDA contains complete underwriting information or a lender's decision model;
- an AIR threshold is a universal lending-law standard or safe harbor;
- a statistically insignificant result proves absence of a meaningful disparity;
  or
- results generalize beyond the frozen year, cohort, geography, support region,
  field definitions, and specifications.

Potential explanations—including risk distribution, income measurement, sample
selection, product mix, model features, lender rules, data quality, or
discrimination—remain hypotheses for accountable investigation. The analysis
may prioritize follow-up evidence but cannot adjudicate those explanations from
HMDA associations alone.

## 9. Review and implementation gate

This contract must pass methodology and independent review before implementation.
Implementation must fail closed when source identity, schema, cohort mapping,
control manifest, group semantics, overlap requirements, uncertainty method, or
sensitivity registry differs from the reviewed contract.

No result language is approved by this design document. Findings, if later
generated, require separate evidence review and must retain the non-causal and
non-legal boundaries above.
