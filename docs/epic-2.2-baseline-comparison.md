# Epic 2.2 — Baseline Comparison Contract

## Status and scope

This is the normative implementation contract for Epic 2.2. It compares one
current Epic 2.1 single-run profile with one explicitly selected baseline and
produces deterministic, renderer-neutral evidence about changes in group
composition, missingness, score and outcome distributions, and dataset and
model versions.

Comparison is descriptive screening. A change flag is not a validation failure,
a drift diagnosis, a causal finding, a compliance conclusion, or an instruction
to replace a model or dataset. Comparison never changes row eligibility, profile
values, metric values, configuration, or source data. Epic 2.2 does not select a
baseline automatically, retain a baseline registry, compare fairness metrics,
run significance tests, or define monitoring cadence.

## Explicit baseline selection and identity

Baseline comparison is opt-in. The caller supplies a `BaselineSelection` with:

- `baseline_id`: a non-blank, caller-owned immutable identifier;
- `selection_method`: one of `run_id`, `artifact_uri`, or `content_digest`;
- `selected_value`: the non-blank run ID, URI, or lowercase SHA-256 digest used
  to make the selection; and
- `profile_digest`: lowercase SHA-256 of the baseline profile's canonical JSON,
  or `null` only when the selected baseline artifact is unavailable.

When `selection_method="content_digest"`, `selected_value` must equal
`profile_digest` exactly. Both must be present lowercase 64-character SHA-256
hex strings. A selection model with unequal values is invalid and comparison
does not start. For the other selection methods, `selected_value` identifies
the external run or artifact while `profile_digest` independently binds its
resolved profile content.

`baseline_id` is the stable identity exposed by every check and flag.
`selected_value` records how the caller resolved that identity; it is not
derived from recency, dataset version, model version, filename order, or the
observed data. The implementation must not choose “previous”, “latest”, a
reference group, or the current run as an implicit baseline.

When the baseline is available, the caller supplies its immutable
`LayeredValidationResult` and the complete validated `AuditConfig` recorded for
that run. The current result and current recorded config are supplied
separately. Before calculation, the implementation recomputes the canonical
baseline profile digest and requires it to equal `profile_digest`. A mismatch
is incompatible evidence, not a comparison against whichever object happened
to be passed.

The result repeats the complete `BaselineSelection`; renderers must show at
least `baseline_id`, `selection_method`, `selected_value`, and `profile_digest`.
Changing the selected baseline necessarily changes serialized comparison
identity even if the profile statistics happen to be identical.

## Public API and result model

Epic 2.2 adds a pure public function with this semantic signature:

```python
compare_profiles(
    current: LayeredValidationResult,
    current_config: AuditConfig,
    baseline: LayeredValidationResult | None,
    baseline_config: AuditConfig | None,
    selection: BaselineSelection,
    policy: BaselineComparisonPolicy,
) -> BaselineComparisonResult
```

The function accepts already validated, frozen inputs and performs no I/O or
baseline lookup. `baseline` and `baseline_config` are either both present or
both absent. `BaselineComparisonResult` is frozen and strict and contains:

- `schema_version`: literal `"1.0"`;
- `baseline`: the complete selection record;
- `current_profile_digest`: lowercase SHA-256 of the exact current profile used;
- `status`: `completed`, `partially_completed`, `unavailable`, or
  `incompatible`;
- `policy`: the complete threshold policy used;
- `checks`: the canonically ordered `ComparisonCheck` tuple;
- `flags`: the canonically ordered `ChangeFlag` tuple; and
- `issues`: comparison-level data-quality issues.

Every required comparison domain has one or more checks. A `ComparisonCheck`
contains `check_id`, `code`, `status`, `statistic`, `threshold`,
`current_value`, `baseline_value`, `baseline_id`, `affected_fields`,
`affected_groups`, and optional `reason_code`. Check status is `evaluated`,
`not_computable`, `unavailable`, or `incompatible`. Values are typed JSON
scalars or `null` and all numeric values are finite. A non-evaluated check has
null statistic and values except for safe identity evidence needed to explain
incompatibility.

