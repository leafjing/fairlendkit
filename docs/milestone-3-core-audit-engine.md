# Milestone 3 — Core Audit Engine and Reliability Contract

## Status and purpose

This document is the normative implementation contract for Milestone 3. It
connects the existing input-validation, metric-primitive, and `AuditResult`
contracts through one deterministic public use case. Existing implemented
contracts remain authoritative where linked; any implementation change needed
by this milestone must update those contracts, the generated schema, fixtures,
and tests in the same pull request.

Milestone 3 is complete only when a caller can submit one pandas `DataFrame`
and one validated `AuditConfig` and receive a complete, internally consistent
`AuditResult`. The result is descriptive screening evidence. It is not an
automated decision about fairness, legality, or regulatory compliance.

## Public API

The package root must export exactly one high-level audit entry point:

```python
import pandas as pd

from fairlendkit import AuditConfig, AuditResult, run_audit


def run_audit(data: pd.DataFrame, config: AuditConfig) -> AuditResult:
    """Validate one dataset and assemble one complete audit result."""
```

The call contract is:

- `data` must be a pandas `DataFrame`; other objects raise `TypeError`.
- `config` must be a fully validated, immutable `AuditConfig`; other objects
  raise `TypeError`. Configuration-validation errors occur when constructing
  `AuditConfig`, before `run_audit` begins.
- Structural or semantic validation failure raises the existing typed input
  validation exception and produces no partial `AuditResult`.
- Analytical reliability and data-quality warnings do not raise. They are
  represented by typed metric states, validation issues, and limitations.
- The input frame, its index, columns, values, dtypes, and metadata must not be
  mutated. Internal working frames must be copies or derived immutable views.
- The function performs no file, network, renderer, CLI, notebook, governance,
  or mitigation side effects.
- Every invocation returns schema-valid `AuditResult` version `2.0`. Milestone
  3 is the documented schema review that introduces this version; version
  `1.0` remains a supported legacy input as described below.

`run_audit` owns this fixed orchestration order:

1. validate configuration type and dataframe type;
2. run the existing layered validation and eligibility rules;
3. stop on failed structural or semantic validation;
4. normalize favorable outcome, favorable decision, favorable probability,
   and optional weight semantics from `AuditConfig`;
5. calculate overall and per-group metrics;
6. calculate directed comparisons against each explicit reference group;
7. classify metric reliability and generate eligible screening flags;
8. calculate seeded bootstrap intervals where applicable;
9. assemble and cross-validate the complete `AuditResult`.

Renderers remain consumers of `AuditResult` and must never call metric
primitives or recompute results.

## Required configuration additions

Milestone 3 adds the following immutable `AuditConfig` fields:

- `bootstrap_seed: int = 0`, inclusive range `0` to `2**64 - 1`: seed for the
  SHA-256 counter sampler. The global NumPy or Python random state must not be
  read or changed.
- `bootstrap_resamples: int = 1000`, minimum `1`: requested bootstrap draws.
- `minimum_valid_resamples: int = 800`, minimum `1` and no greater than
  `bootstrap_resamples`: minimum defined draws required to emit an interval.
- `air_screening_threshold: float = 0.8`, finite and strictly greater than
  `0`: documented screening threshold for AIR.

`confidence_level` and `minimum_group_size` retain their existing meanings.
These values are serialized in `RunMetadata.configuration`; no hidden runtime
default may affect a result.

## Population and grouping contract

### Overall and single-attribute groups

Metrics are calculated on the eligible rows produced by the existing validation
contract. The overall group is represented by the reserved audit-group value
`{"__scope__": "overall"}`. For each protected attribute, the engine emits one
single-attribute group for every configured allowed value, including an allowed
value with zero eligible rows. This makes an absent configured group explicit
rather than silently dropping it.

Milestone 3 does not calculate intersections across protected attributes. A row
may contribute to its overall metric and to one group for each configured
protected attribute. This is intentional and must not be described as duplicate
evidence within a single comparison.

Group labels retain their original type. Values such as `1`, `"1"`, and `True`
must not be merged. Group equality uses the existing type-sensitive configuration
rules.

### Comparison direction

For each protected attribute, every non-reference allowed value is a comparison
group and `reference_groups[attribute]` is the reference group. The direction is
always:

