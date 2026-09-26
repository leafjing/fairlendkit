# Epic 1.3 — Structural Integrity Contract

## Status and scope

This document is the normative implementation contract for Epic 1.3. It adds
structural-integrity validation to the existing `AuditConfig` and
`validate_audit_data` boundary. It does not add metric computation, report
rendering, or the layered validation-result model planned for Epic 1.4.

The validator is deterministic, does not mutate the caller's `DataFrame`, and
evaluates all row-level conditions against the original input before deciding
which rows are eligible.

## Configuration model

`AuditConfig` adds the following frozen, serialized fields:

- `duplicate_policy`: `error`, `exclude`, or `allow`; default `error`.
- `record_id_column`: optional non-empty column name. When configured, it is a
  required column with the dedicated semantic role `record_id` and cannot
  overlap another configured column role.
- `expected_categories`: mapping from configured categorical column names to a
  non-empty tuple of allowed typed values; default empty mapping. Keys may name
  only `outcome_column`, `decision_column`, or a protected attribute. A derived
  decision has no input column and therefore cannot be a key.

Unknown fields remain forbidden. `record_id_column`, if present, participates
in the existing one-role-per-column rule. Each `expected_categories` key must
name exactly one eligible categorical role. Allowed values must be unique under
FairLendKit's type-sensitive equality rule: `True`, `1`, and `"1"` are distinct.

Configuration validation rejects:

- an empty allowed-value tuple;
- a duplicate allowed value;
- a key that is not an eligible categorical column;
- a column with multiple semantic roles; or
- a `favorable_label`, `favorable_decision_label`, or configured reference-group
  value omitted from the applicable allowed-value tuple.

There is no configurable numeric range for scores in Epic 1.3. A valid score
is any finite real number; the configured decision threshold must remain
finite, `minimum_group_size >= 1`, and `0 < confidence_level < 1`. Sample
weights remain finite and non-negative, with a positive total over final
eligible rows.

## Required columns and value types

The required-column set is the union of outcome, score, protected attributes,
candidate proxy features, configured decision or weight columns, and the
optional record ID column. A missing required column is a dataset-level error
and is never converted into row exclusions.

After exclusions defined below, final eligible data must satisfy:

- `score_column`: numeric dtype and finite numeric values;
- `sample_weight_column`, when configured: numeric dtype, finite and
  non-negative values, with a strictly positive eligible-row sum;
- `record_id_column`, when configured: non-missing and unique among final
  eligible rows;
- each configured categorical column: every value belongs to its
  type-sensitive `expected_categories` set;
- the configured favorable outcome, favorable observed decision, and every
  reference group occur in final eligible data.

`object` or string numeric values are not coerced into numeric columns.
Booleans do not satisfy numeric score or weight requirements. Positive and
negative infinity are invalid, not missing.

## Duplicate definition and policy

Duplicate membership is computed once against the original input:

- If `record_id_column` is configured, every row whose non-missing ID occurs
  more than once belongs to a duplicate set. All occurrences, including the
  first, are duplicate rows. Missing IDs are handled as missing required
  values, not as duplicate IDs.
- Without `record_id_column`, duplicate membership uses exact equality across
  the full input row and pandas duplicate semantics. All occurrences of an
  identical row, including the first, are duplicate rows.

The policy then applies as follows:

- `error`: any duplicate set raises `DataValidationError` after the validator
  has determined its count; the error includes the duplicate-row count.
- `exclude`: every member of every duplicate set is ineligible. Keeping an
  arbitrary first occurrence is forbidden.
- `allow`: duplicate membership is reported, but duplicates are not excluded.

When a record ID is configured, `allow` does not waive ID uniqueness: repeated
IDs make the final eligible dataset invalid. Consequently, callers that use a
record ID must select `error` or `exclude` whenever repeated IDs exist.

## Stable reason codes

Epic 1.3 defines these row-level reason codes:

- `missing_required_value`: at least one required value is missing.
- `duplicate_record`: the row belongs to a duplicate set.
- `non_finite_numeric`: a score or sample weight is positive or negative
  infinity.
- `unexpected_category`: a value is outside a configured allowed-value set.

Reason-code strings are public serialized identifiers. They must not be renamed
without an explicit compatibility decision. Missing columns, non-numeric
dtypes, negative weights, non-positive final weight totals, absent required
semantic values, and invalid configuration are dataset- or configuration-level
errors; they do not receive row-level reason codes in Epic 1.3.

