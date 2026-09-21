# Product Requirements

## Mission

Provide a reproducible, credit-specific audit workflow that connects model scores to lending decisions, observed disparities, threshold sensitivity, potential proxy-risk indicators, and review-ready evidence.

The [canonical glossary](glossary.md) defines the normative vocabulary used by requirements, configuration, reports, examples, and papers.

## Primary users

- Fintech and lending model-risk teams
- Fair-lending and compliance practitioners
- Credit unions and lending startups
- Academic researchers studying responsible underwriting

## Review roles and decision ownership

FairLendKit supports a cross-functional review; it does not assign an automated
verdict to any one team. Reports must distinguish the following responsibilities:

- Model Risk evaluates methodology, performance, assumptions, limitations, and
  whether further model investigation is warranted.
- Compliance and Fair Lending evaluate the relevant compliance risk, review
  methodology and group definitions, and determine escalation needs with counsel.
- Data Science and Analytics prepare and validate data, reproduce calculations,
  and investigate unexpected results.
- Business, Product, and Credit owners supply policy, decision-process, and
  operational context and own approved business actions.
- Audit, Controls, and Governance preserve evidence, track findings and
  remediation, and support management reporting.

The toolkit provides evidence and screening prompts. The designated business or
control owner remains accountable for investigation, decisions, remediation,
and monitoring.

## Canonical workflow

1. Validate data and audit configuration.
2. Evaluate overall model performance.
3. Measure group selection and outcome disparities.
4. Measure group error and calibration disparities.
5. Scan decision thresholds and construct a fairness-accuracy frontier.
6. Screen candidate features for potential proxy-risk indicators.
7. Generate reproducible reports with uncertainty and limitations.
8. Route each screening flag through a review lifecycle: analytical finding,
   risk assessment, investigation, decision, and remediation or monitoring.

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

The HTML report must provide both an executive summary and reviewer detail. The
summary answers: what was analyzed, what was found, and what a reviewer should
consider next. Detailed sections preserve group counts, comparison bases,
uncertainty, missingness, threshold sensitivity, limitations, and metric
definitions.

Screening flags use transparent, versioned rules and distinguish at least:

- invalid input;
- material data-quality concern;
- insufficient sample or unreliable result;
- undefined metric;
- notable observed difference;
- threshold-sensitive result; and
- additional investigation recommended.

Flags are prompts for human review, not automated compliance conclusions.

## Practitioner follow-up workflow

For every notable finding, the report should present applicable, non-prescriptive
review prompts: document no further action and rationale; validate data; review
business rules or controls; investigate the model, threshold, or features;
escalate to the appropriate owner; or establish remediation and monitoring.
Reports must preserve the selected disposition, owner, rationale, and status when
supplied by downstream governance workflows. V1 does not make or enforce the
decision.

## V1 acceptance criteria

Given the versioned synthetic example, one documented CLI command must generate all required outputs deterministically. Unit tests must cover metric direction, reference-group behavior, missing data, small groups, zero denominators, sparse outcomes, unexpected categories, undefined metrics, and threshold boundaries. Golden tests must verify that executive, detailed, and machine-readable outputs derive from the same result model and that every flag exposes its rule, supporting evidence, and limitation.

## Non-goals

- Declaring a model compliant or non-compliant
- Providing legal advice
- Replacing fair-lending counsel or a complete model-risk process
- Processing proprietary Capital One data, models, code, or intellectual property
- Serving as a production loan-decision engine
- Inferring protected attributes for operational lending decisions
