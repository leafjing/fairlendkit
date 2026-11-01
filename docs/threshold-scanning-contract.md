# Milestone 5 — threshold scanning and fairness–accuracy frontier

Status: active; architecture contract ready for implementation.

## Outcome

Given one validated audit population and its configured score semantics, scan a
deterministic set of candidate decision thresholds and report how performance,
selection, error, and group-disparity metrics change. Construct a descriptive
fairness–accuracy frontier without selecting, recommending, or automatically
deploying a threshold.

The feature is analysis, not mitigation or a legal/compliance conclusion.

## Boundaries

- Threshold scanning is available only when the score column is present and
  finite after the existing eligibility rules.
- The configured score direction controls the inclusive decision rule:
  `score >= threshold` for higher-is-more-favorable and `score <= threshold`
  for lower-is-more-favorable.
- Observed decisions remain the source of the ordinary audit. Scanned decisions
  are counterfactual analytical results and must be labeled separately.
- Existing metric definitions, group/reference direction, reliability states,
  undefined reasons, weighting semantics, and eligibility population are
  reused without reinterpretation.
- Renderers consume typed scan results and never recompute thresholds, metrics,
  dominance, or flags.

## Candidate set

The first release accepts an explicit, ordered list of finite candidate
thresholds in configuration. Values must be unique after numeric validation and
are evaluated in canonical ascending numeric order. This avoids silently
changing runtime or analytical resolution as dataset size changes.

Automatic grids, quantile grids, per-group thresholds, threshold optimization,
and threshold recommendations are out of scope for the first release. They may
be added later as separate, versioned policies.

## Configuration contract

`AuditConfig` adds one optional field:

```python
threshold_scan: ThresholdScanConfig | None = None
```

`ThresholdScanConfig` is a strict, frozen model with one required field:

```python
candidate_thresholds: tuple[float, ...]  # at least one item
```

Unknown fields are rejected. Boolean values, strings, `NaN`, positive or
negative infinity, and duplicate numeric values are invalid. Positive and
negative zero are the same candidate. Integers in JSON may be accepted through
normal numeric validation and are stored as binary64 values. Validation sorts
the stored tuple in ascending numeric order; callers cannot control evaluation
or serialization order through input order.

The scan is disabled when `threshold_scan` is absent or `null`. Enabling it
does not relax the existing rule that the ordinary audit must configure exactly
one of `decision_column` or `decision_threshold`. That ordinary decision source
continues to produce `observed_metrics` and screening flags. Every scan
candidate instead derives a separate counterfactual favorable-decision vector
from `score_column`; it never overwrites the configured decision source.

Complete JSON excerpt for a higher-is-more-favorable score:

```json
{
  "outcome_column": "repaid",
  "score_column": "creditworthiness_score",
  "score_type": "ranking",
  "favorable_label": 1,
  "score_direction": "higher_is_more_favorable",
  "favorable_decision_label": 1,
  "decision_column": "approved",
  "threshold_scan": {
    "candidate_thresholds": [0.45, 0.55, 0.65]
  }
}
```

The excerpt omits unrelated required provenance and group fields for brevity.
The equivalent Python addition to a complete `AuditConfig` is:

```python
threshold_scan=ThresholdScanConfig(
    candidate_thresholds=(0.45, 0.55, 0.65),
)
```

For `higher_is_more_favorable`, candidate `0.55` means
`score >= 0.55`; for `lower_is_more_favorable`, the same candidate means
`score <= 0.55`. Equality is favorable in both cases. A candidate is not an AIR
screening threshold and must never be described as one.

## Stable threshold identity

Each validated candidate receives an identity independent of candidate order.
Normalize negative zero to positive zero, encode the resulting IEEE-754
binary64 value as eight big-endian bytes, and use the 16 lowercase hexadecimal
digits prefixed by `t`. For example, `0.5` is `t3fe0000000000000`.
Threshold-scoped metric keys use this identity, not a display-rounded decimal
or list position. Adding another candidate therefore cannot rename existing
points. User-facing renderers display the validated numeric threshold and may
also expose the identity for traceability.

## Result contract

`ThresholdScanResult` records the canonical candidate policy, evaluated
population count, weights-used indicator, score direction, reference groups,
points, frontier identities, and scan-level limitations. `ThresholdPoint`
records:

- threshold and inclusive operator;
- overall accuracy, selection rate, TPR, FPR, FNR, and precision;
- the existing per-group values for the same applicable metrics;
- existing directed comparisons: AIR, selection-rate difference, equal
  opportunity difference, and equalized-odds gap;
- numerator, denominator, undefined reason, reliability, and uncertainty links
  using the existing metric contracts; and
