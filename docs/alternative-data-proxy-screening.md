# Alternative-data potential proxy-risk screening contract

Status: required independent approval gate for AD-4. AD-4 proxy implementation
must not begin until this contract, deterministic fold fixtures, thresholds, and
privacy tests pass independent review. Outputs are exploratory screening
evidence, never proxy, causation, intent, legality, or feature-removal verdicts.

## Typed input and applicability boundary

One screen is identified by `(protocol_version, population_id, candidate_id,
protected_attribute_id, baseline_id, development_window, holdout_window)`. The
caller supplies typed entity-level evidence only:

- a versioned eligible population produced after AD-0 leakage and AD-1 quality
  gates, with population inclusion/exclusion reason counts;
- one explicitly configured numeric or categorical candidate value per entity,
  including an explicit missing state and derivation/version;
- one user-supplied categorical protected attribute used only as an audit target;
- an optional approved baseline feature set with its own contracts; and
- development/temporal-holdout membership, candidate availability time, source,
  provider, coverage stratum, and protected-group observation time.

The first release does not consume a credit outcome, decision label, model
score, or outcome maturity field. Credit-label maturity is therefore not an
eligibility requirement; supplying an outcome as a candidate or baseline field
is prohibited. Every candidate, baseline, and protected attribute must have been
observed no later than the applicable `as_of_time`. Post-decision observations,
future revisions, or fields rejected by the leakage gate fail closed before a
screen exists.

Protected attributes are never inferred. An entity with a missing protected
attribute is excluded from that protected-attribute screen and retained in an
explicit excluded count; it is not assigned to an `unknown` class. Candidate
missingness remains evidence: categorical screens use an explicit missing level,
numeric association excludes missing numeric values from eta-squared but tests
missing-versus-present association on the full protected-known population, and
predictability uses the training-fold imputation/indicator contract below.

The first release is strictly unweighted. An optional input weight may be
retained only as provenance and must not affect eligibility, fitting, metrics,
bootstrap sampling, thresholds, counts, or suppression. Configuration requesting
weighted proxy evidence is invalid rather than silently treated as unweighted.
Every result and trace records `weighting="unweighted"`; all denominators and
minimum supports are raw distinct-entity counts.

## Entity reduction and deterministic population

Source records are not classifier rows. Before fold assignment, the caller must
declare one versioned, candidate-specific entity reducer that uses only records
available by `as_of_time`. The reducer and canonical candidate contract decide
how multiple records become one value; AD-4 may not choose latest, average,
maximum, or any other aggregation implicitly.

After authoritative revision/reversal selection and reduction, there must be
exactly one candidate value, protected value, baseline vector, provider/source
assignment, coverage stratum, and population membership per entity per screen.
Duplicate identical rows collapse once. Conflicting protected values,
development/holdout membership, source scope, baseline values, or reducer
outputs fail closed. Weights are never summed across duplicates. Canonical
entity ordering is the UTF-8 byte ordering already used by the fold and numeric
preprocessing contracts; input row order cannot change a fold, statistic,
interval, trace, suppression decision, or serialized result.

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
rejected with `ad_proxy_window_conflict` for invalid window ordering or
`ad_proxy_isolation_failure` for population/preprocessing leakage. Insufficient
fold support remains unavailable under `ad_insufficient_fold_support`.

Development predictability uses only out-of-fold scores from the deterministic
folds. Temporal-holdout predictability never performs holdout cross-validation:
after development scoring is complete, fit exactly one new diagnostic model on
the entire canonically ordered development population and score the holdout once.
All preprocessing is refit on full development only. Numeric median, missing
indicator, mean, and `ddof=0` standard deviation come only from development.
Categorical vocabulary and rare mapping are learned only from full development;
holdout-only levels map to `unseen`. The holdout never changes a coefficient,
preprocessing value, category vocabulary, or threshold.

The intercept-only baseline, approved baseline model, and baseline-plus-candidate
model use the exact same development and holdout entity pairs. Each is refit on
all development entities with its declared feature set and the same optimizer;
baseline and augmented holdout scores are emitted as an inseparable pair for
incremental AUC. Golden fixtures freeze full-development preprocessing values,
rare/unseen vocabulary, optimizer iterations, coefficients, and holdout logits
for the null, baseline, candidate, and baseline-plus-candidate diagnostic models.

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

## Metric populations, directions, and denominators

All metrics are computed separately for development and temporal holdout
populations. Higher eta-squared, Cramer's V, protected-group AUC, and incremental
AUC mean stronger screening evidence; the contract never reverses their
direction or interprets a lower value as proof of safety.

