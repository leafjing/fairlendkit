# Alternative-data potential proxy-risk screening contract

Status: required independent approval gate for AD-4. AD-4 proxy implementation
must not begin until this contract, deterministic fold fixtures, thresholds, and
privacy tests pass independent review. Outputs are exploratory screening
evidence, never proxy, causation, intent, legality, or feature-removal verdicts.

## Candidate admission gate

Every candidate is explicitly named and must be available no later than
`as_of_time`. The following are prohibited as candidates or baseline features:

- protected attributes and deterministic transformations of them;
- outcome, decision, label-maturity, and post-decision fields;
- entity, record, account, obligation, meter, address, permission, revision,
  reversal, and join/linkage identifiers;
- raw descriptions, free text, exact geolocation, and direct identifiers;
- fold assignments, sample weights, provider row keys, and target encodings
  fitted outside a training fold; and
- any field rejected or excluded by the leakage gate.

Configuration records feature type, derivation/version, allowed values or range,
missing-state meaning, source, and contextual proxy pathways. Missingness is an
explicit category/indicator and is never mean-imputed into invisibility.

## Entity and time isolation

All rows for an entity belong to exactly one fold. Fold assignment uses these
exact bytes: ASCII `fairlendkit-proxy-fold-v1`, then each UTF-8 string
(`protocol_version`, `entity_id`) as an unsigned 32-bit big-endian byte length
followed by its bytes, with `seed` between them as one unsigned 64-bit big-endian
integer. Reject strings longer than `2^32-1` bytes. Compute SHA-256, interpret
all 32 digest bytes as one unsigned big-endian integer, and assign
`integer % fold_count`. Fold numbers are zero-based. This length-prefixed tuple
encoding prevents field-boundary collisions; raw IDs and digests are not
reported. Preprocessing, rare-level mapping, and fitting use training folds only.

Evaluation also requires a forward temporal holdout whose feature window begins
after the development window ends. No entity may cross development and holdout
populations. Cross-validation estimates development variability; the temporal
holdout is separately labeled and cannot be merged into it. A screen is
unavailable if either isolation rule cannot be satisfied.

Each fold must contain at least the configured raw entity minimum and every
protected class used by its metric. Fewer than two protected classes, an absent
class in any validation fold, or fewer valid folds than `minimum_valid_folds`
produces `ad_insufficient_fold_support` and no flag.

## Fixed screens and baselines

The first release supports:

1. Numeric candidate versus categorical protected attribute: correlation ratio
   eta-squared on observed numeric values, plus a separate bias-corrected
   Cramer's V between candidate-missingness and the protected attribute.
2. Categorical candidate versus categorical protected attribute: bias-corrected
   Cramer's V on held-out contingency counts, including a missing category.
3. Protected-group predictability: out-of-fold AUC for binary protected targets
   or macro one-vs-rest AUC for multiclass targets. Every class is reported.

The first release is unweighted: survey/sample weights are neither predictors
nor fitting/metric weights. For numeric values `x` and protected classes `g`,
eta-squared is `SS_between / SS_total`, where `SS_between = sum_g n_g *
(mean_g - mean)^2` and `SS_total = sum_i (x_i - mean)^2`, using observed numeric
values only. It is undefined when fewer than two classes remain or
`SS_total=0`. Candidate missingness is separately cross-tabulated as
missing/present.

For an `r` by `k` contingency table with total `n`, compute Pearson
`chi2 = sum((observed-expected)^2/expected)` over positive expected cells,
`phi2=chi2/n`, `phi2_corrected=max(0, phi2-((k-1)*(r-1))/(n-1))`,
`r_corrected=r-((r-1)^2/(n-1))`, and
`k_corrected=k-((k-1)^2/(n-1))`. Bias-corrected Cramer's V is
`sqrt(phi2_corrected / min(k_corrected-1, r_corrected-1))`. It is undefined for
`n<=1`, a non-positive corrected denominator, or fewer than two nonempty rows or
columns. Before defining `r` and `k`, computing expected counts, or applying any
correction, delete every zero-marginal row and column; repeat until none remain.
Missing, `rare`, and `unseen` are explicit levels when their margins are
positive. They are not dropped merely because of their names.

Binary AUC is the unweighted probability that a randomly chosen positive-class
entity has a higher held-out score than a negative-class entity, with ties worth
`0.5`. Multiclass AUC computes that formula one-vs-rest for every class in
canonical typed-label order and takes their unweighted arithmetic mean. A class
without both sides is undefined; it is not omitted from the macro mean.