```text
comparison rate / reference rate
comparison rate - reference rate
```

The reference group is not compared with itself. Reversing the configured
reference group must reverse difference direction and invert AIR when both
selection rates are positive. The result must preserve explicit
`comparison_group` and `reference_group` objects.

### Stable ordering and metric keys

Output order is independent of dataframe row order, hash order, locale, and
dictionary insertion order:

1. overall metrics in the metric order defined below;
2. protected attributes sorted by column name;
3. group values sorted by the canonical typed token
   `<type-name>:<canonical-json-value>`;
4. within each group, metrics in the metric order below;
5. directed comparisons in comparison-group canonical order.

Metric keys use lowercase ASCII identifiers. Attribute names and typed group
values are encoded as `<type>-<lowercase-hex>`, where the hex payload is the
UTF-8 encoding of the value's canonical JSON representation. Attribute names
use the fixed `str` type. This encoding stays within the existing `Identifier`
pattern and prevents type collisions:

```text
overall.<metric>
group.<encoded-attribute>.<typed-value>.<metric>
comparison.<encoded-attribute>.<typed-comparison>.vs.<typed-reference>.<metric>
```

The typed value prefix is one of `str`, `int`, `bool`, or `float`; null is not a
group value after eligibility processing. For example, string `"A"` becomes
`str-224122`, while integer `1` becomes `int-31`. Implementations must expose
one tested canonical key builder rather than reproduce this encoding in callers.

## Metric applicability matrix

The canonical metric order is the order shown here. All rates and confusion
matrix terms use normalized favorable semantics: positive outcome means
`outcome == favorable_label`, and positive decision means the configured
favorable decision. Optional weights use the existing normalization contract.

| Metric | Formula | Scope | Applicability and typed undefined behavior |
| --- | --- | --- | --- |
| `selection_rate` | `(TP + FP) / N` | overall, group | Undefined for empty population or zero total weight. |
| `denial_rate` | `(TN + FN) / N`, equivalently `1 - selection_rate` | overall, group | Same denominator state as selection rate. “Denial” means the configured unfavorable decision. |
| `accuracy` | `(TP + TN) / N` | overall, group | Undefined for empty population or zero total weight. |
| `precision` | `TP / (TP + FP)` | overall, group | Undefined when there are no favorable decisions or their total weight is zero. |
| `true_positive_rate` | `TP / (TP + FN)` | overall, group | Undefined when there are no favorable outcomes or their total weight is zero. |
| `false_positive_rate` | `FP / (FP + TN)` | overall, group | Undefined when there are no unfavorable outcomes or their total weight is zero. |
| `false_negative_rate` | `FN / (TP + FN)` | overall, group | Same denominator state as true-positive rate. |
| `brier_score` | weighted mean of `(p_favorable - y_favorable)^2` | overall, group | Only for `score_type="probability"`; otherwise `metric_not_applicable`. Undefined for empty population or zero total weight. Probability orientation follows `score_direction`: lower-is-more-favorable input is transformed to `1 - score`. |
| `roc_auc` | weighted probability that a favorable outcome ranks more favorable than an unfavorable outcome, with ties worth `0.5` | overall, group | Undefined for no favorable outcomes, no unfavorable outcomes, corresponding zero class weight, or constant eligible score. Ranking order follows `score_direction`. |
| `selection_rate_difference` | comparison selection rate minus reference selection rate | comparison | Undefined if either source metric is undefined. This is the canonical name; it supersedes the older alias `demographic_parity_difference`. |
| `adverse_impact_ratio` | comparison selection rate divided by reference selection rate | comparison | Undefined if either input is undefined or defined reference rate is zero. |
| `demographic_parity_difference` | comparison selection rate minus reference selection rate | comparison | Required 2.0 compatibility alias for the name exposed by schema 1.0; value and evidence must exactly equal `selection_rate_difference`. It must not produce a second flag. |
| `equal_opportunity_difference` | comparison TPR minus reference TPR | comparison | Undefined if either source metric is undefined. |
| `equalized_odds_gap` | `max(abs(TPR_c - TPR_r), abs(FPR_c - FPR_r))` | comparison | Undefined if any of the four source rates is undefined. Non-negative; direction remains visible in the component rates. |

