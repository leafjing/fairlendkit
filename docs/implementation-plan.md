# V1 Implementation Plan

This plan turns the product requirements into ordered, independently testable
work packages. Work proceeds in sequence unless an earlier contract exposes a
dependency that must be resolved first.

## Delivery rule

Every work package is complete only when its public contract, implementation,
tests, user documentation, edge cases, and limitations agree. Each package must
leave the test suite green and machine-readable outputs backward-compatible or
explicitly versioned.

Every package also passes an architecture check: volatile details depend on
stable abstractions, concrete adapters depend on inner-layer protocols, and no
domain or use-case module imports an outer implementation. Composition belongs
at an application entry point. Abstractions are introduced for demonstrated
variation or test seams, not for hypothetical flexibility.

## Epic 1 — Input and semantic validation

### 1.1 Run context contract

- Record population and sampling definition.
- Record dataset and model version or explicitly record that either is unavailable.
- Record whether the score is a probability or ranking score.
- Record extraction/as-of time separately from execution time.
- Acceptance: invalid or ambiguous run context fails before metric calculation.

### 1.2 Group and unknown-value semantics

- Declare a non-empty, type-sensitive allowed-category set for every protected
  attribute; configuration keys must exactly match the protected attributes.
- Treat missing values (null/NA) separately from unknown values (non-null values
  outside the allowed-category set), with an explicit `error` or `exclude`
  policy for each condition. Neither condition may be folded into an allowed
  group.
- Verify every reference group is allowed at configuration time and present
  after all row-eligibility rules have been applied.
- When exclusion is configured, preserve the input and emit stable reason codes,
  per-reason row counts, and the de-duplicated total excluded-row count.
- Acceptance: no category is inferred, coerced, folded, or silently excluded;
  type-distinct values remain distinct, every exclusion is auditable, and a
  reference group absent from eligible data fails before analysis.

### 1.3 Structural integrity

- Declare duplicate-record policy and optional stable record identifier.
- Validate required columns, types, finite values, configured ranges, and expected
  categories.
- Acceptance: every excluded or rejected row has a stable reason code and count;
  rows matching multiple reasons contribute once to the total excluded count and
  once to each applicable reason count.

### 1.4 Layered validation result

- Separate structural validity, semantic validity, analytical reliability, and
  data-quality observations.
- Preserve stable codes, affected fields/groups, severity, evidence, and message.
- Acceptance: a technical pass is never represented as fitness-for-use approval.

## Epic 2 — Data-quality observations

### 2.1 Single-run profile

- Report missingness overall and by group, group sizes, unexpected categories,
  score/outcome distributions, outliers, and data freshness.

### 2.2 Baseline comparison

- Compare group composition, missingness, distributions, and model/dataset
  versions against an explicitly selected prior run or baseline.
- Acceptance: every change flag exposes its statistic, threshold, and baseline.

## Epic 3 — Core metrics and reliability

### 3.1 Metric applicability contract

- Document inputs, formula, direction, assumptions, undefined states, and
  interpretation limits for every metric.

### 3.2 Core metric set

- Implement outcome/selection rates, group comparisons, performance and error
  rates, calibration measures, counts, and configured uncertainty.

### 3.3 Edge-case behavior

- Handle small groups, imbalance, sparse outcomes, zero denominators, invalid
  inputs, and undefined or unreliable estimates without manufacturing numbers.

## Epic 4 — Threshold sensitivity

### 4.1 Threshold scan

- Evaluate decision, performance, error, and disparity measures across a declared
  threshold grid using the configured score direction.

### 4.2 Frontier and sensitivity flags

- Produce the fairness-accuracy frontier and identify conclusions that materially
  depend on the selected threshold.

## Epic 5 — Reporting, flags, and audit trail

### 5.1 Typed result and flag model

- Define stable result sections and transparent flag rules with supporting
  evidence, limitations, and review prompts.

### 5.2 Audience-specific views

- Generate an executive summary, reviewer detail, visualizations, JSON, and CSV
  from the same typed result without recomputation.

### 5.3 Reproducibility record

- Preserve configuration, fingerprints, versions, timestamps, metric definitions,
  validation results, exclusions, warnings, and output schema version.

## Epic 6 — Human review lifecycle

### 6.1 Investigation prompts

- Map findings to non-prescriptive data, business-rule, control, model, feature,
  threshold, escalation, remediation, and monitoring review categories.

### 6.2 Governance integration contract

- Import/export owner, status, rationale, evidence references, decision, and
  timestamps without mixing human dispositions into computed results.

## Epic 7 — End-to-end evidence and release

### 7.1 Synthetic reference audit

- Ship a deterministic example covering normal results, warnings, undefined
  metrics, threshold sensitivity, and documented follow-up reasoning.

### 7.2 Public-data case study

- Document population, data rights, transformations, missingness, limitations,
  and appropriate interpretation.

### 7.3 Release gate

- Require unit, property, contract, golden-file, and CLI integration tests;
  synchronized documentation; citation metadata; and security/methodology review.

## Dependency order

```text
Epic 1 -> Epic 2 -> Epic 3 -> Epic 4 -> Epic 5 -> Epic 6 -> Epic 7
                  \---------------------> Epic 5
```

Reporting design may be prototyped earlier, but its public schema is not final
until validation, metrics, and threshold contracts are stable.