- Numeric eta-squared uses distinct entities with known protected class and a
  finite observed candidate value. Its denominator is `SS_total`, and its
  support reports eligible protected-known entities, finite observed entities,
  candidate-missing entities, and per-class observed counts.
- Numeric missingness V uses every distinct protected-known entity, with exactly
  two candidate states, `missing` and `present`. Its statistical denominator is
  the contingency total `n`.
- Categorical V uses every distinct protected-known entity, including candidate
  `missing`, fold-trained `rare`, and held-out `unseen` levels where applicable.
  Its denominator is the post-pruning contingency total `n`.
- Binary/multiclass predictability AUC uses each distinct protected-known entity
  with one held-out prediction. Its denominators are the positive and negative
  raw entity counts for each one-vs-rest class.
- Incremental AUC uses the exact paired entity set with both baseline and
  baseline-plus-candidate held-out scores. A missing member of either pair makes
  that entity set invalid; it is never repaired by using different denominators.

Each evidence item carries population ID, window, metric and direction,
eligible/excluded/missing counts, raw entity denominator, per-class support,
point estimate, interval/reliability state, and stable reason codes. Undefined
denominators, insufficient classes/folds, non-finite values, or unequal paired
populations produce unavailable evidence with no point estimate or flag.

## Thresholds and flags

Configuration must explicitly provide `association_threshold`,
`predictability_auc_threshold`, `incremental_auc_threshold`, confidence level,
fold count, minimum valid folds, per-fold class minimum, stability tolerance,
bootstrap seed/resamples, minimum valid resamples, `minimum_stratum_entities`,
and exhaustive canonical `provider_strata` and `coverage_strata`. Association
thresholds are in `[0,1]`, predictability AUC thresholds in `[0.5,1]`,
incremental AUC thresholds in `[0,1]`, and stability tolerance in `[0,1]`. Fold
count is at least 2; minimum valid folds is between 2 and fold count. There are
no hidden defaults. `minimum_stratum_entities` is an integer at least the
configured `minimum_report_cell_count` and at least `2`; it applies to raw
distinct entities before any derived evidence.

Every eligible entity maps to exactly one declared provider stratum and one
declared coverage stratum; an explicitly declared `other` stratum closes each
vocabulary. Stratum labels are contract IDs, not raw provider/category values.
Provider and coverage dimensions must each contain at least two nonempty,
comparable, supported strata in both development and holdout. Otherwise the
screen records `ad_proxy_strata_not_comparable` and cannot emit a flag. Compute
the same metric and interval separately for every stratum in both windows. Every
stratum must meet `minimum_stratum_entities`, contain all protected classes
required by the metric, reach `minimum_valid_resamples`, and use the same metric,
preprocessing isolation, direction, and reliability rules as the overall result.
Insufficient support in an otherwise comparable dimension produces
`ad_proxy_stratum_support` and no flag. Stability is never silently marked not
applicable for either required dimension.

Association statistics are recomputed from the entities inside each stratum.
Predictability and incremental AUC reuse the already frozen overall-window
out-of-fold or temporal-holdout scores and subset those paired arrays by stratum;
they never fit a provider- or coverage-specific model. Bootstrap resamples only
within that stratum and remains protected-class-stratified.

Intervals use the existing SHA-256 counter bootstrap and Hyndman-Fan Type 7
percentiles. Resampling is at entity level, stratified by protected class. For
association metrics, recompute the statistic per resample. For predictability,
resample the fixed out-of-fold entity labels/scores without refitting; for
incremental AUC, resample paired baseline and baseline-plus-candidate scores
together. A resample with an undefined class/statistic is invalid. Failure to
reach `minimum_valid_resamples` makes evidence unreliable and forbids a flag.

The AD-3 bootstrap contract is reused without a second RNG: domain-separated
seed material includes protocol version, population/window, candidate,
protected attribute, baseline identity, metric, class/aggregation, and stream
role. Entity arrays are in canonical order before counter draws. Trace records
the RNG identity, seed fingerprint, resamples, valid/invalid resamples,
minimum-valid threshold, confidence level, Type 7 rule, point/interval
applicability, and reliability reason, but no entity ID, raw protected value,
prediction, coefficient, or resample array. When
`valid_resamples < minimum_valid_resamples`, `reliable=false` and interval
endpoints are null; a release model cannot re-inject them.

A potential proxy-risk screening flag uses one fixed conjunctive rule. For the
same metric, class aggregation, paired entity definition, and inclusive threshold
`T`, both development and holdout must independently satisfy
`reliable=true AND point>=T AND lower>=T`. The temporal comparison must satisfy
`abs(holdout_point-development_point)<=stability_tolerance`.