`N`, numerator, and denominator mean normalized weight units when weights are
configured and record counts otherwise. `sample_count` always remains the
unweighted eligible row count.

Metric primitives must reject invalid arrays, non-finite values, mismatched
lengths, and values outside their declared domain. Such programmer/input
contract violations are not converted into undefined metrics.

## Metric state and reliability

Undefined and unreliable are distinct states:

- **defined and reliable**: finite value, applicable metric, and sufficient
  support; may be eligible for uncertainty and a screening flag;
- **defined but unreliable**: finite descriptive value, but the group is below
  `minimum_group_size`, is severely imbalanced, or fails another documented
  reliability gate; value is retained but no screening flag is allowed;
- **undefined**: calculation has no valid denominator or required class support;
  `value=null` and a canonical `UndefinedReason` is required;
- **not applicable**: the metric does not apply to configured score semantics;
  represented as an undefined value with `metric_not_applicable`;
- **invalid input**: structural/semantic data or primitive-contract failure;
  the audit stops and is not represented as a metric state.

`ObservedMetric` therefore gains a required `reliability` field with values
`reliable`, `unreliable`, `undefined`, `not_applicable`, or `not_assessed`. The
state must agree with the value and reason. New 2.0 computations use the first
four states: defined values can be reliable or unreliable; undefined values
must use `undefined` or `not_applicable`. `not_assessed` is reserved solely for
migrated 1.0 payloads and must never be emitted by `run_audit`.

The canonical undefined-reason vocabulary must be extended with:

- `no_favorable_decisions` and `zero_favorable_decision_weight` for precision;
- `constant_score` for AUC without rank variation;
- `metric_not_applicable` for score-type applicability;
- `component_metric_undefined` for a compound metric such as equalized odds;
- `insufficient_valid_resamples` for uncertainty only, never as the observed
  metric's reason.

Reliability limitations use stable codes:

- `small_group`: unweighted group count is below `minimum_group_size`;
- `severe_outcome_imbalance`: either the favorable or unfavorable outcome
  class has an unweighted count below `minimum_group_size` within the evaluated
  scope;
- `sparse_decision_support`: favorable-decision support is below
  `minimum_group_size` for precision; the unfavorable-decision count does not
  affect precision reliability;
- `insufficient_valid_resamples`: fewer than `minimum_valid_resamples`
  bootstrap draws produced a defined finite value.

A gate applies to metrics exactly as follows. `D+` means the unweighted
favorable-decision count. A check written `count < minimum_group_size` is a
reliability warning, not an undefined denominator test.

| Metric | `small_group` | `severe_outcome_imbalance` | `sparse_decision_support` |
| --- | --- | --- | --- |
| `selection_rate`, `denial_rate` | applies | ignored | ignored |
| `accuracy` | applies | applies | ignored |
| `precision` | applies | ignored | applies when `D+ < minimum_group_size` |
| `true_positive_rate`, `false_positive_rate`, `false_negative_rate` | applies | applies | ignored |
| `brier_score`, `roc_auc` | applies | applies | ignored |
| `selection_rate_difference`, `adverse_impact_ratio`, `demographic_parity_difference` | merge both source selection-rate limitations | ignored | ignored |
| `equal_opportunity_difference` | merge both source TPR limitations | merge both source TPR limitations | ignored |
| `equalized_odds_gap` | merge both source TPR and FPR limitations | merge both source TPR and FPR limitations | ignored |

“Applies” means a defined metric is `unreliable` when the gate is active.
Overall scope and each single-attribute group use the same matrix. The outcome
imbalance gate is one condition: if either outcome class is below the minimum,
every metric marked `applies` receives that limitation; it is not split into
favorable- and unfavorable-support variants.

State precedence is `invalid input` (stop the audit), then `not_applicable` or
`undefined`, then reliability gates. An undefined or not-applicable metric does
not receive a reliability limitation, even when its scope also activates a
gate. This avoids attaching a sample-strength judgment to a value that does not
exist.

A defined metric may be associated with multiple active limitations. De-duplicate
its limitation codes, then preserve this fixed gate order:
`small_group`, `severe_outcome_imbalance`, `sparse_decision_support`,
`insufficient_valid_resamples`. The first three determine point-estimate
reliability; `insufficient_valid_resamples` describes only the missing interval
and does not change a reliable point estimate to unreliable.