`check_id` is unique within a result and stable across equivalent inputs. It is
`<code>:<scope_digest>`, where `scope_digest` is the lowercase SHA-256 of the
canonical JSON object containing only that check's identity dimensions: field,
typed group, quantile probability, or typed category as applicable. Canonical
JSON uses the digest rules below; an empty identity object is used for a
singleton check. Human-readable labels are not interpolated into IDs.

A `ChangeFlag` contains `source_check_id` plus the same required evidence fields
except check status and reason, and has its own stable change `code`. The source
ID must resolve to exactly one evaluated check in the same result, and every
flag's statistic, threshold, values, baseline ID, fields, and groups must equal
that source check's evidence. Zero, one, or multiple flags may reference one
check; code matching alone is never an association mechanism. A flag is created
only when the source check's declared comparison condition is met. Thus every
flag always contains:

- a stable code;
- an exact `source_check_id`;
- the named statistic and its comparison condition;
- the exact threshold used (finite numeric or the literal `"equal"`);
- the typed current and baseline values that produced the statistic, with
  finite numbers wherever the values are numeric;
- the explicit `baseline_id`; and
- sorted affected fields and affected groups.

No flag may contain row indices, record identifiers, raw samples, free-form
payloads, or an automated verdict. Checks retain non-flagged evidence so an
empty `flags` tuple means “no configured threshold was crossed among evaluated
checks”, not merely “no evidence was saved”.

## Composition with validation and AuditResult

`compare_profiles()` returns only an independent `BaselineComparisonResult` and
does not mutate either frozen input. Epic 2.2 also adds the pure composition
function:

```python
attach_baseline_comparison(
    current: LayeredValidationResult,
    comparison: BaselineComparisonResult,
) -> LayeredValidationResult
```

`LayeredValidationResult` gains an additive optional `comparison` field. A
single-run result has `comparison=null`, which means comparison was not
requested. The composition function requires `current.profile` to be the exact
current profile used by the comparison, verified by a `current_profile_digest`
stored in `BaselineComparisonResult`. It returns a newly constructed frozen
validation result with `comparison` set, the data-quality layer rebuilt under
the integration rules below, aggregate status re-derived, and all other source
evidence fields unchanged. It rejects a different current profile, a result
that already contains a comparison, or any inconsistent derived layer/aggregate
status. It never edits `current` in place.

`AuditResult.validation` receives that newly composed validation result through
the existing AuditResult construction path; there is no second comparison field
on `AuditResult`. Aggregation is therefore part of Epic 2.2, not deferred to a
renderer or a later epic. Legacy and single-run AuditResult fixtures migrate to
the explicit `comparison=null` value and must not fabricate an unavailable
comparison.

## Threshold policy

There are no hidden or universal change thresholds. The caller must provide a
strict `BaselineComparisonPolicy` containing all of:

- `group_proportion_delta`: finite number in `(0, 1]`;
- `missingness_rate_delta`: finite number in `(0, 1]`;
- `score_quantile_delta`: finite number greater than `0`, in score units; and
- `outcome_proportion_delta`: finite number in `(0, 1]`.

All numeric change conditions are inclusive: flag when
`absolute(current_value - baseline_value) >= threshold`. Equality therefore
flags. Values below a threshold remain recorded as evaluated checks. Version
and category-presence checks use exact typed equality and have the literal
threshold `"equal"`; a mismatch flags.

Policy fields cannot be omitted, inferred from the data, or changed by an
adapter. Policy serialization is part of the result. A future relative,
weighted, statistical-significance, or domain-specific rule requires a new
named statistic and an additive contract; it must not reinterpret these codes.

## Compatibility gate

Comparison first applies one all-or-nothing compatibility gate. Profiles are
compatible only when:

- both are present, have `schema_version == "1.0"`, and are complete successful
  Epic 2.1 profiles;
- profile digests and enclosing row counts pass their own invariants;
- required analysis column names and column roles match exactly;
- protected attributes, typed allowed groups, and typed reference groups match
  exactly;
- favorable outcome and favorable decision labels match by type and value;
- score type and score direction match; and
- profile methods match, including score quantile method and population
  definitions.

