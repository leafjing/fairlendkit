# Fairlearn and Aequitas interoperability comparison

Status: `design_only / no_results`

This document defines a reproducible interoperability comparison between
FairLendKit, Fairlearn, and Aequitas. Its purpose is to detect semantic or
implementation differences on the same fixed synthetic rows and to evaluate a
low-friction CSV workflow. It does not treat agreement as proof of correctness,
fairness, compliance, or external validity, and it does not treat disagreement
as proof that any tool is defective.

The first implementation is an isolated development spike. It must not add
Fairlearn or Aequitas to FairLendKit's runtime dependencies, access production
or consumer data, invoke mitigation, or publish a legal conclusion.

## 1. Frozen package identity

Identity checked on 2026-11-02 UTC against official PyPI metadata and official
source repositories:

### Fairlearn

- Package: `fairlearn==0.15.0`
- PyPI: <https://pypi.org/project/fairlearn/0.15.0/>
- Source tag: <https://github.com/fairlearn/fairlearn/tree/v0.15.0>
- License: MIT, as recorded in the official repository
  [LICENSE](https://github.com/fairlearn/fairlearn/blob/v0.15.0/LICENSE)
- Wheel: `fairlearn-0.15.0-py3-none-any.whl`
- Wheel SHA-256:
  `4f4656c25af384fc3369db719231680c4e83beb2e6e075e5dc3c2b27d06455c9`
- Source archive: `fairlearn-0.15.0.tar.gz`
- Source SHA-256:
  `dfdfbddc3b86d2a8e4e04e282bb29d7603f28559a28abeca97847bf5e0f79f80`

### Aequitas

- Package: `aequitas==1.1.0`
- PyPI: <https://pypi.org/project/aequitas/1.1.0/>
- Source tag: <https://github.com/dssg/aequitas/tree/1.1.0>
- License: MIT, as recorded in the official repository
  [LICENSE](https://github.com/dssg/aequitas/blob/1.1.0/LICENSE)
- Wheel: `aequitas-1.1.0-py3-none-any.whl`
- Wheel SHA-256:
  `a99b8031a499577251fb26fae2ff20f2b23b2ad759cc8657b8afaae53bbc0b33`

The implementation must install these artifacts in an isolated, hashed test
environment. A later package release is a new comparison identity and requires
a reviewed manifest update. Unversioned `main`, `master`, hosted demos, and
mutable documentation pages are discovery aids, not the executable baseline.

## 2. Scope and positioning

The comparison has three bounded goals:

1. Cross-check common group metrics after aligning inputs and definitions.
2. Record semantic differences instead of coercing outputs until they match.
3. Measure the user steps needed to run a fixed CSV audit without weakening
   FairLendKit's fail-closed contracts.

Fairlearn is used as a reference for grouped metric organization, control
features, uncertainty workflows, and clearly separated mitigation interfaces.
Aequitas is used as a reference for group audit, explicit reference-group
disparities, and layered audit output. FairLendKit retains its own typed schema,
undefined reasons, reproducibility artifacts, credit-specific interpretation
boundaries, and joint risk/fairness gates.

The spike compares measurement only. Fairlearn reductions,
`ThresholdOptimizer`, Aequitas remediation choices, and any group-specific
threshold policy are out of scope. If studied later, mitigation must have a
separate offline-only contract and must not be presented as proof of legality or
absence of discrimination.

## 3. Canonical fixed input

One checked-in synthetic CSV is the sole row-level input. It contains no real
person, customer, application, or lender data. The manifest freezes:

- ordered columns and data types;
- row count and ordered stable `row_id` values;
- file SHA-256 and ordered-row digest;
- favorable outcome and positive-score direction;
- favorable decision value;
- comparison and reference group values;
- optional control-feature values;
- sample weights when a weighted case is enabled;
- missing and invalid-value fixtures; and
- deterministic generation code and seed, if generated rather than literal.

Canonical semantic fields are:

- `row_id`: stable identity used only for reconciliation;
- `y_true`: binary observed outcome with an explicit favorable value;
- `y_pred`: binary decision or prediction with an explicit favorable value;
- `y_score`: numeric score with declared higher-is-more-favorable direction;
- `sensitive_feature`: group label;
- `control_feature`: optional prespecified stratum, never inferred from outcome;
- `sample_weight`: finite non-negative weight where supported; and
- `is_valid`: fixture-only marker used to assert exclusion behavior.

Adapters may rename or reshape fields for a tool, but they may not alter row
membership, group values, labels, decisions, scores, weights, or missingness.
Every adapter emits its own input digest and row count. A mismatch fails before
metric comparison.

## 4. Functionality map

| Research need | FairLendKit | Fairlearn 0.15.0 | Aequitas 1.1.0 | Comparison rule |
| --- | --- | --- | --- | --- |
| Group metric organization | Typed audit results with configured comparison/reference direction | `MetricFrame` with `sensitive_features`; optional `control_features` | Group/crosstab audit tables by protected attribute | Compare only after identical row and group identity checks. |
| Selection rate | Configured favorable decision divided by group denominator | `selection_rate` under an explicit positive label | Predicted-positive prevalence/group counts | Recompute numerator and denominator independently; names alone are insufficient. |
| Directed AIR | Comparison selection rate divided by configured reference selection rate | A ratio reduction may default to min/max or overall comparison depending on invocation | Disparity ratio relative to a selected reference group | Require an explicit reference group and formula; never equate min/max ratio with directed AIR. |
| TPR/FPR | Uses configured favorable outcome and score/decision semantics | Standard classification metrics supplied to `MetricFrame` | Crosstab rates derived from label and score columns | Freeze positive label, denominator, missingness, and weight behavior. |
| Equal opportunity/equalized odds | Typed aggregate from group rates | Metric helpers and grouped differences | Derivable from group-rate disparities, subject to API semantics | Compare the underlying group rates first, then the aggregate formula. |
| Sample weights | Supported only through documented metric contracts | Passed through metric `sample_params` where supported | Do not assume equivalent weighted semantics without API-level evidence | Weighted cases are metric-specific; unsupported paths are `not_comparable`. |
| Conditional strata | Governed by the reviewed conditional-disparity research contract | `control_features` can organize conditional groups | Group audit is not presumed equivalent to causal or risk adjustment | Compare strata only after freezing the target population and aggregation rule. |
| Confidence intervals | FairLendKit bootstrap/reliability contract | `MetricFrame` bootstrap/quantile facilities where configured | No equivalence is presumed from point-estimate tables | Freeze method, unit, draws, seed, confidence level, and undefined-draw policy. |
| Reliability/undefined state | Typed defined/unreliable/undefined states and reason codes | Raw metric result, `NaN`, warning, or exception depends on metric path | Table/null behavior depends on crosstab and disparity path | Preserve each raw state; normalize only through reviewed reason mappings. |
| Reporting | JSON/CSV/HTML from the same typed result | DataFrame/Series-oriented analysis outputs | Group/disparity/fairness audit tables and visual layers | Compare evidence fields, not visual similarity. |
| Mitigation | Offline-only boundary; not part of this spike | Reductions and post-processing APIs exist | Any mitigation/remediation path is out of comparison scope | No thresholds, model fitting, or production recommendations in the initial spike. |

This map is a design hypothesis to be verified against the pinned packages. If
an API behaves differently, the artifact records the observed behavior and the
document is amended; the adapter must not fabricate equivalence.

## 5. Input-semantic differences that must be explicit

### 5.1 Favorable label and decision direction

All tools must receive the same favorable outcome and favorable decision.
Adapters must not rely on an implicit `1` meaning. If a tool API assumes a
positive label, the manifest records the exact value passed. Reversing a label
requires a separate fixture and must reverse the expected directional metrics.

### 5.2 Reference group and ratio direction

FairLendKit AIR is directional:

```text
selection_rate(comparison) / selection_rate(reference)
```

A Fairlearn min/max or to-overall ratio is not this estimand unless the selected
groups and direction reduce to the same formula. Aequitas reference-group
configuration must name the same reference value. The artifact records the raw
tool invocation, selected reference, numerator group, denominator group, and
formula ID.

### 5.3 Denominators and missing rows

For every metric and group, record eligible rows, excluded rows, numerator,
denominator, and exclusion reasons. Tool defaults for nulls, unknown groups,
invalid scores, or absent classes must not silently change the cohort. An
adapter either reproduces the canonical exclusion policy exactly or marks the
comparison `cohort_mismatch`.

### 5.4 Undefined and unreliable values

`0`, `NaN`, null, exception, undefined, and unreliable are distinct states.
The comparison stores raw outputs before applying a mapping. A mapping to a
FairLendKit reason code requires a reviewed rule with evidence from a pinned API
path. Unknown behavior uses `external_state_unmapped`, not a guessed zero.

### 5.5 Weight semantics

An unweighted fixture is primary. Weighted fixtures run only for metrics whose
three implementations demonstrably accept equivalent frequency/importance
weights. The artifact records whether a tool ignored, rejected, normalized, or
used weights. A weighted mismatch cannot be hidden by comparing rounded point
estimates.

### 5.6 Control features and conditioning

Fairlearn `control_features` group output is useful for organizing conditional
comparisons, but it does not by itself perform risk adjustment or establish
cause. Aequitas group audit is not assumed to implement the same target
standardization. FairLendKit conditional analyses remain governed by the
separately reviewed conditional-disparity and HMDA research contract `f448f37`,
including common support, uncertainty, sensitivity, and non-causal language.
This independent branch records the commit identity rather than creating a link
to a document that is not yet present on its `main` baseline.

## 6. Reproducible comparison protocol

### 6.1 Environment

The spike uses a disposable environment separate from FairLendKit's normal test
environment. Its lock manifest records Python version, operating system,
installer version, direct and transitive package versions, source URLs, artifact
SHA-256 values, and license identities. Installing the spike dependencies must
not modify package runtime metadata or default extras.

### 6.2 Execution order

1. Validate the canonical CSV, schema, row IDs, and file digest.
2. Materialize three adapter inputs and verify their row/digest reconciliation.
3. Run FairLendKit, Fairlearn, and Aequitas in isolated processes.
4. Save raw machine-readable outputs without normalization.
5. Derive canonical numerators, denominators, rates, and directed contrasts.
6. Compare values only where semantic preconditions match.
7. Emit pass, mismatch, or not-comparable status with stable reason codes.
8. Re-run from the lock manifest and require byte-stable canonical artifacts,
   excluding explicitly identified environment/timestamp fields.

### 6.3 Metric cases

The minimal fixture suite covers:

- balanced groups with no disparity;
- a directional selection-rate disparity;
- reference-group reversal;
- exact AIR `0.8`, below `0.8`, and above `0.8`;
- zero reference-group selection rate;
- absent outcome class;
- constant scores with both classes;
- ties and mixed score ordering;
- missing group, label, decision, and score values;
- a low-support group;
- one intersectional group case;
- an optional supported weighted case; and
- one control-feature/stratum case.

Exact AIR `0.8` is a boundary fixture, not a legal pass/fail fixture. The
artifact records whether each tool flags, reports, or leaves interpretation to
the caller.

### 6.4 Numeric comparison

Counts and denominators must match exactly. Rational metrics derived from the
same counts compare against an exact fraction when possible. Floating values use
a preregistered absolute and relative tolerance no looser than `1e-12` unless a
tool's documented algorithm requires a reviewed exception. Rounded displays are
never comparison inputs.

Confidence intervals are comparable only when estimand, resampling unit,
method, draws, seed policy, confidence level, and invalid-draw handling match.
Otherwise they are reported side by side as `method_not_equivalent`.

## 7. Stable difference reasons

The machine-readable comparison uses at least these reason codes:

- `value_match`
- `numeric_mismatch`
- `numerator_mismatch`
- `denominator_mismatch`
- `cohort_mismatch`
- `reference_direction_mismatch`
- `positive_label_mismatch`
- `undefined_state_mismatch`
- `external_state_unmapped`
- `weight_semantics_not_equivalent`
- `interval_method_not_equivalent`
- `metric_not_supported`
- `dependency_identity_mismatch`
- `adapter_input_digest_mismatch`
- `external_execution_failed`

A mismatch is evidence to investigate. It is not automatically assigned to one
tool as an error and must not be silently accepted because two of three tools
agree.

## 8. Machine-readable artifact contract

The spike artifact contains:

- evidence class `external_interoperability_spike_not_production_validation`;
- FairLendKit commit, configuration SHA-256, command, environment, and seed;
- pinned external package artifacts, versions, URLs, SHA-256 values, and
  licenses;
- canonical input path, schema digest, file hash, row-ID digest, and row count;
- exact adapter commands and adapter-input digests;
- per tool and metric: raw status, raw value, numerator, denominator, group,
  reference, positive label, weight mode, exclusions, warnings, and errors;
- canonical estimand/formula ID and normalized comparison value when eligible;
- tolerance, comparison status, stable reason code, and diagnostic detail;
- separate totals for matches, mismatches, not-comparable cases, and execution
  failures; and
- a release lock that remains `locked_research_only` until independent review.

Raw external outputs may be stored only when they contain synthetic fixture
data and pass repository size and license checks. The artifact must not copy
third-party documentation or claim that MIT licensing makes tool outputs legal
or compliance advice.

## 9. CSV user-value comparison

The same fixed CSV task may support a separate usability study. It records, for
each tool and a preregistered participant/instruction protocol:

- setup steps and wall-clock time;
- first-run success or failure;
- configuration errors;
- manual data transformations;
- steps to obtain selection rate and a directed reference-group disparity;
- whether the participant correctly interprets direction, denominator,
  uncertainty, and limitations; and
- total human actions before a reproducible artifact exists.

This is a user study, not a code-speed benchmark. Documentation length, command
count, or script runtime alone does not establish lower user burden. Results may
inform a simpler FairLendKit CSV entry point but may not weaken semantic checks
or fail-closed behavior.

## 10. Non-extrapolation boundary

The comparison must not claim that:

- matching outputs validate fairness, causality, legality, or production
  suitability;
- one tool is globally more accurate because it matches another;
- AIR `0.8` is a universal credit-law threshold or safe harbor;
- demographic parity identifies the cause of a disparity;
- conditional grouping is equivalent to complete underwriting adjustment;
- mitigation removes discrimination or creates a compliant decision policy;
- synthetic-fixture agreement establishes performance on HMDA, lender, or
  consumer data; or
- package popularity, documentation quality, or API simplicity substitutes for
  external-method validity.

FairLendKit remains responsible for its credit-specific contracts, including
label semantics, directed references, undefined states, data-quality evidence,
risk-adjusted interpretation, and human review.

## 11. Implementation and review gate

Before the spike runs, independent review must approve:

- package and license manifest;
- fixed synthetic input and schema;
- adapter field mappings;
- metric/formula registry;
- undefined-state mapping;
- weight and confidence-interval eligibility;
- numeric tolerances and difference reason codes; and
- artifact and release-lock schema.

The initial spike may then run only on the fixed synthetic input. Adding HMDA or
other public microdata requires a separate approved data-source and study
contract. Adding any production or consumer data is prohibited by this design.

No comparison results are approved by this document. Findings require a
separate reproducibility and interpretation review.
