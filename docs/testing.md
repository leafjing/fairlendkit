# Testing and Independent Verification

## Purpose

This plan defines the evidence required to approve Phase 0 contracts and later
implementations. Verification is performed against the documented metric,
configuration, and report contracts. The reviewer must not implement the code
under review.

## Test layers

### Unit tests

- Use small, hand-calculated fixtures for every metric and disparity measure.
- Assert the numerator, denominator, group count, point estimate, confidence
  interval, and warning or undefined state separately.
- Test semantic validation for favorable labels, score direction, decision
  meaning, protected attributes, and explicit reference groups.
- Test serialization and deserialization of every public configuration and
  result field.

### Property tests

Use generated valid inputs to check invariants where the contract defines them:

- Rates and confidence bounds remain within their documented domains.
- Permuting row order does not change results.
- Duplicating every row preserves point estimates while changing counts.
- Reversing a group comparison changes disparity differences consistently and
  reciprocates ratios only where both denominators are defined and non-zero.
- Threshold results are deterministic and follow the declared score direction.

Property tests supplement explicit examples; they do not replace fixtures for
undefined values, warnings, or report language.

### Golden-file tests

- Maintain a versioned synthetic input, configuration, and expected
  `AuditResult` JSON document.
- Compare structured values rather than unstable HTML details such as generated
  IDs or timestamps.
- Require an explained fixture update when an intentional contract change alters
  expected output.
- Verify that HTML, JSON, and CSV exports agree with the same `AuditResult` and
  that renderers do not recompute metrics.

### Integration tests

Run the documented CLI command from a clean environment and verify its exit
status, output filenames, schemas, metadata, data fingerprint, warnings, and
cross-format consistency. Invalid configurations and input data must fail with
actionable errors and must not leave a plausible-looking partial audit report.

### Regression tests

Every corrected defect receives a minimal test. Permanent regression coverage
is required for favorable-label inversion, score-direction inversion,
reference-group reversal, missing-value handling, group-order instability, and
undefined-versus-zero confusion.

## Verification matrix

| Case | Expected evidence |
| --- | --- |
| Zero reference-group selection rate (AIR denominator) | AIR is explicitly undefined, never infinity, zero, or a compliance conclusion; both groups' counts and selection rates and the warning are preserved. |
| Zero comparison-group selection rate with non-zero reference-group rate | AIR is the valid value `0`, not undefined; the comparison direction, both groups' counts, and both selection rates are preserved. |
| No favorable decisions | Selection rate is the valid value `0`; AIR follows its group-rate denominator policy and remains distinct from outcome-conditioned metrics. |
| No favorable outcomes | True-positive-related metrics follow their outcome-conditioned denominator contracts; undefined values are distinct from zero and from decision-based selection rates. |
| No unfavorable outcomes | False-positive-related metrics follow their outcome-conditioned denominator contracts; undefined values are distinct from zero and from decision-based selection rates. |
| Threshold `0` and `1` | Boundary inclusion matches the declared operator and score direction; decisions and counts are hand-checked. |
| Missing protected group or reference group | Validation fails when the configured reference is absent; missing values follow the documented include/exclude policy and exclusions are counted. |
| Tiny groups | Counts are reported and comparisons are warned or suppressed at the configured minimum; no confident screening claim is emitted. |
| Severe class or group imbalance | Metrics retain correct denominators and uncertainty; warnings prevent point estimates from appearing conclusive. |
| Multiple protected attributes | Each configured attribute is evaluated without overwriting another attribute's groups or metadata. |
| Intersectional slices | Cartesian labels, counts, missing values, and minimum-size safeguards are deterministic and traceable. |
| Favorable-label reversal | Recomputed outcomes match hand calculations; cached or stale values cannot survive the semantic change. |
| Score-direction reversal | Threshold ordering and favorable decisions reverse consistently without silently changing labels. |
| Reference-group reversal | Differences change sign and ratios follow the documented direction; report labels identify the reference explicitly. |
| Bootstrap edge cases | Seeded runs are reproducible; degenerate samples and insufficient valid replicates produce documented warnings. |
| Serialization round trip | Configuration and result values, undefined states, warnings, and metadata survive JSON round trips without semantic loss. |

Each implemented metric must map its applicable rows in this matrix to named
tests. A test may cover multiple rows, but an unchecked row requires an explicit
issue and blocks approval when it affects the PR.

## Evidence required before approval

A PR is approvable only when all applicable evidence is present:

1. The linked issue and acceptance criteria identify the contract being changed.
2. Hand calculations or an authoritative reference establish expected metric
   values independently of the implementation.
3. New and existing automated tests pass on supported Python versions in CI.
4. Boundary and failure-path tests cover every applicable matrix row.
5. Schema changes include compatibility impact, examples, and golden-file
   updates; unexplained snapshot regeneration is insufficient.
6. CLI or report changes include an end-to-end artifact comparison and confirm
   cross-format consistency.
7. The PR contains no confidential data or artifacts and uses only synthetic,
   public, or properly licensed fixtures.
8. Documentation, tests, and code use the same metric names, directions,
   reference groups, missing-data rules, and versioned definitions.
9. Any unresolved ambiguity or known limitation is linked to an issue and is not
   hidden by a default, warning suppression, or renderer behavior.

## Review gates

### Methodology gate

Block approval if a metric lacks a documented population, numerator,
denominator, direction, undefined-state policy, reference-group convention, or
uncertainty method. Also block when favorable-outcome or score semantics are
implicit, missing data is silently dropped, small groups bypass safeguards, or
proxy association is presented as causation.

### Report-language gate

Observed metrics, screening flags, statistical uncertainty, limitations, and
practitioner notes must remain visibly separate. Automated output must not label
an entity `compliant`, `non-compliant`, `legal`, or `illegal`. The four-fifths
rule is a screening heuristic, and proxy-risk indicators are statistical
associations; neither may be phrased as proof. Counts, exclusions, reference
groups, uncertainty, and applicable warnings must accompany findings.

### Independence gate

The reviewer may add review documentation, independent fixtures, and
black-box verification, but must not author or repair the production
implementation being approved. Required implementation changes are returned to
the programmer through PR comments or linked issues, then independently
re-tested after revision.