Dataset version, model version, execution time, `data_as_of`, physical row
counts, observed outcome categories, and the configured decision threshold are
not compatibility requirements; they are either comparison subjects or run
context. Sample-weight configuration does not affect compatibility because all
Epic 2.1 profile comparisons are explicitly unweighted.

Any compatibility failure makes the result `incompatible`; all required checks
are `incompatible`, no numeric or version flags are emitted, and exactly one
`comparison_baseline_incompatible` issue records a stable reason code. The
implementation must not compare the compatible-looking subset of mismatched
profiles. Supported reason codes are:

- `profile_schema_mismatch`;
- `profile_invariant_failure`;
- `baseline_digest_mismatch`;
- `analysis_semantics_mismatch`;
- `group_definition_mismatch`; and
- `profile_method_mismatch`.

Affected fields and groups identify the mismatched declarations without
including raw data. If multiple reasons apply, choose the first code in the
order above after collecting the union of safe affected fields/groups. This
keeps output deterministic.

## Group-composition comparison

For every configured protected attribute and allowed typed group value, compare
the Epic 2.1 **eligible-population** proportion. Emit one
`group_proportion_absolute_delta` check with:

- `statistic="absolute_proportion_delta"`;
- current and baseline eligible proportions;
- `threshold=policy.group_proportion_delta`;
- the protected attribute in `affected_fields`; and
- the typed single-attribute group in `affected_groups`.

Flag code `group_composition_changed` is emitted when the inclusive threshold
is met. Counts are retained by the source profiles but are not substituted for
the required rate evidence. Configured groups with zero rows remain comparable:
their proportion is the defined value `0.0` because each successful profile has
a positive eligible-population denominator.

## Missingness comparison

Compare each overall input-population missingness rate for every required
analysis field. Also compare grouped missingness for every field and every
configured protected-attribute value, using the same one-attribute group
definition as Epic 2.1.

Each `missingness_rate_absolute_delta` check uses
`statistic="absolute_rate_delta"`, the policy's missingness threshold, the two
rates, the profiled field plus grouping attribute as affected fields, and the
group when applicable. Flag code `missingness_changed` is emitted at or above
the inclusive threshold.

An overall rate is always computable. A grouped rate is computable only when
both source profiles contain at least one input row in that group. If either
group total is zero, emit a `not_computable` check with
`reason_code="zero_group_sample"`; do not treat a missing rate as zero and do
not emit a change flag. This rule also covers a configured group absent from an
Epic 2.1 grouped-missingness tuple.

## Distribution comparisons

### Score distribution

Compare each of the five fixed Epic 2.1 quantiles at probabilities `0`, `0.25`,
`0.5`, `0.75`, and `1`. Each `score_quantile_absolute_delta` check records
`statistic="absolute_quantile_delta"`, the current and baseline quantile, and
`threshold=policy.score_quantile_delta`. It affects only the score column.

Flag code `score_distribution_changed` is emitted for each quantile meeting the
inclusive threshold. The quantile probability is a required finite member of
the check and flag, so multiple flags remain distinguishable. No standard
deviation normalization, bins, PSI, KS statistic, or significance claim is
permitted: those cannot be reconstructed faithfully from the Epic 2.1 profile.

### Outcome distribution and category changes

Compare category membership separately for every typed category in the
canonical union of the current and baseline eligible outcome categories. Typed
values remain distinct (`true`, `1`, and `"1"` are different). For each category
emit one `outcome_category_presence_equal` check with:

- a category-specific `check_id` whose identity scope contains the typed
  category;
- `statistic="exact_equality"` and threshold `"equal"`;
- boolean `current_value` and `baseline_value` indicating membership; and
- the outcome column as affected field and the typed `category` member.

The scalar booleans satisfy the common check schema; a category set is never
placed in `current_value` or `baseline_value`. When current is `true` and
baseline is `false`, emit `outcome_category_added`; for the inverse emit
`outcome_category_removed`. The flag's `source_check_id` links it to that exact
evaluated membership check. Its values remain the same two booleans; absence is
not represented by null. This permits deterministic validation without relying
on a shared code or searching a collection value.

