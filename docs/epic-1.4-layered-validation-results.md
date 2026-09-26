# Epic 1.4 — Layered Validation Results Contract

## Status and scope

This is the normative implementation contract for Epic 1.4. It replaces the
flat successful-validation summary with a renderer-neutral result containing
four distinct layers: structural validity, semantic validity, analytical
reliability, and data-quality observations. Epic 1.4 closes Epic 1. It does not
add fairness metrics, legal/policy thresholds, drift algorithms, renderers, or
a governance approval workflow.

Technical validation never means that data is representative, suitable, fair,
compliant, or fit for a particular use.

## Layer boundaries

Every issue belongs to exactly one layer; implementations must not duplicate an
issue across layers merely for visibility.

### Structural validity

Structural validity determines whether the declared table can be processed
without violating its physical and eligibility contract. It owns required
columns, one-role-per-column enforcement, dtypes, finite numeric values, weight
bounds, duplicates, record IDs, missing required values, configured category
membership, and construction of the de-duplicated eligible population. Rows may
be excluded only under an explicit configuration policy.

### Semantic validity

Semantic validity determines whether analysis meaning is explicit and
internally consistent. It owns favorable outcome and decision meanings, score
direction/type, decision source and threshold operator, population and sampling
definitions, allowed/reference groups, missing/unknown semantics, and dataset,
model, and as-of context. Meanings must never be inferred from observed values.

### Analytical reliability

Analytical reliability determines whether eligible data supports a stated
calculation and how cautiously it must be interpreted. It owns group/class
support, denominators and weights, estimability, undefined-result reasons, and
uncertainty limitations. Reliability issues never silently exclude rows. Epic
1.4 initially reports group support available during validation; later metric
epics may add codes without moving structural or semantic issues.

### Data-quality observations

Data quality records factual, non-transforming observations: freshness,
missingness by group, anomalous values, distribution/group-size change, and
dataset/model-version change when required metadata or a declared baseline is
available. If evidence needed for a check is unavailable, that check is
`not_evaluated`, not `passed`.

## Public result model

On successful technical validation, `validate_audit_data` returns a frozen,
strict `LayeredValidationResult` with:

- `schema_version`: literal `"1.0"` for this standalone contract;
- `status`: derived aggregate `ValidationStatus`;
- `technical_validation`: aggregate of structural and semantic layers;
- `applicability`: literal `"not_assessed"`;
- `applicability_statement`: the canonical practitioner-review statement;
- `input_rows`, `eligible_rows`, and `excluded_rows`;
- `reason_counts`, sorted by code with zero counts omitted;
- `duplicate_rows` and compatibility-period `small_groups`; and
- `layers`: exactly one result for each required layer in canonical order.

`ValidationStatus` is a closed enumeration:

- `passed`: evaluated with no warning or error;
- `warning`: at least one warning and no error;
- `failed`: at least one error; and
- `not_evaluated`: required inputs, baseline, or later-epic calculation are
  unavailable.

Each layer contains its identifier, derived status, and ordered issue tuple.
`warning` and `failed` require a corresponding issue. Empty issue tuples are
valid for `passed`; `not_evaluated` requires an informational issue identifying
the unavailable input or unimplemented later-epic check.

## Issue contract

Every `ValidationIssue` requires:

- stable lower-case `code`;
- `severity`: `info`, `warning`, or `error`;
- sorted unique `affected_fields`;
- sorted unique `affected_groups`, each a sorted attribute-to-typed-label map;
- typed `evidence`;
- canonical neutral `message`; and
- `blocking`, indicating whether technical execution is prevented.

Evidence permits only JSON-safe optional members `count`, `total`, `observed`,
`expected`, `minimum`, `maximum`, and `reason_counts`. Numbers must be finite;
counts are non-negative integers. Evidence must not contain row indices, record
IDs, applicant values, free-form payloads, or unbounded samples. Each code
defines its required evidence members.

Issue order is deterministic by layer, severity (`error`, `warning`, `info`),
code, fields, then groups. Row or mapping insertion order cannot change output.
A domain-owned registry fixes each code's message, severity, blocking behavior,
and evidence requirements. Adapters cannot invent or reinterpret entries. New
codes are additive; renaming or changing a code is breaking.

## Initial stable codes

Epic 1.4 registers at least:

- Structural: `missing_required_column`, `missing_required_value`,
  `non_numeric_score`, `non_numeric_weight`, `negative_weight`,
  `non_positive_weight_total`, `non_finite_numeric`, `duplicate_record`,
  `non_unique_record_id`, `unknown_protected_group`, `unexpected_category`, and
  `no_eligible_rows`.
