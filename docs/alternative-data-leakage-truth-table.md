# Alternative-data leakage truth table

This table is normative for AD-0. Let `A` be `as_of_time`, `X` be run
`execution_time`, and `O` be the exact version's `observed_at`. Feature
intervals are inclusive; outcome evidence begins strictly after `A`.

```text
feature_start <= feature_end <= A < performance_start <= performance_end
performance_end <= label_maturity_time
```

The label is usable only when `label_maturity_time <= X`; a later maturity time
is valid configuration whose result is unavailable.

| Evidence | Boundary combination | Authoritative behavior | Disposition/code |
|---|---|---|---|
| Feature event | `event_time <= A` and `O <= A` | Version may enter features. | eligible |
| Feature event | `event_time <= A < O <= X` | Unavailable at decision time. | exclude / `ad_observed_after_decision` |
| Feature event | `A < event_time <= X` | Post-decision event cannot be a feature. | error / `ad_feature_after_decision` |
| Feature event | `X < event_time` or `X < O` | Future relative to execution. | error / `ad_future_timestamp` |
| Feature period | `period_end <= A` and `O <= A` | Eligible if start does not follow end. | eligible |
| Feature period | `period_start <= A < period_end` | Period crosses decision boundary. | error / `ad_feature_after_decision` |
| Feature period | `A < period_start` | Entire period is post-decision. | error / `ad_feature_after_decision` |
| Original plus revision | both observed by `A` | Latest valid linked version is authoritative. | eligible latest version |
| Original plus revision | original `O <= A`, revision `A < O <= X` | Original is authoritative; revision is excluded from features. | exclude revision / `ad_revision_after_decision` |
| Original plus reversal | reversal observed by `A`, valid earlier target | Apply explicit offset under family rules. | eligible chain |
| Original plus reversal | original observed by `A`, reversal observed after `A` | Preserve original decision-time view. | exclude reversal / `ad_observed_after_decision` |
| Revision/reversal chain | cycle, missing/cross-scope target, or target observed later | No authoritative chain exists. | error / linkage or `ad_non_monotonic_history` code |
| Outcome event/period | starts `<= A` | Not post-decision performance. | error / `ad_outcome_not_post_decision` |
| Outcome event/period | starts `> A`, ends in performance window, `O <= X` | May enter labels only, never features. | eligible outcome evidence |
| Outcome event/period | outside configured performance window | Exclude from this label. | exclude / `ad_outcome_outside_window` |
| Outcome evidence | `O > X` | Unavailable to this run. | error / `ad_future_timestamp` |
| Label | `X < label_maturity_time` | A future configured maturity date is valid; partial events cannot make the label mature. | unavailable / `ad_label_immature` only |
| Claimed mature evidence | evidence is asserted observed, but its `observed_at > X` | The run falsely claims knowledge not yet observed. | error / `ad_future_timestamp` |
| Mature label | raw value outside binary mapping | Cannot be inferred as good or bad. | error / `ad_unrecognized_outcome_label` |
| Completed source snapshot | `coverage_end > X` | Future completion claim is invalid. | error / `ad_future_timestamp` |
| Ongoing source | declared `coverage_end=null` | Metadata only; records still need individual eligibility. | valid metadata |

`ad_future_timestamp` applies to timestamps asserting knowledge or completed
events: record event/period end, `observed_at`, revision, reversal, evidence
claimed as already mature, and completed source coverage. A configured
`label_maturity_time > X` is legitimate future metadata and produces only
`ad_label_immature`; it is never itself `ad_future_timestamp`. Planned future
metadata cannot enter analytical evidence.

## Authoritative version algorithm

Group by source, entity, and logical record chain. Validate scope, targets, and
acyclicity first. For features, exclude versions with `observed_at > A`. Follow
valid revision links among remaining versions and select the terminal version
with greatest `(observed_at, record_id)`. Equal observation times require
explicit linkage to determine order; otherwise fail as conflicting. Apply only
reversals observable by `A`. For outcomes, repeat at execution cutoff `X`, then
apply the performance window and maturity rule.

## Required fixtures

The AD-0 oracle contains every table case and equality at each boundary:
`feature_end == A`, `performance_start == A`, `O == A`, `O == X`, and
`label_maturity_time == X`. It includes a pre-decision original with a
post-decision revision and reversal, an equal-observation-time conflict, and an
outcome event valid for labeling but forbidden from features. It separately
tests `label_maturity_time > X` as only immature and claimed mature evidence
with `observed_at > X` as future timestamp.