- stable metric keys containing the canonical threshold identity;
- `frontier_status`: `frontier`, `dominated`, or `ineligible`; and
- zero or more stable `frontier_ineligibility_reasons`.

The point metric representation reuses the Schema 2.0 value, group direction,
sample-count, undefined-reason, reliability, limitation-link, and uncertainty
contracts. Scan metrics are not inserted into ordinary `observed_metrics`.
Within the threshold section, every metric key is unique, every uncertainty or
limitation link resolves to a point metric, and ordering is candidate, metric,
protected attribute, comparison group, then reference group using the existing
canonical group ordering.

The initial ineligibility reasons are `utility_undefined`,
`utility_unreliable`, `fairness_measure_undefined`, and
`fairness_measure_unreliable`. A reason carries the affected metric keys; free
text alone is not sufficient. A point can carry more than one reason in the
fixed order above.

## Frontier contract

A point is frontier-eligible only when the fixed utility metric and every fixed
fairness measure are defined and reliable. The first release uses:

- utility axis: overall accuracy, maximized;
- fairness-cost axes: `abs(selection_rate_difference)`,
  `abs(equal_opportunity_difference)`, and `equalized_odds_gap`, minimized;
- AIR is displayed but is not transformed into a frontier axis because distance
  around parity is not symmetric under the directed ratio.

For every protected attribute, each non-reference group produces one directed
comparison against that attribute's configured reference group. Every such
comparison contributes its three fairness-cost values as separate active axes.
No maximum, average, or other aggregation across groups or attributes is
silently substituted. Consequently, an undefined or unreliable active value in
any directed comparison makes that threshold point frontier-ineligible.

A point is dominated when another eligible point is no worse on every active
axis and strictly better on at least one. Equal-axis duplicates remain distinct
threshold points but receive the same dominance state. Undefined or unreliable
points are retained in the scan and marked frontier-ineligible; they are never
silently dropped.

The frontier is descriptive. Ordering, highlighting, and exports must not name
any point “best”, “optimal”, “recommended”, or “compliant”.

## Schema and compatibility decision

Milestone 5 introduces `AuditResult` Schema `2.1`. It adds a required nullable
top-level `threshold_scan` section: `null` when scanning is disabled and a
`ThresholdScanResult` when enabled. A native 2.1 writer always emits the field,
so omission is not a second representation of disabled scanning. Strict Schema
2.0 reading remains supported; migration to 2.1 sets `threshold_scan=null` and
does not infer counterfactual results. Schema 1.0 continues through the existing
1.0-to-2.0 migration before the mechanical 2.0-to-2.1 step.

Canonical JSON includes the full typed section. The metrics CSV gains
threshold-scoped rows and explicit `analysis_scope`, `threshold`, and
`threshold_identity` columns in Slice 5.3; ordinary rows use
`analysis_scope=observed` and empty threshold cells. HTML labels the section
“Counterfactual threshold analysis” and keeps it visually separate from the
ordinary audit. Renderers must show ineligible points and reasons rather than
dropping them.

## Package and dependency shape

Create `fairlendkit.thresholds` with domain contracts, scan calculation, and
frontier construction. It may depend on configuration and metric-domain
contracts. It must not depend on CLI, pandas, or report renderers.

`application.py` owns orchestration from the validated dataframe into immutable
threshold-domain inputs. Report models expose a new versioned threshold section;
JSON, CSV, and HTML render that section from the same typed result.

## Delivery slices

1. **5.0 — contracts:** configuration, typed point/frontier models, stable
   threshold identity, validation invariants, and Schema 2.1 models plus
   migration skeleton. No scan calculation is included.
2. **5.1 — scan engine:** inclusive score-to-decision derivation and reuse of
   existing overall/group metric functions, with no report changes.
3. **5.2 — frontier:** deterministic multi-axis dominance and explicit
   ineligibility reasons.
4. **5.3 — integration:** `run_audit`, public API, canonical JSON, metrics CSV,
   self-contained HTML, and CLI workflow.
5. **5.4 — release gate:** hand-calculated fixture, direction reversal,
   reference reversal, weights, ties, sparse groups, undefined/reliability,
   deterministic ordering, architecture checks, golden artifacts, and Python
   3.11/3.12 CI.

## Definition of done

- Every scan value traces to one candidate, population, group direction, metric
  definition, and reliability/uncertainty record.
- Candidate reordering cannot change canonical output bytes.
- Higher/lower score-direction mirror fixtures produce equivalent decisions.
- No renderer or CLI path recomputes analytical values.
- Existing reports without a configured scan remain backward compatible.
- Documentation states that the frontier supports human investigation and does
  not prescribe a lending policy.
- Independent review and the full two-runtime release gate pass before closure.
