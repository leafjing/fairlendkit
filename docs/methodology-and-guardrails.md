# Methodology and Guardrails

## Interpretation boundary

FairLendKit reports observed statistical evidence for practitioner review. It does not determine causation, intent, business necessity, less-discriminatory alternatives, or legal compliance.

## Four-fifths rule

The four-fifths rule originates in the U.S. employment-selection
[Uniform Guidelines on Employee Selection
Procedures](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607).
The EEOC characterizes it as a [rule of thumb, not a legal
definition](https://www.eeoc.gov/laws/guidance/questions-and-answers-clarify-and-provide-common-interpretation-uniform-guidelines#q12).
FairLendKit does not treat that employment rule as a universal credit-law
threshold.

In a credit audit, the configurable AIR `0.8` threshold is only a
reliability-gated screening signal. A flag is not a finding of discrimination,
illegality, or non-compliance. A ratio at or above `0.8`, or no emitted flag, is
not proof of fairness, compliance, legality, or a safe harbor. The threshold
must not be described as a pass/fail rule.

Reviewers must examine both selection rates, group denominators, absolute rate
difference or another effect size, confidence intervals or documented
uncertainty, missing/excluded records, and reliability limitations. Where the
data support it, interpretation also considers preregistered conditional or
risk-adjusted comparisons, overlap diagnostics, and sensitivity analyses.
These remain associational and must be followed by accountable human review;
they do not establish cause, intent, business necessity, or a legal conclusion.

## Proxy-risk screening

Correlation, Cramer's V, mutual information, and protected-class predictability can identify statistical association. They do not establish that a feature is an unlawful proxy or that its use caused disparate treatment or disparate impact.

Proxy-screening outputs must be labeled `potential proxy-risk indicators`. High/medium/low labels require documented, configurable thresholds and must never be presented as legal conclusions.

## Label and score semantics

Credit datasets commonly encode default as `1`, while lending decisions encode approval as `1`. Every audit must explicitly set:

- Favorable outcome
- Score direction
- Decision meaning
- Reference group

The run must fail validation when these semantics are missing or inconsistent.

## Statistical reliability

- Report the sample count for every group and metric.
- Warn or suppress comparisons below a configurable minimum group size.
- Include confidence intervals for key disparity measures.
- Distinguish undefined metrics from zero-valued metrics.
- Document missing-data handling and excluded records.
- Support intersectional groups, while applying the same sample-size safeguards.

## Mitigation boundary

Mitigation is V1.1. Group-specific decision thresholds can create material legal, ethical, and operational risks. Any future implementation must default to offline simulation, document assumptions, and avoid recommending automatic production deployment.

## Data and intellectual property

Only public, properly licensed, or synthetic data may be committed. No Capital One internal data, derived confidential data, model artifacts, code, documentation, or other proprietary information may be used.

HMDA examples must disclose dataset limitations and must not imply that HMDA alone represents a complete underwriting model or causal analysis.

## Report language

Reports separate:

1. Observed metrics
2. Screening flags
3. Statistical uncertainty
4. Data and methodological limitations
5. Practitioner review notes

The terms `compliant`, `non-compliant`, `legal`, and `illegal` must not be generated as automated conclusions.

## Findings and follow-up

FairLendKit must keep the following stages distinct:

1. Analytical finding: a reproducible observation or validation result.
2. Risk assessment: human evaluation of severity, likelihood, scope, and context.
3. Investigation: data, control, business-rule, model, threshold, or feature review.
4. Decision: an accountable owner determines the disposition and rationale.
5. Remediation or monitoring: approved action, tracking, and subsequent review.

The report may suggest relevant investigation categories, but it must not claim
that an observed disparity identifies its cause. A reviewer may conclude that no
further action is warranted, provided the rationale and evidence are documented.

Flag thresholds must be configurable or normatively documented, versioned, and
shown with the supporting values. Arbitrary or undisclosed red/amber/green logic
is prohibited.

## Audience layers

Executive summaries communicate scope, population, key observations, data-quality
concerns, follow-up areas, and important limitations without omitting uncertainty.
Reviewer detail includes counts, definitions, comparison groups, thresholds,
confidence intervals, exclusions, warnings, and reproducibility metadata. The two
layers must be generated from the same typed result and cannot make conflicting
claims.
