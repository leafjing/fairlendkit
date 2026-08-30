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
- `favorable_label` (`str | int | bool`): value in the outcome column that
  represents the favorable outcome.
- `score_direction`: `higher_is_more_favorable` or
  `lower_is_more_favorable`.
- `protected_attributes` (non-empty list): one or more columns used for group
  analysis. Multiple attributes are validated independently; later analysis
  may also form intersectional slices.
- `reference_groups` (mapping): exactly one explicit reference value for every
  protected attribute. No demographic group is selected by default.
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
- `missing_value_policy`: `error` (default) or `exclude`. With `exclude`, the
  validator reports excluded-row counts but does not mutate the input frame.

Unknown configuration fields are rejected. Top-level configuration fields
cannot be reassigned after construction. Orchestration code must serialize the
validated configuration at run start so nested input mappings cannot alter the
recorded run metadata.

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
boolean `True`, integer `1`, and string `"1"` are three different values. The favorable outcome and
any favorable decision label must occur in eligible data. Every configured
reference group must occur in its protected-attribute column; an unknown group
is a validation error.

Required analysis columns are the outcome, score, protected attributes,
candidate proxy features, and configured decision or weight columns. Missing
required columns fail validation. Missing required values either fail or are
counted for exclusion according to `missing_value_policy`.

## Public API

```python
from fairlendkit import AuditConfig, ScoreDirection, validate_audit_data

config = AuditConfig(
    outcome_column="repaid",
    score_column="creditworthiness_score",
    favorable_label=1,
    score_direction=ScoreDirection.HIGHER_IS_MORE_FAVORABLE,
    protected_attributes=("group",),
    reference_groups={"group": "reference"},
    favorable_decision_label=1,
    decision_threshold=0.6,
    threshold_operator="ge",
)
summary = validate_audit_data(frame, config)
assert config.is_favorable_decision_score(0.6)
```

`ValidationSummary` records input, eligible, and excluded row counts plus stable
identifiers for groups below `minimum_group_size`. It does not imply statistical
significance or legal compliance.