For a comparison metric, collect the limitations attached to every source
metric named in the matrix, take the stable union by code, and attach all codes
to the comparison metric in the same fixed order. A comparison is reliable only
when it is defined and every source metric is reliable. Source limitations
remain attached to their source metrics; merging does not remove or reorder
them.

The result emits one limitation record per `(code, scope)`, with every affected
defined metric key in canonical metric order. Limitations are ordered by scope
in canonical group/comparison order and then by the fixed gate order above.
Duplicate codes within a scope and duplicate metric keys within a limitation
are invalid.

A limitation must identify affected metric keys through the new required
`related_metric_keys: tuple[Identifier, ...]` field. For a result produced by
`run_audit` it must be non-empty, unique, canonically ordered, and resolve to
observed metrics; implementations must not encode key relationships only in
prose. The empty tuple has the legacy migration meaning defined below.

## Screening flags

Milestone 3 emits only the AIR screening flag:

```text
code: air_below_threshold
condition: below
threshold: config.air_screening_threshold
```

The flag is emitted only when AIR is defined and finite, both source selection
rates are `reliable`, AIR itself is therefore `reliable`, and
`AIR < air_screening_threshold`. Equality does not trigger it. Undefined,
not-applicable, or unreliable metrics never generate a flag. The flag references
the AIR metric key and retains `requires_practitioner_review=true`.

No other metric produces a screening flag in this milestone. In particular,
differences, AUC, Brier score, and equalized-odds gap remain descriptive until a
separate documented threshold contract is approved. A missing flag is never a
pass or compliance conclusion.

## Uncertainty contract

Milestone 3 uses the following fully specified nonparametric percentile
bootstrap. It is a SHA-256 counter sampler and does not depend on a language or
numerical library random-number generator. “SHA-256” means the FIPS 180-4 hash,
all text is UTF-8, and all unsigned integers use fixed-width big-endian encoding:

- resample eligible rows with replacement within the evaluated scope;
- use exactly `bootstrap_resamples` attempted draws;
- encode `bootstrap_seed` as exactly eight unsigned big-endian bytes;
- use stream name `overall` for overall metrics, `group` for single-group
  metrics, and the two independent stream names `comparison` and `reference`
  for the corresponding sides of a directed comparison;
- encode `metric_key` and `stream_name` as their UTF-8 bytes, each preceded by
  its byte length as an unsigned 32-bit integer; this prevents concatenation
  ambiguity;
- for zero-based draw `d`, zero-based sampled position `p`, and zero-based
  rejection counter `r`, form
  `b"fairlendkit-bootstrap-v1\x00" + seed_u64 + key_len_u32 + key_bytes +
  stream_len_u32 + stream_bytes + d_u64 + p_u64 + r_u32`;
- hash that byte string and interpret the first eight digest bytes as unsigned
  integer `x`; for population size `n`, let `limit = floor(2**64 / n) * n`;
  accept `x` when `x < limit` and select source row position `x % n`, otherwise
  increment `r` and hash again;
- reject `n == 0` before sampling; counters must fit their stated widths or the
  configuration/input is invalid;
- generate draws in increasing `d`, positions in increasing `p`, and rejection
  attempts in increasing `r`; no mutable random stream is shared between keys
  or comparison sides;
- for directed comparisons, resample comparison and reference groups from their
  separately derived streams, preserving each original group size;
- apply configured sample weights as metric weights after row resampling; the
  weights are not also used as sampling probabilities;
- discard draws in which the metric is undefined or non-finite;
- sort the `m` valid draw values as `v[0] <= ... <= v[m-1]`; for either target
  quantile `q`, set `h = (m - 1) * q`, `i = floor(h)`, `j = ceil(h)`, and return
  `v[i] + (h - i) * (v[j] - v[i])`. Use target quantiles
  `(1 - confidence_level) / 2` and `1 - (1 - confidence_level) / 2`. This is
  the precisely defined linear quantile method and does not delegate semantics
  to a library default;
- record the number of valid draws, not merely attempted draws.

