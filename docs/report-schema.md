# Audit result and report schema

`AuditResult` schema version `1.0` is the canonical renderer-neutral result
contract. HTML, JSON, and CSV renderers consume this model and must not receive
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

## Versioning and serialization

`schema_version` is required and fixed to `"1.0"`. Pydantic's generated JSON
Schema is the normative machine-readable equivalent contract and is tested for
the version constant, required sections, strict unknown-field rejection, and
JSON round trips. A breaking field or semantic change requires a new schema
version and migration notes.

The synthetic example at `examples/synthetic/audit-result.json` contains no
real applicant, lender, or proprietary data.
