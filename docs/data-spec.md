# Data specification and `AuditConfig`

The [canonical glossary](glossary.md) is the normative vocabulary for this
contract.

## Contract boundary

An audit combines a tabular dataset with an explicit `AuditConfig`. FairLendKit
does not infer whether a label is favorable, whether a higher score is better,
or which group is the reference. Configuration errors use Pydantic's
`ValidationError`; dataset errors raise `fairlendkit.DataValidationError`.

Input data must be public, appropriately licensed, or synthetic. Proprietary or
confidential data and artifacts must not be committed to the repository.

## Required configuration

- `outcome_column` (`str`): observed outcome or ground-truth column.
- `score_column` (`str`): finite numeric model score.
- `population_definition` (`str`): non-blank description of the population
  represented by the audit.
- `sampling_definition` (`str`): non-blank, independent description of how
  records were selected from that population, including when no sampling was
  performed.
- `score_type`: `probability` or `ranking`; the toolkit does not infer
  calibration semantics from score values.
- `dataset_version` and `model_version`: non-blank identifiers or explicit
  `null` when unavailable.
- `data_as_of`: timezone-aware extraction/as-of timestamp or explicit `null`
  when unavailable.
- `execution_timestamp`: timezone-aware timestamp for this audit execution,
  recorded separately from `data_as_of`.
- `favorable_label` (`str | int | bool`): value in the outcome column that
  represents the favorable outcome.
- `score_direction`: `higher_is_more_favorable` or
  `lower_is_more_favorable`.
- `protected_attributes` (non-empty list): one or more columns used for group
  analysis. Multiple attributes are validated independently; later analysis
  may also form intersectional slices.
- `allowed_groups` (mapping): a non-empty collection of allowed category values
  for every protected attribute. Mapping keys must exactly match
  `protected_attributes`; values are compared without string coercion.
- `reference_groups` (mapping): exactly one explicit reference value for every
  protected attribute. Each reference value must be a member of that
  attribute's `allowed_groups`. No demographic group is selected by default.
- `favorable_decision_label` (`str | int | bool`): value representing the
  beneficial action. It is required and distinct from `favorable_label`, which
  describes the observed outcome.
- Exactly one decision source:
  - `decision_column`: column containing observed actions; or
  - `decision_threshold` and `threshold_operator`: finite threshold and explicit
    inclusive comparison (`ge` means score `>=` threshold; `le` means score
    `<=` threshold) used to derive the favorable decision.

## Optional configuration

- `sample_weight_column`: finite, non-negative weights with a positive total.
- `candidate_proxy_features`: candidate feature columns selected for screening.
- `minimum_group_size` (default `30`, minimum `1`): groups below this size are
  returned as warnings in the validation summary; they are not silently removed.
- `confidence_level` (default `0.95`, exclusive range 0 to 1).
- `missing_value_policy`: `error` (default) or `exclude`, governing null/NA values
  in required analysis columns.
- `unknown_group_policy`: `error` (default) or `exclude`, governing non-null
  protected-attribute values outside the configured `allowed_groups`.

Missing and unknown are different states and their policies are evaluated
independently. Neither policy permits coercing, relabeling, or folding a value
into an allowed group. With either `exclude` policy, validation constructs an
eligibility result without mutating the input frame and reports stable reason
codes and counts.

Unknown configuration fields are rejected. Top-level configuration fields
cannot be reassigned after construction. Orchestration code must serialize the
validated configuration at run start so nested input mappings cannot alter the
recorded run metadata.

All run-context fields are required in the configuration. Only
`dataset_version`, `model_version`, and `data_as_of` accept explicit `null` when
the value is unavailable. Blank definitions, blank version identifiers,
unsupported score types, naive timestamps, and omitted fields fail configuration
validation before any data validation or metric calculation.

Every input column has exactly one semantic role. Outcome, score, observed
decision, sample weight, protected-attribute, and candidate-feature columns
must all be distinct. Candidate features also cannot repeat or overlap any core
column; callers that intentionally screen a transformed copy must provide it
under a distinct column name. Role overlap is treated as ambiguous semantics
and fails configuration validation.

For a derived decision, `ge` is valid only with
`higher_is_more_favorable`, and `le` only with
`lower_is_more_favorable`. This redundancy is intentional: inconsistent score
and decision directions fail validation instead of silently reversing results.
Scores are not assumed to be probabilities, so the contract does not impose a
0-to-1 threshold range.

