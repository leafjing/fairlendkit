# Methodology and Guardrails

## Interpretation boundary

FairLendKit reports observed statistical evidence for practitioner review. It does not determine causation, intent, business necessity, less-discriminatory alternatives, or legal compliance.

## Four-fifths rule

The adverse impact ratio and four-fifths rule are screening heuristics. Crossing a threshold is neither proof of unlawful discrimination nor proof of compliance. Reports must display underlying selection rates, group sample sizes, uncertainty, and limitations alongside the ratio.

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

