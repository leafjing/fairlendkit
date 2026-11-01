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

## Result contract

Each threshold point records:

- threshold and inclusive operator;
- overall accuracy, selection rate, TPR, FPR, FNR, and precision;
- the existing per-group values for the same applicable metrics;
- existing directed comparisons: AIR, selection-rate difference, equal
  opportunity difference, and equalized-odds gap;
- numerator, denominator, undefined reason, reliability, and uncertainty links
  using the existing metric contracts; and
- stable metric keys containing a canonical threshold identity.

The scan result also records the candidate policy, evaluated population count,
weights-used indicator, score direction, reference groups, and limitations.

## Frontier contract

A point is frontier-eligible only when the configured utility metric and every
configured fairness measure are defined and reliable. The first release uses:

- utility axis: overall accuracy, maximized;
- fairness-cost axes: `abs(selection_rate_difference)`,
  `abs(equal_opportunity_difference)`, and `equalized_odds_gap`, minimized;
- AIR is displayed but is not transformed into a frontier axis because distance
  around parity is not symmetric under the directed ratio.

A point is dominated when another eligible point is no worse on every active
axis and strictly better on at least one. Equal-axis duplicates remain distinct
threshold points but receive the same dominance state. Undefined or unreliable
points are retained in the scan and marked frontier-ineligible; they are never
silently dropped.

The frontier is descriptive. Ordering, highlighting, and exports must not name
any point “best”, “optimal”, “recommended”, or “compliant”.

## Package and dependency shape

Create `fairlendkit.thresholds` with domain contracts, scan calculation, and
frontier construction. It may depend on configuration and metric-domain
contracts. It must not depend on CLI, pandas, or report renderers.

`application.py` owns orchestration from the validated dataframe into immutable
threshold-domain inputs. Report models expose a new versioned threshold section;
JSON, CSV, and HTML render that section from the same typed result.

## Delivery slices

1. **5.0 — contracts:** configuration, typed point/frontier models, stable
   threshold identity, validation invariants, and schema-version decision.
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
