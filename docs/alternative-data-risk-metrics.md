# Alternative-data credit-risk metric contract

Status: required independent approval gate for AD-3. AD-3 implementation must
not begin until this contract and its hand-calculated fixtures pass independent
review. AD-0 through AD-2 do not implement these metrics.

## Population and direction

Every metric uses one leakage-safe, label-mature evaluation population. The
configuration supplies two non-empty, typed, disjoint tuples:
`favorable_outcome_labels` and `unfavorable_outcome_labels`. After typed label
comparison, every mature eligible value must belong to exactly one tuple;
otherwise the run fails with `ad_unrecognized_outcome_label`. A value in the
unfavorable tuple maps to `bad=1`, and a value in the favorable tuple maps to
`bad=0`. Boolean, integer, and string labels are not mutually coerced. Missing,
censored, pending, unknown, third-category, or immature outcomes are never
mapped by negating favorable membership. Reports preserve both tuples and the
user-supplied outcome definition.

The configuration declares whether the supplied score targets the favorable or
unfavorable outcome. Calculation normalizes it to `risk_score`, where larger
always means greater ranked risk:

- unfavorable-target score: `risk_score = score`;
- favorable-target score: `risk_score = -score` for ranking scores; and
- favorable-target probability: `risk_probability = 1 - score`.

Probability scores must be finite in `[0, 1]` and explicitly target one outcome.
Ranking scores need only be finite. Calibration-in-the-large, calibration slope,
and Brier score apply only to a probability of the unfavorable outcome; for a
ranking score they are `not_applicable`, not zero. KS, Gini, bands, lift, and
capture accept either score type after direction normalization.

## Weighting and common gates

Optional weights are finite and non-negative and use the existing maximum-weight
normalization. Raw entity count and normalized weight total are both reported.
Zero total weight, absence of either outcome class, or an immature label makes
class-dependent metrics undefined. Reliability uses configured minimum total,
bad, and good entity counts; disclosure suppression is applied after reliability
and before serialization.

All splits are by entity. Multiple rows for one entity must be reduced under an
explicit pre-decision aggregation contract before risk evaluation; row-level
duplication cannot increase metric support.

## Score bands

`score_band_edges` is a strictly increasing explicit tuple in normalized
`risk_score` units. It creates `(-inf, e1)`, `[e1, e2)`, ..., `[en, +inf)`.
All equal scores remain in one band; ties are never split. Each band reports raw
entity count, normalized weight, bad count/weight, good count/weight, observed
bad rate, score minimum/maximum, and unavailable/suppressed state. Empty bands
remain present with an undefined rate.

Quantile-derived or data-dependent edges are outside the first contract. Band
order is increasing risk. A monotonicity observation may describe adjacent bad
rates but is not a pass/fail model verdict.

## Calibration

For probability `p_i` of bad outcome `y_i`:

- calibration-in-the-large is `mean_w(p) - mean_w(y)`; zero is exact aggregate
  calibration, positive means higher mean predicted risk;
- Brier score is `sum(w * (p - y)^2) / sum(w)`; and
- calibration slope is the coefficient of `logit(clamp(p, epsilon, 1-epsilon))`
  in a weighted logistic regression of `y`, with an intercept.

`epsilon` is required, finite, and in `(0, 0.5)`. The report records it. The
slope fit uses unregularized double-precision IRLS, zero coefficients at start,
at most 100 iterations, and convergence only when the maximum absolute
coefficient change is at most `1e-10`. The slope is undefined for one outcome
class, constant transformed probability, separation, non-convergence, or a
singular fit; implementations do not silently regularize or substitute a value.

## KS and Gini

Sort distinct normalized risk scores from high to low and process each complete
tie block. At every block boundary compute cumulative weighted bad capture and
cumulative weighted good capture. KS is the maximum absolute difference between
those two cumulative fractions, including the initial and final zero-difference
boundaries. Range is `[0, 1]`; the result records every maximizing score when
ties occur and uses the smallest normalized risk score as the canonical display
threshold.

Risk AUC is the weighted probability that a randomly selected bad entity has a
higher `risk_score` than a good entity, with equal scores worth `0.5`. Gini is
`2 * risk_auc - 1`, range `[-1, 1]`. This direction is fixed: positive values
mean bad outcomes tend to receive higher normalized risk scores. Gini is not
computed from rounded AUC.

## Lift and capture

`top_fractions` is a strictly increasing tuple in `(0, 1]`. Entities are sorted
by descending normalized risk. Zero-weight entities do not contribute to total
weight, target, selected count, or metrics; their raw excluded count is reported.
For positive total weight `W` and fraction `f`, target `T=f*W`. Traverse complete
equal-score blocks. Select the first block for which cumulative positive weight
after the block is `>= T`; if it equals `T`, stop exactly there. If cumulative
weight before a block is `< T` and after it is `> T`, include the whole crossing
block. Never split a tie. At `f=1`, select every positive-weight entity. Each
result records
requested fraction, achieved weight fraction, raw entity count, bad capture
`captured_bad_weight / total_bad_weight`, selected bad rate, and lift
`selected_bad_rate / overall_bad_rate`. A zero selected or total bad weight is
undefined with a stable reason, never zero.

The cutoff fixture has tie blocks `(risk, weight, bad)` of `(0.9,2,1)`,
`(0.8,1,0)`, `(0.8,1,1)`, and `(0.7,0,1)`. Thus `W=4`. At `f=0.5`, `T=2` and
selection stops after the first block with achieved fraction `0.5`. At `f=0.75`,
the complete `0.8` tie block is included, achieved fraction is `1.0`, bad capture
is `1.0`, selected bad rate is `3/4`, overall bad rate is `3/4`, and lift is
`1.0`; the zero-weight entity contributes to none of these values.

## Uncertainty, comparison, and fixtures

Bootstrap sampling is entity-level and stratified by observed outcome, using the
existing deterministic seed-stream contract. Bands, KS, Gini, calibration,
lift, and capture report valid-resample counts and reliability. Group/provider/
coverage-stratum comparisons use the same score direction, bands, cutoff rules,
outcome window, and compatible evaluation population; no model-training
population comparison is implied.

AD-3 must add hand-calculated weighted and unweighted fixtures covering score
direction reversal, probability/ranking applicability, complete ties, a cutoff
crossing a tie block, empty bands, zero weight, one outcome class, separation,
and disclosure suppression.
