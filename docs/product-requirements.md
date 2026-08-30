# Product Requirements

## Mission

Provide a reproducible, credit-specific audit workflow that connects model scores to lending decisions, observed disparities, threshold sensitivity, potential proxy-risk indicators, and review-ready evidence.

The [canonical glossary](glossary.md) defines the normative vocabulary used by requirements, configuration, reports, examples, and papers.

## Primary users

- Fintech and lending model-risk teams
- Fair-lending and compliance practitioners
- Credit unions and lending startups
- Academic researchers studying responsible underwriting

## Canonical workflow

1. Validate data and audit configuration.
2. Evaluate overall model performance.
3. Measure group selection and outcome disparities.
4. Measure group error and calibration disparities.
5. Scan decision thresholds and construct a fairness-accuracy frontier.
6. Screen candidate features for potential proxy-risk indicators.
7. Generate reproducible reports with uncertainty and limitations.

Mitigation and re-audit are deferred to V1.1.

## Required inputs

- Observed outcome (`y_true`)
- Model score (`y_score`)
- Protected attribute used to form audit groups
- Explicit reference group
- Explicit favorable outcome and score direction
- Explicit favorable decision meaning
- Optional observed decision and candidate features for proxy-risk screening

The configuration must define label semantics. FairLendKit must never infer whether a larger score represents higher creditworthiness or higher default risk.

## V1 outputs

- `audit.html`: human-readable review report
- `audit.json`: machine-readable report and metadata
- `metrics.csv`: overall and group metrics
- `threshold_frontier.csv`: threshold sensitivity results
- Run metadata: input fingerprint, configuration, package version, timestamp, and warnings

## V1 acceptance criteria

Given the versioned synthetic example, one documented CLI command must generate all required outputs deterministically. Unit tests must cover metric direction, reference-group behavior, missing data, small groups, and threshold boundaries.

## Non-goals

- Declaring a model compliant or non-compliant
- Providing legal advice
- Replacing fair-lending counsel or a complete model-risk process
- Processing proprietary Capital One data, models, code, or intellectual property
- Serving as a production loan-decision engine
- Inferring protected attributes for operational lending decisions