- Semantic: `favorable_label_absent`, `favorable_decision_label_absent`,
  `reference_group_absent`, `ambiguous_column_role`,
  `inconsistent_threshold_direction`, and `invalid_category_declaration`.
- Analytical reliability: `small_group` (warning). Later metric work may add
  denominator, class-support, estimability, and uncertainty codes.
- Data quality: `comparison_baseline_unavailable` (info). When every applicable
  check lacks evidence, the layer status is `not_evaluated`.

Existing row-level codes retain their Epic 1.2/1.3 meanings. For conditions
governed by `error`, `exclude`, or `allow`, policy may determine severity and
blocking but never changes the condition's code.

Configuration failures may remain Pydantic `ValidationError`s. Dataset failure
remains `DataValidationError`, adding ordered `issues` while retaining
`reason_counts` and exclusion evidence. Failure exposes no plausible partial
success result.

## Status and applicability rules

Layer status is derived: any error means `failed`; otherwise any warning means
`warning`; otherwise an evaluated layer is `passed`; a layer with no runnable
applicable check is `not_evaluated`.

`technical_validation` is `failed` if structural or semantic validity fails,
`warning` if neither fails and either warns, otherwise `passed`. Successful
return requires it not to be `failed`. Overall `status` uses the worst evaluated
layer (`failed > warning > passed`); `not_evaluated` is neutral unless all
layers are unevaluated.

`applicability` is always `not_assessed` in Epic 1.4. Status fields and messages
must not express approval, fitness, fairness, legality, or compliance. Every
human-readable or serialized presentation includes: "Technical validation does
not determine fitness for use; applicability requires practitioner review."

## Count and serialization invariants

- `input_rows == eligible_rows + excluded_rows`.
- `excluded_rows` counts the union of exclusion masks.
- `reason_counts` counts every matching reason, so its sum may exceed
  `excluded_rows` and cannot be used for reconciliation.
- Exclusion issue evidence agrees with `reason_counts`.
- Four layer entries are required, unique, and canonically ordered.
- Enums/codes serialize as strings; typed labels retain types; tuples become
  JSON arrays.
- Equivalent inputs serialize deterministically, apart from external run
  timestamps not owned by this result.
- Unknown fields and non-finite JSON numbers are rejected; round trips preserve
  meaning.

Within `AuditResult.schema_version == "1.0"`, layered validation is additive
because no released renderer contract exists. `AuditResult.validation` adopts
the layers while retaining `input_rows`, `analyzed_rows` as the serialized alias
of `eligible_rows`, exclusions, and warnings during V1. Breaking removal or
reinterpretation requires a schema-version change and migration notes.

## Backward compatibility

For the remainder of V1:

- `validate_audit_data` keeps its name and arguments.
- `ValidationSummary` remains importable as an alias or wrapper.
- `input_rows`, `eligible_rows`, `excluded_rows`, `small_groups`,
  `exclusion_reason_counts`, `exclusion_evidence`, `reason_counts`, and
  `duplicate_rows` retain Epic 1.3 meanings.
- Existing `ExclusionReason` strings and `DataValidationError.reason_counts`
  and `.evidence` remain unchanged; `.issues` is additive.
- Existing valid `AuditResult` fixtures keep parsing or receive a documented,
  deterministic migration in the implementation PR.

Compatibility adapters must not fabricate `passed` for an unevaluated layer.

## Acceptance tests

Implementation is acceptable only when named tests demonstrate:

1. Exactly four layers in canonical order, with status derived from issues.
2. Every status, including wholly `not_evaluated` data quality, and unavailable
   baseline evidence.
3. Structural, semantic, reliability, and data-quality fixtures assign each
   issue to exactly one layer.
4. The registry enforces canonical code, message, severity, blocking behavior,
   fields/groups, and evidence requirements.
5. Evidence rejects non-finite values, negative counts, raw identifiers,
   unknown fields, and type-erased labels.
6. Multi-reason rows preserve all counts while exclusions reconcile by union,
   including `sum(reason_counts) > excluded_rows`.
7. Row permutation and mapping insertion order do not change serialization.
8. Technical passage retains `applicability="not_assessed"` and the canonical
   practitioner-review statement; approval/compliance wording is rejected.
9. Failures raise `DataValidationError` with ordered issues, no partial result,
   and all legacy exception attributes.
10. `ValidationSummary`, all Epic 1.3 properties, and reason strings remain
    compatible.
11. `AuditResult` JSON/JSON Schema cover layered results, unknown-field
    rejection, deterministic round trips, and migration fixtures.
12. All Epic 1.1–1.3 tests pass on Python 3.11/3.12 and `git diff --check` passes.

The implementation PR must link every criterion to a named automated test. Any
contract change requires matching documentation and tests. Epic 2 cannot begin
until Epic 1.4 is implemented and independently reviewed.