For each provider and coverage dimension, at least two nonempty supported strata
must exist in both windows. Every required stratum must be reliable in both
windows and must satisfy
`abs(stratum_point-window_overall_point)<=stability_tolerance` separately in
development and holdout. Stratum point/lower values are stability evidence and
do not separately have to meet `T`; the overall development and holdout results
are the threshold evidence. Any unsupported required stratum yields
`ad_proxy_stratum_support`; any supported provider/coverage difference above
tolerance yields `ad_proxy_stratum_unstable`. A temporal difference above
tolerance yields `ad_proxy_holdout_unstable`. Every such failure emits no flag.

Thus a flag is emitted only when all development, holdout, fold, bootstrap,
pairing, provider, coverage, and disclosure gates pass.

### Typed flag evidence references

A published `ProxyScreeningFlag` contains `rule_id`, `rule_version`,
`candidate_id`, `protected_attribute_id`, `metric`, `class_aggregation`,
`baseline_id` when applicable, `threshold`, `stability_tolerance`, and a neutral
review prompt. It never contains one ambiguous point estimate or interval.
Instead it contains these exact typed references:

- `threshold_evidence.development` and `threshold_evidence.holdout`, each a
  deterministic `ProxyEvidenceKey` resolving to one published evidence item with
  window, point, lower/upper interval, reliability, raw support bucket, and
  threshold comparison;
- `stability_evidence.temporal`, containing the two overall evidence keys,
  absolute point difference, tolerance, and `passed=true`;
- `stability_evidence.provider[]` and
  `stability_evidence.coverage_stratum[]`, in canonical stratum-contract order,
  each containing stratum contract ID, development stratum evidence key,
  development-overall evidence key, holdout stratum evidence key,
  holdout-overall evidence key, the two absolute differences, tolerance, and
  `passed=true`; and
- fold, bootstrap, pairing, and population contract references needed to resolve
  the same evidence, never entity IDs, predictions, coefficients, or raw labels.

`ProxyEvidenceKey` is derived only from versioned contract IDs, window, metric,
class aggregation, baseline scope, and stratum scope. It contains no consumer or
raw provider value. References must resolve within the same canonical release;
missing, cross-release, duplicated, or mismatched references fail closed.

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

Every publishable proxy unit participates in the same AD-1 release-wide exact
integer system as quality and risk evidence. Units include development/holdout,
candidate, protected attribute, metric/class, provider, coverage stratum,
baseline/incremental scope, eligible/excluded/missing support, contingency
margins, AUC class supports, fold supports, flags, and associated bootstrap
evidence. Historical equivalent releases are strong equations. Primary and
complementary suppression are solved jointly across JSON, CSV, and HTML; proxy
tables may not run a private suppression pass.

When a proxy unit is primary- or complementary-suppressed, its point estimate,
support, contingency components, interval, reliability details, threshold
comparison, stability difference, flag, and bootstrap evidence are all hidden.
The typed canonical JSON contains only the suppression state, safe count bucket,
and true suppression reason. Renderers cannot receive exact hidden values.
Before release, every hidden atomic entity-count variable must retain at least
two feasible non-negative integer values under current and historical equations.

Flag candidates and every referenced evidence unit enter joint suppression
before serialization. If the flag unit or any threshold, temporal, provider, or
coverage evidence it references is suppressed, unavailable, or unreliable, the
flag serializes only as a suppressed/unavailable release unit with no evidence
references, comparison values, or review prompt; it is not a published flag.
There are no dangling references and no renderer may reconstruct them.

The AD-3 trace/release boundary is reused: complete versioned configuration and
non-sensitive calculation trace are required, unreliable intervals have null
endpoints, and suppressed evidence never exposes count, weight, rate, value, or
interval. Logs, exceptions, fingerprints, diagnostics, and metadata receive no
entity ID, protected label, category value, fold membership, prediction,
coefficient, hidden exact support, or seed material.

The fixed logistic classifier is an internal diagnostic estimator of protected-
group predictability only. AD-4 does not train, tune, select, persist, export, or
recommend a credit model; it does not optimize an underwriting threshold or
recommend candidate retention/removal. Its coefficients and per-entity scores
are never public results.

## Minimum hand-calculated and adversarial fixtures

Fixtures are frozen, entity-level, order-permuted, and use no real consumer data:

1. **Numeric association:** four protected-known entities have classes
   `A,A,B,B` and candidate values `0,2,4,6`. Overall mean is `3`, class means are
   `1` and `5`, `SS_between=16`, `SS_total=20`, and eta-squared is `0.8`.
   Permuting input rows must reproduce every intermediate and result.
2. **Binary AUC and increment:** labels `A,A,B,B` with candidate-model scores
   `0.1,0.4,0.6,0.9` for class `B` yield AUC `1.0`; the intercept-only baseline
   yields `0.5`; paired incremental AUC is `0.5`. Threshold and lower-bound
   equality use inclusive comparison.
