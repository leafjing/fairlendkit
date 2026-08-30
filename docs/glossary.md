# Canonical Glossary

This glossary is the normative vocabulary for documentation, configuration, reports, examples, and papers. A metric specification may add a formula or narrower technical definition, but it must not redefine these terms.

## Core data and decision terms

### Outcome

The observed result against which a model or decision is evaluated, represented as `y_true`. An outcome can be favorable or unfavorable depending on the configured `favorable_label`. For example, repayment may be favorable while default may be unfavorable. An outcome is not a lending decision.

### Favorable label

The explicit outcome value that represents the beneficial result for the evaluated individual. It must be configured; FairLendKit must not infer it from values such as `0` or `1`. The favorable label controls the meaning and direction of outcome-based performance metrics.

### Score

A numeric model output used to rank or classify records, represented as `y_score`. Its direction must be explicit: a higher score may mean greater creditworthiness or greater default risk. A score is not a probability unless the input contract says so, and it is not a decision until a documented threshold or policy is applied.

### Decision

An observed or derived action such as approval or denial. The value representing the favorable decision must be explicit. When a decision is derived from a score, the configured threshold, comparison operator, and score direction determine it. A decision must not be described as an outcome.

### Favorable decision

The decision value representing the beneficial action for the evaluated individual, such as approval. It is distinct from the favorable label: approval is a decision, while repayment is an observed outcome.

## Group and comparison terms

### Protected attribute

An attribute used for a research or audit comparison involving a legally protected or otherwise review-relevant characteristic. Its inclusion in an audit does not authorize its use in operational lending decisions. Applicable law and permissible data use depend on context and jurisdiction.

### Audit group

A category or intersectional category formed from the configured protected attribute or attributes for analysis. Use `audit group` when describing the software's group-by operation. Do not assume that every configured category has the same legal status in every jurisdiction.

### Protected group

A group associated with a protected characteristic in the applicable review context. Use this term only when that context is established; otherwise use `audit group`. FairLendKit does not infer which group is legally protected.

### Reference group

The explicitly configured audit group used as the denominator or comparison baseline for a disparity measure. It has no universal default and must not be inferred from race, sex, sample size, outcome rate, or apparent advantage. Being selected as the reference group does not imply legal or normative superiority.

### Comparison group

The audit group whose metric is compared with the reference-group metric. Reports should name both groups and preserve the direction of the comparison.

### Disparity

A descriptive difference or ratio between a comparison-group metric and a reference-group metric, with direction defined by the metric contract. A disparity is an observed statistical relationship, not by itself evidence of causation, intent, unlawful discrimination, or legal non-compliance.

## Screening and interpretation terms

### Selection rate

The proportion of records in an audit group receiving the configured favorable decision. Reports must state the favorable-decision definition and group denominator.

### Adverse impact ratio

The comparison group's selection rate divided by the reference group's selection rate. The comparison direction and any undefined denominator must remain explicit. The four-fifths rule applied to this ratio is a screening heuristic, not a compliance test.

### Potential proxy-risk indicator

A statistical screening result showing that a candidate feature is associated with, informative about, or predictive of a configured protected attribute under a documented method. Correlation, Cramer's V, mutual information, or protected-class predictability may produce such indicators. An indicator does not establish that the feature is an unlawful proxy, caused a disparity, or was used with discriminatory intent.

Use the full label `potential proxy-risk indicator` in practitioner-facing outputs. Do not shorten it to `proxy`, `illegal proxy`, or `discriminatory feature`. Any severity category must use documented, configurable thresholds.

### Screening flag

A review prompt generated when a documented screening condition is met. It calls for practitioner examination and is not an automated finding of compliance, non-compliance, legality, or illegality.

### Statistical uncertainty

The sampling variability communicated through a documented method such as a confidence interval. It does not account for every source of error, including measurement error, selection bias, dataset shift, omitted variables, or causal uncertainty.

### Small-group warning

A warning or suppression triggered when an audit group's sample count is below the configured minimum. It prevents unstable estimates from being presented without qualification; it does not make larger-group estimates automatically reliable.

## Required usage rules

- Always distinguish outcome, score, and decision.
- Always configure favorable label, score direction, favorable decision, and reference group.
- Use `audit group` as the software-neutral term unless the applicable protected-class context is established.
- State disparity direction and name both comparison and reference groups.
- Use `potential proxy-risk indicator` for proxy screening results.
- Do not generate `compliant`, `non-compliant`, `legal`, or `illegal` as automated conclusions.

