# Canonical Undefined Reasons

## Purpose

An undefined metric is not the numeric value `0`, an error, or an adverse
finding. It means the metric cannot be calculated under its documented
population and denominator contract. This document defines the stable
vocabulary used by metric producers, `AuditResult`, JSON, HTML, and CSV
renderers.

Each undefined metric must carry a machine-readable `code` and the matching
canonical `message`. Renderers may display structured context, such as the
metric and audit-group identifiers, but must not change the meaning of the
reason or turn it into a legal or compliance conclusion.

## Reason catalog

| Code | Canonical message | Use when |
| --- | --- | --- |
| `empty_population` | No records are available for this metric. | The metric's complete evaluation population has no records. |
| `zero_total_weight` | The metric population has no positive total weight. | Records exist, but their eligible weights sum to zero. |
| `no_favorable_outcomes` | No favorable observed outcomes are available for this metric. | A metric conditioned on favorable outcomes has no qualifying records. |
| `zero_favorable_outcome_weight` | Favorable observed outcomes have no positive total weight. | Favorable outcomes exist, but their eligible weights sum to zero. |
| `no_unfavorable_outcomes` | No unfavorable observed outcomes are available for this metric. | A metric conditioned on unfavorable outcomes has no qualifying records. |
| `zero_unfavorable_outcome_weight` | Unfavorable observed outcomes have no positive total weight. | Unfavorable outcomes exist, but their eligible weights sum to zero. |
| `comparison_metric_undefined` | The comparison-group input metric is undefined. | A directed disparity cannot be calculated because its comparison-group input is undefined. |
| `reference_metric_undefined` | The reference-group input metric is undefined. | A directed disparity cannot be calculated because its reference-group input is undefined. |
| `zero_reference_selection_rate` | The reference-group selection rate is zero, so the ratio is undefined. | AIR has a defined reference-group selection rate of zero. |

## Selection rules

- Producers must select the most specific applicable reason.
- `empty_population` and `zero_total_weight` apply to an entire metric
  population. Outcome-conditioned metrics use the corresponding favorable- or
  unfavorable-outcome reason instead.
- A disparity that receives an undefined group metric uses
  `comparison_metric_undefined` or `reference_metric_undefined`. The result
  model should retain the source metric's reason as structured context rather
  than concatenate it into a new free-form message.
- AIR uses `zero_reference_selection_rate` only when the reference selection
  rate is defined and equal to `0`. If the comparison rate is `0` and the
  reference rate is positive, AIR is the defined numeric value `0`.
- Multiple applicable failures use deterministic precedence: comparison input,
  then reference input, then a metric-specific denominator condition. Reports
  may show all upstream validation warnings separately, but a metric has one
  primary undefined-reason code.

## Result and renderer contract

A versioned report Schema should represent an undefined reason as a closed
enumeration, not an arbitrary string. The conceptual shape is:

```json
{
  "value": null,
  "undefined_reason": {
    "code": "zero_reference_selection_rate",
    "message": "The reference-group selection rate is zero, so the ratio is undefined."
  }
}
```

For a defined metric, `value` is finite and `undefined_reason` is `null`. For an
undefined metric, `value` is `null` and `undefined_reason` is required. The
following are invalid:

- substituting `0`, `NaN`, or infinity for an undefined value;
- emitting a code with a non-canonical message;
- using an undefined reason for input-validation failures that should stop the
  audit;
- translating a reason into `compliant`, `non-compliant`, `legal`, `illegal`,
  or equivalent automated conclusions; or
- using `insufficient data` as an unstructured catch-all when a catalog reason
  applies.

Adding, removing, or changing a reason code or canonical message is a report
Schema compatibility change. It requires an issue, affected tests and fixtures,
documentation updates, and versioning review.

