# Metric contracts

The [canonical glossary](glossary.md) controls terminology. All metric
functions consume boolean indicators normalized from the explicit
`AuditConfig`: `True` means the configured favorable outcome or favorable
decision. This prevents raw `0`/`1` encodings from silently changing direction.

Every result records its value, numerator, denominator, and undefined reason.
`None` means undefined and is never replaced by numeric zero. Optional weights
must be finite and non-negative; a zero total weight produces an undefined
metric.

For numerical stability, supplied weights are divided by their largest positive
value before numerator and denominator evidence is accumulated. This does not
change a weighted rate or mean, because both terms use the same positive scale,
and prevents individually finite extreme weights from overflowing their sum.
The recorded numerator and denominator are therefore normalized weight units,
not necessarily the raw weight total.

Public disparity functions accept only defined finite rate values in `[0, 1]`
or a well-formed undefined `MetricValue` with a non-empty reason. `NaN`,
infinity, out-of-range rates, non-finite evidence, and contradictory
defined/undefined states fail validation.

## Outcome and decision metrics

### Selection rate

- Definition: share receiving the favorable decision.
- Formula: `sum(w * favorable_decision) / sum(w)`.
- Inputs: favorable-decision indicator and optional weights.
- Range: `[0, 1]`.
- Interpretation: observed favorable-decision frequency for the selected audit
  group. It is an approval rate only when approval is the configured favorable
  decision.
- Undefined: no records or no positive total weight.

### Accuracy

- Definition: share for which favorable/unfavorable decision matches the
  favorable/unfavorable observed outcome.
- Formula: `sum(w * (decision == outcome)) / sum(w)`.
- Inputs: favorable-outcome indicator, favorable-decision indicator, and
  optional weights.
- Range: `[0, 1]`; higher is more agreement, not necessarily a better lending
  policy.
- Undefined: no records or no positive total weight.

### True-positive rate

- Definition: favorable-decision rate among favorable observed outcomes.
- Formula: `TP / (TP + FN)`.
- Inputs: favorable outcome, favorable decision, optional weights.
- Range: `[0, 1]`.
- Interpretation: opportunity to receive the favorable decision conditional on
  the configured favorable outcome.
- Undefined: no favorable outcomes or no positive weight among them.

### False-positive rate

- Definition: favorable-decision rate among unfavorable observed outcomes.
- Formula: `FP / (FP + TN)`.
- Inputs: favorable outcome, favorable decision, optional weights.
- Range: `[0, 1]`.
- Interpretation: favorable decisions issued despite an unfavorable observed
  outcome; it is descriptive and not a legal conclusion.
- Undefined: no unfavorable outcomes or no positive weight among them.

### False-negative rate

- Definition: unfavorable-decision rate among favorable observed outcomes.
- Formula: `FN / (TP + FN)`.
- Inputs: favorable outcome, favorable decision, optional weights.
- Range: `[0, 1]`.
- Interpretation: favorable observed outcomes that did not receive the
  favorable decision.
- Undefined: no favorable outcomes or no positive weight among them.

## Group disparity metrics

Every comparison names a comparison group and an explicitly configured
reference group. Reversing those roles changes metric direction.

### Adverse impact ratio (AIR)

- Definition and formula: comparison-group selection rate divided by
  reference-group selection rate.
- Inputs: two defined selection rates in `[0, 1]`.
- Range: `[0, +infinity)`.
- Interpretation: values below `1` mean the comparison group has a lower
  selection rate in this explicit direction; values above `1` mean it has a
  higher rate.
- Undefined: either input rate is undefined or the reference-group selection
  rate is zero. A zero comparison rate with a positive reference rate is the
  defined value `0`.

The four-fifths rule (`AIR < 0.8`) is only a screening heuristic. Crossing the
threshold is neither proof of unlawful discrimination nor proof of compliance.
AIR must be reported with both selection rates, group counts, uncertainty, and
limitations.

### Demographic parity difference

- Definition and formula: comparison selection rate minus reference selection
  rate.
- Inputs: two selection rates.
- Range: `[-1, 1]`.
- Interpretation: negative values mean a lower comparison-group selection rate
  in the stated direction.
- Undefined: either selection rate is undefined.

### Equal opportunity difference

- Definition and formula: comparison true-positive rate minus reference
  true-positive rate.
- Inputs: two true-positive rates.
- Range: `[-1, 1]`.
- Interpretation: negative values mean a lower comparison-group true-positive
  rate in the stated direction.
- Undefined: either true-positive rate is undefined.

## Calibration metric

### Brier score

- Definition: mean squared error between probability of the favorable outcome
  and its observed indicator.
- Formula: `sum(w * (p_favorable - favorable_outcome)^2) / sum(w)`.
- Inputs: normalized favorable-outcome indicator, probabilities explicitly
  defined for the favorable outcome in `[0, 1]`, and optional weights.
- Range: `[0, 1]`; lower means smaller squared probability error.
- Undefined: no records or no positive total weight.
- Invalid input: an arbitrary score is not accepted as a probability. Values
  outside `[0, 1]` fail validation.

## Hand-calculated fixture

`tests/fixtures/hand_calculated_metrics.json` contains two synthetic audit
groups of four records. The reference group has selection rate `0.50`; the
comparison group has selection rate `0.25`. Therefore AIR is `0.50`, demographic
parity difference is `-0.25`, and equal opportunity difference is `0.00`.
Tests also cover zero denominators, defined zeros, label-direction reversal,
and reference-group reversal.