Then compare category proportions over the canonical union of typed categories.
An absent category has count and proportion `0.0`; this is a defined zero, not
an unavailable value. Each `outcome_proportion_absolute_delta` check records
`statistic="absolute_proportion_delta"` and the configured outcome threshold.
Flag code `outcome_distribution_changed` is emitted at or above that threshold.
The outcome column is the affected field and the typed category is recorded in
the check's `category` member, not represented as a protected group.

## Dataset and model versions

Dataset and model versions are compared independently with exact string
equality. Checks use codes `dataset_version_equal` and `model_version_equal`,
`statistic="exact_equality"`, and threshold `"equal"`. A mismatch emits
`dataset_version_changed` or `model_version_changed` and records both version
strings, the baseline ID, and affected metadata field.

If either side of a version comparison is `null`, that check is
`not_computable` with reason `version_unavailable`; null is not a version and
must not be coerced to an empty string. The other version check and all numeric
checks may still run, producing a `partially_completed` result.

## Unavailable, zero-sample, and non-computable states

If the selected baseline cannot be resolved, pass both baseline arguments as
`null`. The result is `unavailable`; every required check is `unavailable` with
reason `baseline_unavailable`, flags are empty, and the sole issue is the
existing `comparison_baseline_unavailable`. The selection and unavailable
profile digest remain recorded. Baseline absence is never reported as “no
change”.

A successful Epic 2.1 profile guarantees positive input and eligible totals,
so a zero whole-population sample is an invariant failure and therefore
incompatible. Zero samples for a configured group are valid and follow the
domain rules above: eligible group proportions remain defined zeros, while
grouped missingness rates are not computable without a denominator.

`BaselineComparisonResult.status` is derived as follows:

- `unavailable` when no selected baseline artifact is available;
- `incompatible` when the compatibility gate fails;
- `completed` when every required check is evaluated; and
- `partially_completed` when compatible profiles have at least one evaluated
  check and at least one `not_computable` check.

A threshold not being crossed does not make a check unavailable. An arithmetic
error, non-finite derived value, missing required check, or internally
inconsistent source profile fails closed as incompatibility; no partial numeric
result is returned.

## Data-quality layer integration and stable codes

`attach_baseline_comparison()` augments the newly constructed current run's
data-quality layer with comparison issues and issues implied by flags, without
duplicating Epic 2.1 issues. `compare_profiles()` alone does not alter a layer.
Stable codes are:

- `comparison_baseline_unavailable`: info, non-blocking;
- `comparison_baseline_incompatible`: info, non-blocking;
- `comparison_check_not_computable`: info, non-blocking;
- `group_composition_changed`: warning, non-blocking;
- `missingness_changed`: warning, non-blocking;
- `score_distribution_changed`: warning, non-blocking;
- `outcome_distribution_changed`: warning, non-blocking;
- `outcome_category_added`: warning, non-blocking;
- `outcome_category_removed`: warning, non-blocking;
- `dataset_version_changed`: info, non-blocking; and
- `model_version_changed`: info, non-blocking.

Each issue points to the typed comparison evidence rather than squeezing the
new contract into legacy `ValidationEvidence`. One issue may summarize flags
with the same code, but it must preserve links to every underlying flag; the
flags themselves remain the normative evidence records containing statistic,
threshold, values, baseline identity, fields, and groups. Version changes are
factual information; distribution, group, missingness, and category changes are
warnings requesting review. None are blocking.

When comparison is requested, the data-quality layer is `warning` if any
comparison warning exists, otherwise `passed` if at least one comparison or
single-run check ran. It is `not_evaluated` only when every applicable
data-quality check is unavailable. An unavailable or incompatible comparison
does not erase successfully evaluated Epic 2.1 checks and therefore normally
leaves that layer `passed` or at its existing warning status.

## Determinism, ordering, and privacy

Equivalent inputs serialize identically regardless of row order, mapping
insertion order, pandas index, or source artifact location. Checks are ordered:

1. group composition by attribute and typed group value;
2. missingness by field, overall before grouped, then typed group key;
3. score quantiles by ascending probability;
4. outcome category-presence checks, then proportions, each by typed category;
5. dataset version, then model version.

Flags follow their source-check order. Category-presence checks and their flags
use typed category order; when otherwise tied, removals precede additions.
Issues retain the Epic 1.4 issue order. Typed values use the Epic 2.1 canonical
type rank and value ordering.