Intervals are emitted only for defined, reliable numeric metrics with at least
`minimum_valid_resamples` valid draws. If this gate fails, no
`StatisticalUncertainty` record is emitted and a typed
`insufficient_valid_resamples` limitation references the metric key. Bootstrap
failure must never fabricate `[0, 0]`, copy the point estimate into both bounds,
or silently lower the requested confidence level.

Each uncertainty record references exactly one observed metric key. Duplicate
uncertainty records for one key are invalid. Bounds must respect the metric's
declared range. Compatibility-alias `demographic_parity_difference` does not
receive a duplicate interval; its canonical `selection_rate_difference` key
owns the interval.

The test suite must include a checked-in golden bootstrap fixture containing
the config seed, canonical metric keys, sampled row-index arrays for the first
three draws of every stream kind, valid-resample counts, and final interval
bounds. The fixture is the cross-implementation compatibility oracle; changing
the hash preimage, integer widths/byte order, rejection rule, counter order, or
quantile method is a versioned method change.

## Schema 2.0 and legacy migration

Milestone 3 changes `AUDIT_RESULT_SCHEMA_VERSION` from `1.0` to `2.0`. Version
2.0 makes `ObservedMetric.reliability` and `Limitation.related_metric_keys`
required and adds the metric and undefined-reason enum members listed above.
This is intentionally not represented as a backward-compatible 1.0 change.
No public schema version 1.1 exists; the earlier PR draft was never released
and is superseded by this 2.0 contract.

The package must retain an explicit `AuditResultV1_0` parser and provide
`migrate_audit_result_v1_0(payload) -> AuditResult` with these deterministic
rules:

- preserve metadata, validation, observed values, flags, uncertainty,
  limitations, and practitioner notes without recomputation;
- set every legacy observed metric's reliability to `not_assessed`, because a
  1.0 payload lacks sufficient evidence to reconstruct historical gates;
- set every legacy limitation's `related_metric_keys` to the empty tuple;
- preserve legacy metric names; migration does not synthesize new Milestone 3
  metrics or uncertainty;
- set `schema_version` to `2.0`, then validate all references and legacy value
  ranges under the 2.0 model;
- reject unknown source versions and reject a payload that fails the strict
  1.0 parser before migration.

The 2.0 wire schema accepts `not_assessed` and an empty
`related_metric_keys` tuple so migrated results can make an exact JSON round
trip. Their stable meaning is “evidence absent from schema 1.0”; they must not
be defaulted for missing 2.0 fields. The `run_audit` assembler applies the
stronger native-production invariant and rejects either value. Consumers must
display migrated reliability honestly and must not reinterpret `not_assessed`
as reliable or unreliable.

Compatibility tests require: a checked-in 1.0 golden payload; strict 1.0 parse;
1.0→2.0 migration; exact 2.0 round trip; rejection by the 2.0 parser of missing
new fields; enforcement of the stronger `run_audit` production invariant; and
proof that migrating an already migrated payload is rejected rather than
silently repeated. Version 1.0 remains readable but
`run_audit` only writes 2.0.

## Result assembly and reproducibility

The assembler must populate every required `AuditResult` section, including
empty tuples. It must enforce:

- validation counts reconcile with eligible and excluded rows;
- every metric key is unique and canonically ordered;
- every uncertainty record, flag, and limitation metric reference resolves;
- aliases contain identical point estimates and evidence;
- generated metadata uses the existing deterministic input fingerprint;
- the caller-supplied `execution_timestamp` is used as `generated_at`; wall
  clock time must not enter the result;
- practitioner notes are empty because computation cannot author human notes.

Canonical JSON means `model_dump_json()` using the project's documented fixed
serialization options and stable tuple order. Given equal dataframe content,
column order, index, `AuditConfig`, package version, and environment-independent
numeric dependencies, two runs must produce byte-for-byte identical canonical
JSON. Row order is part of the input fingerprint, but metric values must remain
invariant to row permutation; a permuted input may therefore differ only in
fingerprint and any bootstrap sequence explicitly derived from that fingerprint.

## Acceptance matrix

Each row is a release gate and requires an independently readable fixture or
test. A green aggregate test count does not replace these cases.