## Evaluation and merge order

Validation uses this fixed sequence:

1. Validate `AuditConfig` and required-column presence.
2. On the original input, independently compute masks for missing required
   values, duplicate membership, non-finite numeric values, and unexpected
   categories. No earlier exclusion hides a later reason.
3. Apply error policies. `missing_value_policy="error"` fails if the missing
   mask is non-empty. `duplicate_policy="error"` fails if the duplicate mask is
   non-empty. Non-finite numeric values and unexpected categories always fail;
   Epic 1.3 provides no exclusion policy for them.
4. For successful validation, combine exclusion masks with logical OR:
   `missing_required_value` when `missing_value_policy="exclude"`, plus
   `duplicate_record` when `duplicate_policy="exclude"`.
5. Run final eligible-population checks, including non-empty eligible data,
   favorable/reference value presence, record-ID uniqueness, sample-weight
   total, and small-group detection.

This ordering extends Epic 1.2 without changing it: missing or unknown
protected-attribute values continue to use the Epic 1.2 exclusion mask and are
merged with structural exclusions by union. If Epic 1.2 exposes a distinct
unknown-value mask, its reason code and count remain distinct; it must not be
collapsed into `missing_required_value` or `unexpected_category`.

## Validation result for Epic 1.3

Until Epic 1.4 introduces layered results, `ValidationSummary` remains the
successful-validation return type and adds:

- `reason_counts: tuple[tuple[str, int], ...]`: count of rows matching each
  reason, ordered lexicographically by reason code; zero-count reasons are
  omitted.
- `duplicate_rows: int`: total rows belonging to duplicate sets, regardless of
  duplicate policy.

Existing fields retain these meanings:

- `input_rows`: original row count;
- `eligible_rows`: rows remaining after the union of exclusions;
- `excluded_rows`: cardinality of that union, never the sum of reason counts;
- `small_groups`: stable, sorted identifiers computed only from final eligible
  rows.

For a row matching multiple reasons, increment every applicable reason count
once, but increment `excluded_rows` at most once. Therefore
`sum(reason_counts) >= excluded_rows` is valid and expected. Row indices or raw
record IDs must not be included in public errors or summaries.

## Error contract

Configuration failures use Pydantic `ValidationError`. Dataset failures use
`fairlendkit.DataValidationError`. Error messages must identify the violated
rule and aggregate count where applicable, remain deterministic under row
reordering, and avoid leaking input values or record identifiers.

Validation is fail-closed: an error returns no plausible partial
`ValidationSummary`. The caller's frame, index, column order, and dtypes remain
unchanged on success or failure.

## Acceptance tests

Implementation is acceptable only when named tests demonstrate all of the
following:

1. Each duplicate policy with and without `record_id_column`, including the
   all-occurrences rule and typed/string IDs.
2. Missing record IDs follow `missing_value_policy`; repeated IDs cannot remain
   in final eligible data.
3. Required-column union includes the record ID, and role overlap is rejected.
4. Numeric dtype enforcement rejects numeric strings and booleans; `NaN`
   follows missing-value policy; both infinities produce
   `non_finite_numeric`; negative weights and zero eligible weight total fail.
5. Every existing and new configuration bound is exercised at, below, and
   above its boundary where meaningful.
6. Expected-category validation is type-sensitive and rejects invalid keys,
   empty or duplicate sets, omitted configured semantic values, and unexpected
   input values.
7. A hand-built fixture contains rows with two or more simultaneous reasons;
   per-reason counts include every match while `excluded_rows` counts the union.
8. Missing/unknown exclusions from Epic 1.2 and duplicate exclusions from Epic
   1.3 merge in the documented order and cannot hide one another.
9. Favorable labels, observed favorable decisions, reference groups, weight
   totals, and small groups are evaluated on final eligible rows.
10. Row permutation leaves all counts and stable identifiers unchanged; the
    input frame is byte-for-byte equivalent in values, index, columns, and
    dtypes before and after validation.
11. Summary serialization preserves stable reason-code strings and deterministic
    ordering.
12. Existing Epic 1.1 and Epic 1.2 tests remain green on every supported Python
    version, and `git diff --check` reports no errors.

The implementation PR must link each criterion to at least one named automated
test. Any change to this contract requires its documentation and tests in the
same PR.