Canonical profile digests use UTF-8 JSON with sorted object keys, compact
separators, no ASCII escaping requirement, JSON-safe shortest round-trip finite
numbers, and normalized positive zero. The digest excludes comparison objects
and external artifact paths.

Comparison output contains no source rows, samples, row identifiers, applicant
values, unknown raw categories, or artifact credentials. `artifact_uri`
selection values must be stable sanitized identifiers and must not contain URI
userinfo, query strings, or fragments. Implementations reject rather than
silently redact an unsafe value.

## Compatibility and failure behavior

- All Epic 1 and Epic 2.1 public names, arguments, models, codes, and serialized
  meanings remain compatible.
- Calling single-run validation alone still performs no baseline comparison and
  emits no comparison issue merely because no baseline was supplied.
- Comparison is additive to `LayeredValidationResult` during V1 and reaches
  `AuditResult` only through its existing validation field; a legacy result
  parses with validation comparison `null`, meaning not requested, not
  unavailable.
- Missing, unavailable, incompatible, and not-computable are distinct states and
  never become a fabricated zero, equality, empty version, or passed check.
- Invalid selection or policy models raise configuration validation errors.
  Corrupt profile evidence fails closed and returns no plausible partial
  comparison.
- Removing a field, changing a statistic or threshold condition, or changing a
  stable code's meaning requires schema-version review and migration notes.

## Acceptance tests

Implementation is acceptable only when named automated tests demonstrate:

1. Baseline selection is explicit, fully serialized, digest-verified, and never
   inferred from recency, versions, filenames, or observed values;
   `content_digest` selections require exact selected-value/profile-digest
   equality.
2. Every flag contains its stable code, source check ID, statistic, threshold,
   current value, baseline value, baseline ID, and sorted affected fields/groups;
   every source ID resolves to exactly one evaluated check with identical
   evidence.
3. Required numeric policy thresholds are strict, finite, serialized, and
   applied with inclusive absolute-delta semantics, including equality at the
   boundary; equality checks serialize the literal threshold `"equal"`.
4. Eligible group proportions compare every configured typed group, including
   defined zero-count groups, with exact hand-calculated deltas.
5. Overall and grouped missingness compare exact input-population rates; a zero
   group denominator yields `zero_group_sample`, never a zero rate or flag.
6. All five score quantiles compare in score units, preserve probability
   identity, and reject undocumented normalization or inferred methods.
7. Outcome categories preserve types; scalar per-category presence checks,
   additions, removals, union-based zero proportions, rare categories, and
   proportion thresholds match fixtures.
8. Dataset and model versions compare independently; exact changes flag, while
   either-side null produces `version_unavailable` without suppressing other
   checks.
9. A missing baseline returns `unavailable` with the existing stable issue and
   no flags; a digest or semantic mismatch returns `incompatible` with the
   deterministic reason and no partial comparisons.
10. Zero whole-population samples and corrupt/non-finite profiles fail closed;
    zero group samples follow the domain-specific defined/not-computable rules.
11. Complete, partial, unavailable, and incompatible result statuses derive
    exactly from check states; composition returns a new frozen validation
    object, verifies the current-profile digest, attaches comparison once, and
    preserves already completed Epic 2.1 checks while deriving layer and
    aggregate statuses.
12. Row permutation, mapping order, typed-label edge cases, and equivalent
    profile objects produce byte-identical canonical JSON and digest values.
13. Strict models reject unknown fields, booleans as numbers, invalid ratios,
    non-finite values, unsafe artifact URIs, inconsistent totals, duplicate
    checks, and flags without a matching evaluated check.
14. Privacy tests prove that comparison output includes no raw rows, record IDs,
    samples, credentials, query strings, or fragments.
15. All Epic 1 and Epic 2.1 tests plus AuditResult schema and round-trip fixtures
    pass on Python 3.11/3.12, and `git diff --check` passes.

The implementation PR must map every criterion to at least one named automated
test. Contract changes require matching documentation and tests. Epic 2.3 must
not start until Epic 2.2 is implemented, independently reviewed, merged, and
green on `main`.