A score satisfying the inclusive threshold rule receives the meaning recorded
by `favorable_decision_label`. For example, with threshold `0.6`, operator
`ge`, and favorable decision label `"approved"`, scores equal to or greater
than `0.6` are derived favorable decisions. This derived decision remains
distinct from the observed outcome and `favorable_label`.

## Data mappings and values

Column names in the configuration map directly to tabular input columns.
Categorical group and label values retain their input types: for example, the
boolean `True`, integer `1`, and string `"1"` are three different values. Allowed
categories must be unique under this type-sensitive comparison. A null/NA value
is missing; an unknown value is a non-null value that does not equal any allowed
category for that protected attribute. Unexpected textual spellings, whitespace,
or case are not normalized by the validator and therefore remain unknown unless
the caller normalizes upstream and records that transformation.

The favorable outcome and any favorable decision label must occur in eligible
data. Every reference group is checked twice: it must belong to the configured
allowed set before data validation, and it must occur in eligible data after all
configured exclusions. Failure of either check is an error, not a warning.

Required analysis columns are the outcome, score, protected attributes,
candidate proxy features, and configured decision or weight columns. Missing
required columns fail validation. Missing required values either fail or are
counted for exclusion according to `missing_value_policy`.

For exclusions, `ValidationSummary` exposes the original input count, eligible
count, de-duplicated excluded count, and a mapping of stable reason code to row
count. Initial Epic 1.2 reason codes are:

- `missing_required_value` for a row with null/NA in any required analysis
  column; and
- `unknown_protected_group` for a row with a non-null protected-attribute value
  outside that attribute's allowed set.

A row may contribute to more than one reason count, but contributes only once to
the excluded total. Attribute-level evidence retains the affected attribute and
observed value/count without embedding either into the stable code. Rejected runs
use the same codes and evidence, so changing a policy from `error` to `exclude`
does not change the condition's identity.

The input contract must also record or explicitly mark unavailable:

- population and sampling definition;
- dataset and model version;
- analysis or extraction timestamp;
- whether a score is a calibrated probability or an uncalibrated ranking score;
- treatment of missing or unknown protected-attribute values; and
- business-rule indicators or upstream data-quality flags used in interpretation.

These fields may begin as report metadata rather than analysis inputs, but their
availability and provenance must be visible in the audit trail.

## Validation layers and data-quality observations

A successful structural validation means only that the toolkit can execute the
configured analysis. It does not assert that the data is appropriate, complete,
representative, or correctly defined for the review.

Structural checks cover required columns, types, finite numerical values,
duplicate record policy, expected categories, range constraints, missing values,
and eligible group sizes. Semantic checks require explicit meanings for labels,
scores, decisions, thresholds, reference groups, population, and unknown values.

Where baseline or prior-run metadata is available, the validation summary should
also report data freshness, distribution change, group-size change, missingness
by group, unexpected categories, anomalous values, and dataset/model-version
change. These are observations with supporting counts or statistics, not silent
row transformations or automated causal conclusions.

## Public API

```python
from fairlendkit import AuditConfig, ScoreDirection, validate_audit_data

config = AuditConfig(
    outcome_column="repaid",
    score_column="creditworthiness_score",
    population_definition="All completed applications in 2026 Q2",
    sampling_definition="All eligible records; no sampling",
    score_type="ranking",
    dataset_version="applications-2026q2-v1",
    model_version="underwriting-v3.2",
    data_as_of="2026-07-01T00:00:00Z",
    execution_timestamp="2026-07-02T12:30:00Z",
    favorable_label=1,
    score_direction=ScoreDirection.HIGHER_IS_MORE_FAVORABLE,
    protected_attributes=("group",),
    allowed_groups={"group": ("reference", "comparison")},
    reference_groups={"group": "reference"},
    favorable_decision_label=1,
    decision_threshold=0.6,
    threshold_operator="ge",
)
summary = validate_audit_data(frame, config)
assert config.is_favorable_decision_score(0.6)
```

`ValidationSummary` records input, eligible, and excluded row counts, exclusion
reason counts and evidence, plus stable identifiers for groups below
`minimum_group_size`. Counts by reason need not sum to the excluded total because
a row can satisfy multiple exclusion conditions. It does not imply statistical
significance or legal compliance.
