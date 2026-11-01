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

All rows for an entity belong to exactly one fold. Fold assignment is
`sha256(protocol_version || seed || entity_id)` reduced to the configured fold
count; the raw ID and digest are not reported. Preprocessing, rare-level mapping,
and model fitting use training folds only.

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

Predictability uses one version-pinned preprocessing and classifier pipeline:
training-fold median plus missing indicator for numeric features, training-fold
one-hot encoding for categorical features, and L2-regularized logistic
regression with declared solver, tolerance, maximum iterations, and fixed
regularization strength. Non-convergence is unavailable, not a usable score.

The mandatory null baseline is an intercept-only protected-group model; its AUC
is `0.5` where defined. Incremental screening is performed only when the caller
also supplies an approved baseline feature set. The baseline and
baseline-plus-candidate use identical entities, folds, preprocessing rules, and
hyperparameters. Incremental AUC is the latter minus the former; the candidate
alone is never described as incremental evidence.

## Thresholds and flags

Configuration must explicitly provide `association_threshold`,
`predictability_auc_threshold`, `incremental_auc_threshold`, confidence level,
fold count, minimum valid folds, per-fold class minimum, and stability tolerance.
All thresholds are finite and versioned; there are no hidden defaults.

A potential proxy-risk screening flag is emitted only when the corresponding
point estimate meets or exceeds its inclusive threshold, its confidence lower
bound also meets the threshold, all fold/reliability gates pass, and the
temporal-holdout estimate differs from the development estimate by no more than
the stability tolerance. Failure of stability produces a limitation, not a
flag. Every flag records rule ID/version, candidate ID, protected attribute,
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
suppression.