| Case | Required evidence |
| --- | --- |
| Hand-calculated metrics | Independent fixture covers every metric, numerator, denominator, range, and direction. |
| Public API | `DataFrame + AuditConfig` returns a complete schema-valid `AuditResult` from the package-root import. |
| Decision source | Observed decision-column and threshold-derived decision cases produce the expected favorable-decision indicators. |
| Label reversal | Re-encoded favorable outcome and decision labels preserve equivalent results. |
| Score direction reversal | Numerically reversed equivalent scores preserve AUC and Brier meaning after orientation. |
| Reference reversal | Differences reverse sign; positive AIR values invert; group direction fields and keys change correctly. |
| Multiple attributes | Each configured attribute produces its own groups and directed comparisons with deterministic order. |
| Empty and zero-weight groups | Configured absent groups and zero-weight groups emit typed undefined metrics, not zeros or omissions. |
| Sparse outcomes | No-positive and no-negative cases select the exact metric-specific reason codes. |
| Precision support | No favorable decisions and zero favorable-decision weight are distinguished. |
| Small groups | Values may remain descriptive but reliability is `unreliable`, limitations are linked, and no flag is emitted. |
| Severe imbalance | Either outcome class below the minimum marks every matrix-selected defined metric unreliable. |
| Multiple gates | One defined metric retains all applicable limitation codes in fixed gate order without duplicates. |
| Undefined precedence | Undefined/not-applicable metrics retain their typed reason and receive no reliability limitation. |
| Comparison inheritance | Each comparison merges all source limitation codes once and in fixed order. |
| AIR boundary | Values below `0.8` flag only when AIR and both selection rates are reliable; `0.8`, unreliable, and undefined values do not. |
| Bootstrap success | Golden fixture fixes the first three index draws for every stream kind, bounds, and valid-resample count. |
| Bootstrap insufficiency | Too few valid draws produces a linked typed limitation and no interval. |
| Deterministic JSON | Repeated identical calls produce byte-identical canonical JSON. |
| Input immutability | Deep equality, index, columns, dtypes, and dataframe metadata are unchanged after success and failure. |
| Failure boundary | Structural/semantic invalidity raises before any metrics or partial result is exposed. |
| Schema integrity | Unknown fields, duplicate keys/references, invalid ranges, and contradictory reliability states are rejected. |
| Runtime support | Full suite passes on Python 3.11 and 3.12; `git diff --check` passes. |
| Independent review | Reviewer reproduces at least label, reference, small-group, sparse-class, and bootstrap edge cases. |

## Delivery slices

- **3.0 — contract:** this document, linked canonical contracts, review, and
  approved schema-impact list.
- **3.1 — metric primitives:** denial rate, precision, AUC, selection-rate
  difference, equalized-odds gap, typed undefined reasons, and hand fixtures.
- **3.2 — group orchestration:** overall/group calculation, comparison
  direction, canonical ordering, and metric keys.
- **3.3 — reliability and uncertainty:** reliability states, limitation links,
  screening gate, and seeded bootstrap.
- **3.4 — assembler:** public `run_audit`, complete `AuditResult`, deterministic
  serialization, immutability, and end-to-end tests.
- **3.5 — release gate:** README capability truth, complete examples, Python
  3.11/3.12 CI, diff check, and independent review.

Each slice must be independently reviewable and must not claim later-slice
capabilities in the README.

## Explicit non-goals

Milestone 3 does not include:

- threshold scanning or a fairness-accuracy frontier;
- intersectional group expansion;
- HTML or CSV rendering, or renderer presentation design;
- a CLI or notebook workflow;
- proxy-risk screening;
- governance-system integration, review disposition, case management, or audit
  workflow automation;
- mitigation, reweighing, threshold recommendations, or model retraining;
- automated legal, fairness, or compliance conclusions.

These belong to Milestones 4–6 or later reviewed scope. JSON serialization of
the canonical result model is part of reproducibility; a user-facing JSON
renderer is not.

## Definition of done

Milestone 3 is complete only when all delivery slices and acceptance rows are
implemented, documented, and independently approved; Python 3.11 and 3.12 CI
and `git diff --check` are green; the README distinguishes implemented and
future capabilities; and one public API deterministically produces a complete
`AuditResult` without mutating input. Documentation or placeholder models alone
do not satisfy this definition.