3. **Missingness populations:** one numeric candidate is missing. Eta-squared
   excludes that numeric value and reports its smaller observed support, while
   missingness V and predictability retain the entity. A missing protected value
   is excluded from all metrics for that protected screen with an explicit
   exclusion count.
4. **Entity conflict:** duplicate identical rows collapse once; conflicting
   protected values and cross-window membership fail before fold assignment.
   Row permutation cannot change the failure reason.
5. **Reliability:** `0 < valid_resamples < minimum_valid_resamples` produces
   `reliable=false`, null endpoints, and no flag. A one-class resample is invalid,
   not silently omitted from the required valid count.
6. **Joint disclosure:** an overall count of `20` and a published related count
   of `19` would reveal a protected/candidate cell of `1`. The shared AD-1 system
   must add complementary suppression; proxy point estimates, interval, flag,
   trace evidence, and all renderers expose no exact hidden value. Repeating the
   release with historical equations preserves at least two feasible values for
   every hidden variable.
7. **Scope guard:** attempts to supply outcome, decision, post-decision,
   identifier, weight-enabled, or protected-derived candidates fail closed.
   No fixture produces a causation, discrimination, legality, compliance,
   creditworthiness, feature-removal, or threshold-recommendation statement.
8. **One-sided threshold:** development has `point>=T` and `lower>=T`, while
   holdout has either `point<T` or `lower<T`; no flag is emitted even when the
   absolute temporal difference is within tolerance. The converse fixture
   (holdout passes, development fails) also emits no flag.
9. **Provider/coverage stability:** two supported provider strata and two
   supported coverage strata reproduce the overall metric within tolerance and
   permit the gate. Mutating one supported stratum beyond tolerance produces
   `ad_proxy_stratum_unstable`; reducing one below support produces
   `ad_proxy_stratum_support`. Neither mutation emits a flag.
10. **Holdout fitting:** frozen full-development numeric transforms, category
    vocabulary, `rare`/`unseen` mapping, coefficients, iterations, and holdout
    logits prove the holdout is scored once and is never used for fitting or
    cross-validation. Baseline and augmented score arrays have identical entity
    order and length.
11. **Reason-code matrix:** one minimal fixture each requests weighting, supplies
    a prohibited candidate, creates an entity conflict, reverses/overlaps the
    windows, leaks one entity/transform across isolation boundaries, omits a
    protected value, creates an undefined statistic, and mismatches the paired
    baseline population. It asserts respectively
    `ad_proxy_weighting_unsupported`, `ad_proxy_candidate_prohibited`,
    `ad_proxy_entity_conflict`, `ad_proxy_window_conflict`,
    `ad_proxy_isolation_failure`, `ad_proxy_protected_missing`,
    `ad_proxy_statistic_undefined`, and
    `ad_proxy_paired_population_mismatch`, including disposition and exact
    canonical message. Input-order permutations preserve each result.
12. **Single-stratum prohibition:** a population with only one nonempty provider
    stratum yields `ad_proxy_strata_not_comparable` and no flag; a separate
    population with only one nonempty coverage stratum yields the same code and
    no flag. Neither case is recorded as stability not applicable.
13. **Typed flag rendering:** one passing flag references distinct development
    and holdout threshold evidence plus temporal, two provider-stratum, and two
    coverage-stratum stability evidence sets. Canonical JSON preserves the nested
    reference structure. CSV emits one `proxy_flag` row for scalar fields and
    deterministic `proxy_flag_evidence` rows keyed by flag ID, dimension,
    canonical stratum order, window, and evidence key. HTML renders those same
    normalized rows. The golden fixture normalizes all three renderers to the
    identical tuple set. Suppressing each referenced unit in turn produces no
    published flag, no dangling reference, and no numeric leakage in any format.

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

## AD-4 implementation and release acceptance

AD-4 implementation is limited to typed screening inputs/results, deterministic
entity reduction validation, the fixed association/predictability diagnostics,
bootstrap/reliability evidence, joint suppression integration, and canonical
JSON with matching CSV/HTML renderers. Acceptance requires the fixtures above,
full identifier-leakage tests for JSON/CSV/HTML/logs/exceptions/diagnostics,
cross-runtime deterministic goldens, and complete architecture/discoverability
tests.

The slice explicitly excludes real-data connection, download execution, model
training APIs, model/threshold recommendation, automated feature removal,
production credit decisions, and any causal, discriminatory, lawful/unlawful,
compliant/noncompliant, or consumer-creditworthiness conclusion. Adding any of
those capabilities requires a separate contract and independent approval.