Predictability uses one fixed pipeline. Within each fold, order training entities
by canonical `entity_id` before all reductions. Numeric features use the
training-fold median, averaging the two middle finite values with `math.fsum`
when count is even, plus a missing indicator. Impute missing values with that
median, then compute post-imputation mean with `math.fsum(values)/n` and
population variance with `math.fsum((x-mean)^2)/n` (`ddof=0`). Standard deviation
is the non-negative square root. If variance is exactly zero, every standardized
value is exactly `0.0`; otherwise standardize as `(x-mean)/std`. No BLAS/vector
reduction order may replace these canonical scalar reductions. Categorical features use
training-fold one-hot encoding in canonical label order. The classifier is the
FairLendKit full-batch L2 logistic reference implementation, not a caller-chosen
library solver. It minimizes mean negative log likelihood plus
`0.5 * lambda * ||beta_non_intercept||^2`, with `lambda=1.0`; the intercept is
unpenalized. Binary logistic uses one logit. Multiclass uses softmax with the
first canonical class as the zero-coefficient reference.

Optimization starts at all-zero coefficients, uses double-precision damped
Newton steps and Cholesky solution, and halves the step until the objective does
not increase. It stops only when both maximum absolute gradient and coefficient
change are `<=1e-10`, with at most 100 iterations and 60 halvings per iteration.
Singular Hessian, failed Cholesky, non-finite arithmetic, exhausted halvings, or
iteration limit is `ad_proxy_model_nonconvergence`; no coefficients or score are
used. The implementation and golden logits are release-pinned; an alternative
classifier or numerical optimizer is a new contract version.

The mandatory null baseline is an intercept-only protected-group model; its AUC
is `0.5` where defined. Incremental screening is performed only when the caller
also supplies an approved baseline feature set. The baseline and
baseline-plus-candidate use identical entities, folds, preprocessing rules, and
hyperparameters. Incremental AUC is the latter minus the former; the candidate
alone is never described as incremental evidence.

## Thresholds and flags

Configuration must explicitly provide `association_threshold`,
`predictability_auc_threshold`, `incremental_auc_threshold`, confidence level,
fold count, minimum valid folds, per-fold class minimum, stability tolerance,
bootstrap seed/resamples, and minimum valid resamples. Association thresholds
are in `[0,1]`, predictability AUC thresholds in `[0.5,1]`, incremental AUC
thresholds in `[0,1]`, and stability tolerance in `[0,1]`. Fold count is at
least 2; minimum valid folds is between 2 and fold count. There are no hidden
defaults.

Intervals use the existing SHA-256 counter bootstrap and Hyndman-Fan Type 7
percentiles. Resampling is at entity level, stratified by protected class. For
association metrics, recompute the statistic per resample. For predictability,
resample the fixed out-of-fold entity labels/scores without refitting; for
incremental AUC, resample paired baseline and baseline-plus-candidate scores
together. A resample with an undefined class/statistic is invalid. Failure to
reach `minimum_valid_resamples` makes evidence unreliable and forbids a flag.

A potential proxy-risk screening flag is emitted only when the corresponding
point estimate meets or exceeds its inclusive threshold, its confidence lower
bound also meets the threshold, all fold/reliability gates pass, and the
absolute difference `abs(holdout - development)` is no more than the stability
tolerance for the same metric and class aggregation. Failure of stability
produces `ad_proxy_holdout_unstable`, not a flag. Every flag records rule
ID/version, candidate ID, protected attribute,
metric, threshold, point estimate, interval, baseline where applicable, fold
support, populations, and neutral review prompt.

## High cardinality and sparse levels

`maximum_categories` and `minimum_level_entities` are required. Category
vocabularies are learned on each training fold. Levels below the minimum map to
one `rare` level in both training and validation; unseen validation levels map
to `unseen`. Neither level is dropped. A candidate exceeding
`maximum_categories` after this mapping is unavailable with
`ad_high_cardinality_unsupported`; hashing, ordinal coding, and silent truncation
are forbidden in the first release.

## Privacy, reporting, and exclusions

Reports contain candidate contract IDs, aggregate metrics, thresholds, support
buckets, limitations, and flags. They do not contain raw values, category labels
from sparse cells, coefficients, entity predictions, fold membership, or IDs.
The alternative-data disclosure-suppression contract applies before typed result
serialization. Suppressed or unreliable evidence cannot emit a flag.

AD-4 fixtures must cover protected/identifier/leakage-field rejection, entity
and time leakage, deterministic folds, binary and multiclass AUC, missing state,
rare/unseen levels, high cardinality, non-convergence, baseline equality,
incremental evidence, threshold equality, unstable holdout behavior, and
suppression. Golden fixtures include the exact length-prefixed fold bytes,
SHA-256 digest, digest integer, modulo result, eta/contingency components,
Cramer's V correction, per-class AUCs, Type 7 interval endpoints, optimization
iterations/logits, and the absolute development-holdout difference. The
preprocessing fixture records sorted training IDs, finite values, median,
post-imputation vector, `math.fsum` mean, `ddof=0` variance/std, standardized
training and held-out values, missing indicators, and a zero-variance column.
The contingency fixture includes zero-marginal rows/columns plus positive
`rare` and `unseen` levels and fixes the table after pruning and final V.
