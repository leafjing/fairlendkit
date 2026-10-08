# Audit result and report schema

`AuditResult` schema version `1.0` is the currently implemented
renderer-neutral result contract. HTML, JSON, and CSV renderers consume this
model and must not receive
raw outcomes, decisions, scores, or weights. They format already-computed values
and never recompute metrics.

## Required top-level sections

- `metadata`: SHA-256 input fingerprint, package version, timezone-aware
  generation timestamp, and the complete validated `AuditConfig`.
- `validation`: input/analyzed row counts, typed exclusions, and warnings.
- `observed_metrics`: final metric values, calculation evidence, sample counts,
  and explicit group direction.
- `screening_flags`: typed practitioner-review prompts with a finite observed
  value, finite threshold, and comparison condition. A flag cannot encode a
  pass/fail or compliance status.
- `uncertainty`: method, confidence level, bounds, and resample count linked to
  an observed metric key.
- `limitations`: identified data or methodological boundaries.
- `practitioner_review_notes`: explicitly human-authored notes, with author,
  timestamp, and `source="practitioner"`.

Every section is required even when represented by an empty list. This keeps
all renderer outputs structurally consistent.

## Metric values and undefined reasons

Observed values use `ReportedMetricValue`. A defined result contains a finite
numeric `value` and `undefined_reason=null`. An undefined result contains
`value=null` and a required typed `UndefinedReason` object. Numeric zero remains
a defined value.

`UndefinedReasonCode` is a closed enumeration aligned with the canonical
undefined-reason vocabulary. Each code maps to exactly one fixed neutral
message; mismatched or arbitrary free text fails validation. Renderers must
reproduce the stored code and message and must not invent an interpretation.
Adding or changing a code or canonical message requires Schema version review.

Milestone 3 advances the schema to `2.0` to add metric reliability, new metric
names, typed limitation-to-metric references, and new undefined reasons. Version
`1.0` remains a strict legacy read contract and is migrated explicitly; the
migration must not infer reliability that the old payload did not record. The
behavioral contract, migration rules, and compatibility-alias rule are defined in
[`milestone-3-core-audit-engine.md`](milestone-3-core-audit-engine.md). Slice
3.1 must update this document and the generated schema together with the model;
this cross-reference does not claim those fields are already implemented.

In 2.0, `ObservedMetric.reliability` is required. Native `run_audit` results use
`reliable`, `unreliable`, `undefined`, or `not_applicable`; migrated 1.0 results
use `not_assessed` because legacy payloads do not contain enough evidence to
reconstruct the gate decision. Undefined and not-applicable state takes
precedence and receives no reliability limitation.

In 2.0, `Limitation.related_metric_keys` is also required. Native results use a
non-empty, unique, canonically ordered tuple whose keys resolve to
`observed_metrics`; migrated 1.0 limitations use an empty tuple with the fixed
meaning “relationship absent from the legacy schema.” One metric may be linked
from multiple limitations. Comparison metrics merge source limitation codes in
the fixed order defined by the Milestone 3 reliability matrix.

`StatisticalUncertainty` remains linked to one metric key. Its deterministic
2.0 production is guarded by the Milestone 3 bootstrap golden fixture, which
fixes the SHA-256 counter preimage and rejection sampler, stream names, the
first three sampled index arrays, valid-resample counts, `linear` quantiles,
and final bounds. A failed
valid-resample gate emits a linked limitation instead of an interval.

## Group direction

Single-group metrics use `group`. AIR, demographic parity difference, and equal
opportunity difference require both `comparison_group` and `reference_group`
and reject the undirected `group` field. Metric keys are unique and uncertainty
or screening records may reference only keys present in `observed_metrics`.
The result model revalidates each defined value against its metric range; it
cannot rely only on the upstream calculation function. A defined metric also
requires a positive `sample_count`.

## Exclusions and warnings

Exclusion counts must reconcile exactly:

`analyzed_rows + sum(exclusion.count) == input_rows`

Warnings contain stable codes and factual messages. Automated warning and
limitation text rejects compliance or legal verdict phrasing. Screening flags
always require practitioner review; no `compliance_status`, automated verdict,
or pass/fail field exists in the contract. Human review notes remain visibly
separate and attributable.

Epic 1.4 replaces the flat validation presentation with the
[layered validation contract](epic-1.4-layered-validation-results.md). During
V1, `analyzed_rows` aliases `eligible_rows`; exclusion records reconcile the
de-duplicated excluded total, while overlapping per-reason hit counts remain
separate. The embedded result exposes all four layers, technical status, and
`applicability="not_assessed"` without implying fitness for use.

## Versioning and serialization

The currently implemented `schema_version` is required and fixed to `"1.0"`.
Milestone 3 changes the writer version to `"2.0"` and retains a strict 1.0
reader plus the migration defined above. Pydantic's generated JSON Schema is the
normative machine-readable equivalent of each version and is tested for version
constants, required sections, strict unknown-field rejection, migration, and
JSON round trips. Any later breaking field or semantic change requires another
schema version and migration notes.

The synthetic example at `examples/synthetic/audit-result.json` contains no
real applicant, lender, or proprietary data.
