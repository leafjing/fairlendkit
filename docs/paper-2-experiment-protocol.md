# Paper 2 experiment protocol — When Fairness Metrics Mislead

## Status and purpose

This is the preregistration-style method contract for the Paper 2 research
artifact. It must be approved before large-scale experiment code is written or
results are inspected. Amendments after approval require a dated rationale,
must preserve the original protocol, and must label the affected analysis as
confirmatory or exploratory.

The study asks when finite-sample group metrics, uncertainty intervals, and
screening flags cease to be dependable evidence. FairLendKit Milestone 3 is the
frozen measurement implementation. This protocol does not change product
behavior and does not treat a screening threshold as a legal or fairness test.

## Research questions

1. How do group size, group-size imbalance, outcome prevalence, and favorable
   decision support affect metric error, definedness, interval coverage, and
   adverse-impact-ratio (AIR) flag errors?
2. Do the documented reliability gates identify regimes with materially worse
   error, coverage, or flag behavior, and what information is lost when gated
   results are withheld from flags?
3. How do MCAR, MAR, and explicitly modeled MNAR missingness alter observed
   group disparities relative to the complete-data estimand?
4. Where does the fixed percentile bootstrap provide adequate coverage, and
   where do boundaries, sparse support, or undefined resamples cause failure?
5. Do the failure patterns observed under controlled simulation also appear as
   instability in a fixed public mortgage-data cohort and, if feasible, a
   licensed credit-risk benchmark?

## Preregistered claims

No result is required to favor FairLendKit. The confirmatory family contains
exactly five one-sided contrasts, C1 and C3–C6 below. H2 is a non-causal
diagnostic estimand and H7 is exploratory; neither enters multiplicity testing.

- **C1 — sample support:** in `SEL-N025` versus `SEL-N1000`, the mean absolute
  AIR error is larger at `n=25`. The paired statistic is
  `mean(|AIR_hat_25 - AIR| - |AIR_hat_1000 - AIR|)` over all 50,000 replicate
  IDs for which both AIR estimates are defined; paired availability is reported
  against all 50,000 generated pairs.
- **H2 — reliability separation, diagnostic:** across the frozen AIR scenario
  registry, the scenario-standardized mean absolute AIR error is reported for
  `reliable` and `unreliable` observations. It is an association between a
  status and error, not the causal effect of applying a gate.
- **C3 — sparse decisions:** in `PERF-DEC001` versus `PERF-DEC050`, the
  proportion of defined precision estimates is lower at favorable-decision
  prevalence `0.01`. The paired statistic is the mean replicate-level
  difference `I_defined_050 - I_defined_001` over replicate IDs 0–49,999.
- **C4 — AIR gating:** in `SEL-AIR081-N025`, the false-positive proportion is
  lower for the frozen reliability-gated policy than for the ungated policy.
  The paired statistic is `I_false_positive_ungated -
  I_false_positive_gated` over replicate IDs 0–49,999. Population AIR is `0.81`,
  so a flag is false.
- **C5 — missingness:** in `MISS-MNAR30` versus `MISS-MCAR30`, the mean absolute
  selection-rate-difference error is larger under MNAR. The paired statistic is
  `|error_MNAR| - |error_MCAR|` against the same complete-data truth over
  replicate IDs 0–49,999 for which both metrics are defined.
- **C6 — bootstrap regularity:** emitted 95% AIR intervals have lower empirical
  coverage in `SEL-AIR081-N050` than in `SEL-AIR081-N1000`. The paired statistic is the
  explicitly `d_r = I_cover_1000 - I_cover_050` over replicate IDs 0–49,999 for
  which both intervals are emitted. Availability is reported separately and
  never counted as coverage.
- **H7 — public-data stability, exploratory:** low-support public-data cells are
  expected to show greater repeated-subsample dispersion than supported cells.
  The exact estimand and replicate design are frozen below, but no confirmatory
  p-value or generalization claim is made.

### Test registration table

`alpha` is the raw one-sided level before adjustment. Only rows whose family is
`P2-CONFIRMATORY-V1` are tested; Holm adjustment is applied jointly across
those five rows at family-wise `0.05`.

| `test_id` | Status | Metric/endpoint | Scenarios/policies | Contrast and direction | Denominator | Statistic | Raw `alpha` | Holm family |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P2-C1-AIR-MAE-N` | confirmatory | AIR absolute error | `SEL-N025` vs `SEL-N1000` | `AE_025 - AE_1000 > 0` | replicate IDs 0–49,999 with both AIR values defined; availability uses all 50,000 pairs | paired mean difference; one-sample studentized t-test | 0.05 | `P2-CONFIRMATORY-V1` |
| `P2-H2-RELIABILITY-DIAGNOSTIC` | descriptive | AIR absolute error by reliability | five frozen AIR-paired units built from 25 explicitly listed unique AIR×size IDs | mean across units of `MAE_N025 - mean(MAE_N050,N100,N250,N1000)` | defined AIR values from replicate IDs 0–49,999; equal AIR-unit and within-unit reliable-N weights | paired-unit mean and joint paired-unit bootstrap interval | — | none |
| `P2-C3-PRECISION-DEFINED` | confirmatory | precision defined indicator | `PERF-DEC001` vs `PERF-DEC050` | `I_defined_050 - I_defined_001 > 0` | all replicate IDs 0–49,999 | paired mean difference; one-sample studentized t-test | 0.05 | `P2-CONFIRMATORY-V1` |
| `P2-C4-AIR-FP-GATE` | confirmatory | false AIR flag indicator | gated vs ungated in `SEL-AIR081-N025` | `FP_ungated - FP_gated > 0` | all replicate IDs 0–49,999; undefined AIR is no emitted flag and separately counted | paired mean risk difference; one-sample studentized t-test | 0.05 | `P2-CONFIRMATORY-V1` |
| `P2-C5-MISSINGNESS-MAE` | confirmatory | selection-rate-difference absolute error | `MISS-MNAR30` vs `MISS-MCAR30` | `AE_MNAR - AE_MCAR > 0` | replicate IDs 0–49,999 with both metrics defined; availability uses all 50,000 pairs | paired mean difference; one-sample studentized t-test | 0.05 | `P2-CONFIRMATORY-V1` |
| `P2-C6-AIR-COVERAGE` | confirmatory | 95% AIR interval coverage | `SEL-AIR081-N050` vs `SEL-AIR081-N1000` | `d_r=I_cover_1000-I_cover_050 > 0` | replicate IDs 0–49,999 with both intervals emitted; availability uses all 50,000 pairs | paired mean coverage difference; one-sample studentized t-test | 0.05 | `P2-CONFIRMATORY-V1` |
| `P2-H7-HMDA-STABILITY` | exploratory | subsample MAD from full-cohort metric | HMDA fractions 0.25/0.50/0.75 | median low-support MAD minus median supported-cell MAD | eligible cells under the frozen support cutoffs | cell-level difference and cell-bootstrap interval | — | none |

## Estimands and analysis units

### Population estimands

For every synthetic scenario, the population quantities are:

- group selection and denial rates;
- accuracy, precision, TPR, FPR, FNR, Brier score, and ROC AUC;
- comparison-minus-reference selection-rate and TPR differences;
- AIR; and
- equalized-odds gap.

Population truth must be obtained analytically where possible. Otherwise it is
computed once from a deterministic population of at least 10 million records or
deterministic numerical integration with absolute numerical error below
`1e-5`. The truth method and error check are stored with each scenario.

The primary analysis unit is one independently seeded simulated audit. The
public-data analysis unit is a prespecified cohort cell or deterministic
subsample, not an individual applicant.

### Primary operating characteristics

- bias and absolute error of each defined metric;
- RMSE and the 50th, 90th, and 95th percentiles of absolute error;
- defined, reliable, interval-available, and flag-available proportions;
- empirical interval coverage and width;
- AIR false-positive rate: population AIR `>= 0.8` and emitted AIR flag;
- AIR false-negative rate: population AIR `< 0.8` and no emitted flag among
  runs eligible to flag;
- end-to-end AIR miss rate, which also counts unavailable flags; and
- limitation-code frequency and valid-bootstrap-resample proportion.

False-negative rates are reported both conditional on flag eligibility and
unconditionally. This prevents reliability suppression from appearing to
improve sensitivity.

For all coverage results, the numerator is emitted intervals containing the
population truth and the denominator is emitted intervals. Interval
availability uses all generated audits as its denominator. Undefined metrics
never enter error summaries; their frequency is reported separately.

H2 uses exactly these 25 unique IDs; aliases such as `SEL-N025` and
`SEL-AIR081` are excluded:

```text
SEL-AIR060-N025  SEL-AIR060-N050  SEL-AIR060-N100  SEL-AIR060-N250  SEL-AIR060-N1000
SEL-AIR079-N025  SEL-AIR079-N050  SEL-AIR079-N100  SEL-AIR079-N250  SEL-AIR079-N1000
SEL-AIR080-N025  SEL-AIR080-N050  SEL-AIR080-N100  SEL-AIR080-N250  SEL-AIR080-N1000
SEL-AIR081-N025  SEL-AIR081-N050  SEL-AIR081-N100  SEL-AIR081-N250  SEL-AIR081-N1000
SEL-AIR100-N025  SEL-AIR100-N050  SEL-AIR100-N100  SEL-AIR100-N250  SEL-AIR100-N1000
```

For each scenario, compute mean absolute AIR error over defined values from
replicate IDs 0–49,999. A scenario with zero defined AIR values is unavailable,
not silently discarded or imputed.

Every `N025` scenario is `unreliable`; every `N050/N100/N250/N1000` scenario is
`reliable` under `minimum_group_size=50`. The 25 IDs form exactly five paired
scenario units, ordered by AIR `{060,079,080,081,100}`. Unit `a` contains:

```text
unreliable side: SEL-AIR{a}-N025
reliable side:   SEL-AIR{a}-N050, SEL-AIR{a}-N100,
                 SEL-AIR{a}-N250, SEL-AIR{a}-N1000
```

For unit `a`, calculate
`delta_a = MAE_unreliable_a - mean(MAE_reliable_a,N)` with equal weight across
the four reliable-N scenarios. The H2 estimand is the equal-weight mean of the
five `delta_a` values. This pairs reliability states on population AIR while
retaining the diagnostic, non-causal interpretation.

The joint paired-unit bootstrap has 2,000 draws. For draw `b`, sample one vector
of five integer unit indices with replacement from `[0,4]` using the sole RNG
format with `purpose=h2_bootstrap`, `unit_id=H2`, `draw_id=b`,
`scope=analysis`, and `role=scenario_unit_index`. The same sampled unit indices
select both the unreliable side and its four-scenario reliable side; compute
each selected `delta_a`, then their equal-weight mean. A selected unit is
unavailable if its unreliable MAE or any of its four reliable MAEs is
unavailable. A draw with no available selected unit is invalid. Invalid draws
are recorded and not replaced. At least 1,900 of 2,000 draws must be valid;
otherwise H2 is `not_estimable`, with no interval, imputation, resampling, or
one-sided substitute denominator.

Coverage is not part of H2. State-specific definedness and interval availability
use all 50,000 generated audits per scenario as their denominators and are
reported jointly with MAE. No within-scenario or causal effect is claimed.

### Secondary operating characteristics

- signed error and relative error where the population value is safely away
  from zero;
- calibration of nominal 90%, 95%, and 99% intervals in sensitivity runs;
- gate-specific precision, recall, and negative predictive value for detecting
  a prespecified practically large metric error; and
- runtime and deterministic-output checks.

“Practically large error” is fixed before results as `0.05` absolute error for
rates/differences/AUC/Brier, `0.10` for AIR, and `0.05` for equalized-odds gap.
Sensitivity results at half and twice these cutoffs are secondary.

## Synthetic data-generating processes

All experiment and analysis randomness uses
`fairlendkit-paper2-sha256-counter-v1`. Its only seed-material format is the
UTF-8 encoding of:

```text
fairlendkit-paper2-v1\0{master_seed}\0{purpose}\0{unit_id}\0{draw_id}\0{scope}\0{role}
```

A block is `SHA256(seed_material || counter_uint64_be)`, counter starts at zero,
and each digest is consumed as four sequential uint64 big-endian candidates.
The master seed is `20261008`. Field values are closed:

- `purpose`: `generate`, `summary_bootstrap`, or `h2_bootstrap`;
- for `generate`, `unit_id=pair_id`, `draw_id=replicate_id`, `scope` is
  `shared` or `scenario:{scenario_id}`, and `role` is `row`, `missingness`, or
  `auxiliary`;
- for `summary_bootstrap`, `unit_id={scenario_id}:{metric}:{checkpoint}`,
  `draw_id` is the bootstrap draw, `scope=analysis`, and `role=replicate_index`;
- for `h2_bootstrap`, `unit_id=H2`, `draw_id` is the bootstrap draw,
  `scope=analysis`, and `role=scenario_unit_index`.

Every distinct complete field tuple has an independent counter. There is no
second seed format or implicit field.

`pair_id` is frozen by this table. A scenario not listed uses its own
`scenario_id` as `pair_id`.

| Paired inputs | `pair_id` | Common-random-number rule |
| --- | --- | --- |
| `SEL-AIR080-N025`, `SEL-AIR080-N1000` (C1 aliases `SEL-N025`, `SEL-N1000`) | `PAIR-C1-N` | Generate 1,000 ordered rows per group; `N025` uses the first 25. |
| `PERF-DEC001`, `PERF-DEC050` | `PAIR-C3-DEC` | Reuse `X`, outcome uniform, and group rows; apply the scenario-specific solved threshold. |
| gated and ungated policies on `SEL-AIR081-N025` | `SEL-AIR081-N025` | Use one generated audit; only the post-estimation flag policy differs. |
| `MISS-MCAR30`, `MISS-MNAR30` | `PAIR-C5-MISSING` | Reuse complete rows and missingness uniforms; apply the scenario-specific missingness transform. |
| `SEL-AIR081-N050`, `SEL-AIR081-N1000` | `PAIR-C6-COVERAGE` | Generate 1,000 ordered rows per group; `N050` uses the first 50. |

Changing a `scenario_id` never implicitly changes a paired row stream; only
this table may assign the same `pair_id`. The seed manifest stores both IDs.
Paired base rows and, for C5, missingness uniforms use `scope=shared`.
Stochastic components intentionally not shared use
`scope=scenario:{scenario_id}` with the appropriate closed role. Deterministic
thresholds, truncation, missingness transforms, and flag policies consume no RNG.

Bernoulli draws use `U < p`, where `U` is a candidate uint64 divided by
`2**64`. Standard normals use the inverse standard-normal CDF
`scipy.special.ndtri(U)` under a pinned SciPy version; exact endpoint uniforms
are replaced by the nearest interior binary64 value. The research seed manifest
and pinned environment are checked in before the first production run.

### Core DGP

Every scenario has fixed group counts and independently generated rows. `G=0`
is reference and `G=1` is comparison; `Y=1` and `D=1` are favorable. There are
two frozen generator families.

**Selection family.** For group `g`, draw latent
`D_star ~ Bernoulli(s_g)`, with `s_0 = 0.50` and
`s_1 = AIR * s_0`. Set `P=0.75` when `D_star=1` and `P=0.25` otherwise, and use
the common FairLendKit decision rule `D=I(P>=0.50)`. Thus `D=D_star` without a
decision column or group-specific threshold. Independently draw
`Y ~ Bernoulli(0.20)`. Scores and outcomes are auxiliary schema-valid inputs and
are not analyzed in selection-family confirmatory contrasts. Population
selection rates and AIR are exact.

**Performance family.** Draw `X ~ Normal(0, 1)`, set
`p_star = logistic(alpha + beta * X)`, and draw
`Y ~ Bernoulli(p_star)`. `alpha` is solved so `E[p_star]` equals the target
outcome prevalence. Positive `beta` is solved so the population AUC, evaluated
by 64-node Gauss-Hermite quadrature, equals the target AUC within `1e-6`.
Scores are:

```text
calibrated:       P = p_star
intercept_shift:  P = logistic(logit(p_star) + 0.75)
slope_distortion: P = logistic(0.60 * logit(p_star))
```

The common decision rule is `D = I(P >= t)`. The threshold `t` is solved so the
reference favorable-decision prevalence equals its scenario target within
`1e-6`. Unless an AIR scenario explicitly says otherwise, both groups share the
same DGP parameters and population AIR is `1.0`.

All solvers use IEEE-754 binary64, bracketed bisection, tolerance `1e-10`, and
at most 200 iterations; failure to converge aborts generation. Weighted
sensitivity uses `W = exp(0.75 * Z - 0.75**2 / 2)` for an independent
`Z ~ Normal(0, 1)`, giving population mean weight one. It is not confirmatory.

### Regular scenario and scenario registry

`REG` uses the performance family, `n_0=n_1=250`, outcome prevalence `0.20`,
favorable-decision prevalence `0.20`, AUC `0.70`, calibrated scores, no
missingness, no weights, `minimum_group_size=50`, 1,000 bootstrap resamples,
800 minimum valid resamples, 95% confidence, and AIR threshold `0.8`.

The registry below is exhaustive for preregistered simulation. A family varies
only the named factor(s) from `REG`; selection-family scenarios use that
family's equations and the same counts, reliability, and bootstrap settings.

| Factor | Core levels |
| --- | --- |
| Smaller-group `n` | 25, 50, 100, 250, 1,000 |
| Comparison:reference size ratio | 0.10, 0.25, 0.50, 1.00 |
| Favorable-outcome prevalence | 0.01, 0.05, 0.20, 0.50 |
| Favorable-decision prevalence | 0.01, 0.05, 0.20, 0.50 |
| Population AIR | 0.60, 0.79, 0.80, 0.81, 1.00 |
| Score discrimination (population AUC) | 0.55, 0.70, 0.85 |
| Calibration | calibrated, intercept shift, slope distortion |
| Missing fraction | 0, 0.10, 0.30 |
| Missing mechanism | MCAR, differential MAR, outcome-dependent MNAR |

Scenario IDs are generated exactly as follows; zero-padded numeric suffixes are
literal percentages except `N`, which is the row count:

- `SEL-N{025,050,100,250,1000}`: selection family, AIR `0.80`, equal group
  counts at the suffix value;
- `SEL-AIR{060,079,080,081,100}`: selection family, `n_0=n_1=250`;
- `SEL-AIR{060,079,080,081,100}-N{025,050,100,250,1000}`: the complete 5×5
  AIR-by-size interaction (duplicates of one-factor settings share results);
- `SEL-RATIO{010,025,050,100}-AIR{060,080,100}`: comparison count `250`,
  reference count `250 / ratio`, rounded only when integral (all listed are);
- `PERF-PREV{001,005,020,050}`, `PERF-DEC{001,005,020,050}`,
  `PERF-AUC{055,070,085}`, and `PERF-CAL{CAL,INT,SLOPE}`: one-factor
  performance scenarios;
- `PERF-N{025,050,100,250,1000}-PREV{001,005,020,050}` and
  `PERF-N{025,050,100,250,1000}-DEC{001,005,020,050}`: complete 5×4
  interactions;
- `PERF-AUC{055,070,085}-PREV{001,005,020,050}`: complete 3×4 interaction;
- `MISS-{MCAR,MAR,MNAR}{10,30}` plus `MISS-NONE`; and
- `STRESS-N025-PREV001`, `STRESS-N025-DEC001`, and
  `STRESS-N025-MNAR30`.

`SEL-AIR081-N025`, `SEL-AIR081-N050`, and `SEL-AIR081-N1000` are the canonical
spellings used by C4 and C6. Any scenario not
constructed by this registry is exploratory and stored outside confirmatory
result partitions.

### Missingness mechanisms

- **MCAR:** required-field missingness is `M ~ Bernoulli(m)`.
- **Differential MAR:**
  `logit Pr(M=1) = a_m + 0.75*G + 0.50*I(P<0.2)`, where `a_m` is solved so
  marginal missingness is exactly target `m` under the population DGP.
- **Outcome-dependent MNAR stress test:**
  `logit Pr(M=1) = a_m + 0.75*G + 1.00*I(Y=0) + 0.50*G*I(Y=0)`, with `a_m`
  solved for marginal target `m`. It is explicitly non-identifiable from the
  observed data alone.

One Bernoulli missingness indicator removes `Y`, `P`, and `D` together, so all
metrics use the same analyzed cohort. Separate-field missingness is reserved for
exploratory analysis. Missingness uses uniforms paired by replicate and row
across NONE/MCAR/MAR/MNAR scenarios.

Metrics are compared with the complete-data population estimand. No imputation
method is introduced in the confirmatory study.

## Public-data plan and licensing gate

No public data are downloaded or committed until the method review approves the
cohort contract and a data manifest records the source URL, retrieval date,
version/freeze date, license or public-domain basis, file hash, raw byte size,
and permitted redistribution mode.

### Primary candidate: 2024 HMDA snapshot

- Source: official FFIEC/CFPB 2024 Snapshot National Loan-Level Dataset:
  <https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2024>
- Catalog record: <https://catalog.data.gov/dataset/hmda-public-data-starting-in-2017>
- Access basis: public U.S. government data; the exact catalog and source terms
  must be archived in the manifest at retrieval time.
- Intended use: descriptive selection/denial rates, AIR, missingness, cell
  support, and deterministic subsample/geography/time stability.
- Required cohort freeze: conventional first-lien home-purchase applications
  for owner-occupied one-unit dwellings. In the primary mapping, action-taken
  codes `1` (originated) and `2` (approved but not accepted) are favorable,
  code `3` (denied) is unfavorable, and all other action codes are excluded.
  A sensitivity analysis compares originations (`1`) with denials (`3`) only.
  The mapping is verified against the official 2024 data dictionary and stored
  as a checked-in rule table.
- Protected dimensions: race/ethnicity and sex as reported in the public file;
  unknown, not provided, and not applicable remain explicit categories before
  the prespecified complete-case sensitivity analysis. Primary results analyze
  each protected dimension separately; intersectional cells are exploratory.
- Limitation: HMDA does not expose a lender model score, complete underwriting
  covariates, intent, causal treatment, or a legal-compliance ground truth. It
  cannot validate AUC, Brier score, or causal discrimination claims.

The frozen primary cohort is the complete California subset (`state_code=CA`)
of the 2024 snapshot after the rules above. County is the geography stratum;
records lacking county remain in statewide summaries but not county-stratified
H7 cells. National and adjacent-year analyses are exploratory and may be
reported only if their acquisition and compute paths remain reproducible.
Person-level HMDA rows are not committed to Git; the artifact stores the source
manifest, cohort code, permitted derived aggregates, and hashes needed to
rebuild them from the official source.

### Secondary candidate: UCI South German Credit

- Official record and DOI: <https://doi.org/10.24432/C5QG88>
- Current stated license: CC BY 4.0; attribution text and downloaded-file hash
  are required in the manifest.
- Intended use: limited score/outcome sensitivity replication if the method
  review accepts the historical label and protected-attribute construction.
- Limitations: 1970s German data, only 1,000 records, historical coding, no
  contemporary U.S. lending representativeness, and no observed production
  decision process. Any model is a study artifact, not a lender model.

South German Credit is optional. Failure of its semantic or licensing review
does not block the primary HMDA analysis. Kaggle mirrors and datasets with
unclear redistribution terms are excluded.

## Statistical analysis plan

### Monte Carlo summaries

Every scenario used by a `P2-CONFIRMATORY-V1` test or H2 generates exactly
50,000 independent replicates. Other descriptive/exploratory simulation
scenarios generate exactly 10,000. Replicate ID `r` uses the sole generator
seed construction and frozen `pair_id` table above; paired scenarios reuse
the resulting row-level base uniforms before applying scenario transformations.
Results are summarized by scenario and metric with MCSEs and 95%
simulation-error intervals. For a proportion `p`, MCSE is
`sqrt(p * (1 - p) / R)`.

Means use normal simulation-error intervals from the replicate standard error.
Error quantiles and scenario-standardized H2 summaries use 2,000 deterministic
bootstrap draws through the sole RNG format above. Summary bootstrap uses
`purpose=summary_bootstrap` and resamples replicate IDs with the Hyndman–Fan
Type 7 quantile. H2 uses `purpose=h2_bootstrap` and follows the joint
scenario-unit resampling rule above. Analysis purposes cannot produce generator
rows because their allowed scope and role values are disjoint.

Paired policy comparisons, such as gated versus ungated AIR flags, use common
random numbers and report paired risk differences with confidence intervals.
Primary conclusions rely on effect sizes and uncertainty, not only p-values.

### Confirmatory contrasts, tests, and multiplicity

The confirmatory family contains exactly C1, C3, C4, C5, and C6. Each uses the
fixed 50,000 replicate IDs (`0..49999`).
Each test has one metric, endpoint, direction, denominator, and scenario pair
defined above. Calculate its paired differences `d_r`, their mean `d_bar`,
sample standard deviation `s_d` with Bessel correction, and
`t = d_bar / (s_d / sqrt(R_valid))`. The one-sided null is `E[d_r] <= 0`; the
alternative is `E[d_r] > 0`. The raw p-value is the upper-tail probability from
Student's t distribution with `R_valid - 1` degrees of freedom.

For every test report `d_bar`, Monte Carlo standard error
`MCSE = s_d / sqrt(R_valid)`, and the one-sided 95% lower confidence bound
`d_bar - t_0.95,R_valid-1 * MCSE`, in addition to the raw and Holm-adjusted
p-values. The direction is supported only when the adjusted p-value is at most
`0.05`; the bound and effect size remain visible regardless of that decision.

The studentized mean test requires independent replicate pairs and finite
variance, both guaranteed by the DGP and independent replicate seed streams; it
does not assume symmetric paired differences or a sharp null. If `R_valid < 2`
or `s_d=0`, the test fails closed and no confirmatory p-value is emitted.
Holm's step-down procedure controls family-wise error at `0.05` across the five
raw p-values, ordered by `(p, test_id)` for ties. Report raw and adjusted
p-values, paired mean differences, standardized paired effect sizes, and
unadjusted 95% t intervals. H2, H7, every other metric, all trend analyses, and
all additional scenario comparisons are descriptive or exploratory and do not
enter this family.

At 50,000 pairs, the worst-case Bonferroni planning level `0.05/5=0.01` and 80%
power imply an approximate minimum detectable paired mean of
`(z_0.99 + z_0.80)/sqrt(50000) = 0.0142` paired standard deviations. For a
worst-case Bernoulli endpoint with standard deviation `0.5`, the conservative
MDE is about `0.0071` absolute proportion. These are planning bounds; the final
studentized tests and observed paired variances are reported. If an observed
effect below these bounds is inconclusive, the manuscript must say so rather
than add replicates solely to obtain significance.

### Public-data analysis

Public-data outputs are descriptive. For each fraction `f` in
`{0.25, 0.50, 0.75}`, create 100 non-nested deterministic Bernoulli hash
subsamples using precommitted keys `HMDA-SUB-{f}-{000..099}`. The full cohort is
the separate `f=1.00` reference, not a repeated sample. For every protected
dimension and geography stratum, report cell counts, missingness, metric states,
intervals, and across-replicate median absolute deviation (MAD) from the full
cohort estimate.

“Low support” means full-cohort unweighted cell count `<200`; “supported” means
`>=1,000`. Cells from 200 through 999 are displayed but excluded from the H7
contrast. The exploratory H7 estimand is the median cell-level MAD among
low-support cells minus the median cell-level MAD among supported cells,
reported separately by fraction and metric with a cell bootstrap interval.
Geography strata and an adjacent-year replication are descriptive sensitivity
analyses only, and the adjacent year is used only if the identical cohort rule
is valid.

No significance test converts these observations into a causal or compliance
claim. Small-cell handling follows source disclosure rules even when the source
file is public.

## Reproducibility and leakage controls

- Freeze this protocol, scenario manifest schema, seeds, package commit, Python
  version, and exact dependencies before production results are inspected.
- Separate `generate`, `analyze`, and `render` commands. Production analysis
  reads immutable raw results and never regenerates them silently.
- Store hashes for raw data, scenario manifests, result partitions, tables, and
  figures. A verification command fails closed on any mismatch.
- Unit-test population truths, label direction, threshold direction, missingness
  rates, metric mapping, and at least one hand-calculated scenario.
- Run the artifact from a clean environment on all supported Python versions.
- Keep pilot output in a separately labeled directory; pilot results cannot be
  pooled with confirmatory results.
- Analysts may debug code on null or deliberately scrambled scenarios. They may
  not inspect confirmatory outcome summaries before the pipeline and analysis
  plan are frozen.

## Stopping and amendment rules

### Fixed-run and monitoring rule

Every scenario used by a confirmatory test or H2 runs exactly 50,000 replicates;
all other registered scenarios run exactly 10,000. For the 50,000-run set,
monitoring checkpoints are `R={10,000, 20,000, 30,000, 40,000}`. At a checkpoint the system
may inspect only execution health, failure counts, deterministic hashes,
resource use, and the following blinded MC precision diagnostics: denominators,
MCSE magnitudes, and interval half-width magnitudes without effect signs,
scenario labels, confirmatory statistics, p-values, or Holm results.

There is no efficacy, futility, precision, or significance stopping. No
confirmatory estimate or p-value is calculated before all 50,000 replicates for
every member of its scenario pair are complete and frozen. Failed jobs resume
the same replicate IDs; they do not redraw or replace them.

At each scenario's fixed final `R`, report these adequacy diagnostics:

- MCSE for coverage, definedness, reliability, interval availability, flag
  availability, false-positive rate, and false-negative rate;
- normal 95% simulation-error half-width
  `1.96 * sd(absolute_error) / sqrt(50000)` for primary mean absolute error;
- the paired valid denominators for all five confirmatory contrasts; and
- whether C6 has at least 25,000 paired emitted intervals.

Failure to meet MCSE `<=0.005`, MAE half-width `<=0.01`, or the C6 denominator
is reported as `precision_limited`. A run is not extended beyond its fixed `R` and
the result is not replaced, hidden, or rerun to obtain a desired conclusion.
Summary-bootstrap draws remain fixed at 2,000. Structural zero denominators are
valid results and are not rerun to force definedness.

### Evidence-completeness stopping rule

The experiment phase is complete only when:

- every primary estimand has a validated population truth;
- all preregistered scenarios meet a precision target or are labeled
  precision-limited at the cap;
- every C1/C3–C6 contrast and H2/H7 diagnostic has a table or figure and an
  auditable analysis record;
- controlled simulation and the approved public-data analysis reproduce from a
  clean environment;
- seed sensitivity, baseline comparison, missingness ablation, and negative
  results are reported;
- an independent reviewer reproduces the key results and cannot produce a
  reasonable counterexample that invalidates an unqualified primary claim; and
- the manuscript claim table is narrowed wherever evidence is mixed.

Code completion, statistical significance, or a visually attractive plot is
not a stopping criterion.

Protocol amendments are allowed only for discovered errors, infeasible resource
requirements, source-data changes, or reviewer-mandated clarification. Each
amendment records its date, rationale, affected hypotheses, whether any affected
result had been viewed, and whether the resulting analysis is confirmatory or
exploratory.

## Baselines, ablations, and required negative results

Baselines:

- naive point estimates with every defined AIR eligible to flag;
- FairLendKit reliability-gated estimates;
- a transparent minimum-count-only gate; and
- where mathematically appropriate, a standard library/bootstrap baseline whose
  algorithm and differences are documented.

Ablations remove one reliability gate at a time, remove bootstrap eligibility,
or replace differential missingness with MCAR at the same missing fraction.

The report must include null-disparity scenarios, exact-threshold AIR `0.8`,
zero-denominator cases, scenarios where gating suppresses a true signal, and
scenarios where 95% coverage is materially below nominal. Negative or
inconclusive findings remain in the artifact and manuscript evidence table.

## Explicit non-claims

This study does not claim that:

- a metric or AIR threshold determines fairness, discrimination, legality, or
  compliance;
- reliability gates make an estimate unbiased or prove that missingness is
  ignorable;
- bootstrap coverage holds for all lending populations or dependence
  structures;
- HMDA contains a complete underwriting model, causal treatment, business
  justification, or ground-truth discrimination label;
- South German Credit represents modern U.S. applicants or production lending;
- protected-group disparities identify intent or cause;
- simulated DGPs exhaust real-world data-generating mechanisms; or
- results generalize beyond the frozen scenarios, cohorts, metrics, and
  implementation version without further validation.

## Method-review blocker traceability

| Review blocker | Normative resolution | Registered IDs |
| --- | --- | --- |
| Confirmatory family was not executable | `Preregistered claims`, `Test registration table`, and `Confirmatory contrasts, tests, and multiplicity` freeze one metric, scenario/policy pair, direction, denominator, statistic, raw alpha, and Holm family per test. | `P2-C1-AIR-MAE-N`, `P2-C3-PRECISION-DEFINED`, `P2-C4-AIR-FP-GATE`, `P2-C5-MISSINGNESS-MAE`, `P2-C6-AIR-COVERAGE` |
| DGP and scenario identities were not frozen | `Core DGP`, `Regular scenario and scenario registry`, and `Missingness mechanisms` define the counter sampler, equations, parameters, solver, `REG`, missingness coefficients, and exhaustive ID grammar. | `REG`; all `SEL-*`, `PERF-*`, `MISS-*`, and `STRESS-*` IDs in the registry |
| H2 estimand and state handling were ambiguous | `Primary operating characteristics` fixes definedness and coverage denominators, five AIR-keyed paired units, within-unit reliable-N weighting, joint bootstrap indices, invalid-draw handling, and non-causal wording. | `P2-H2-RELIABILITY-DIAGNOSTIC`; the 25 unique AIR-by-size scenario IDs grouped into five paired units |
| H7 could not identify stability | `Public-data analysis` freezes 100 non-nested outer replicates per fraction, MAD, support cutoffs, cell-bootstrap interval, and an exploratory contrast; `Public-data plan` freezes the California cohort. | `P2-H7-HMDA-STABILITY`; `HMDA-SUB-{f}-{000..099}` |
| Precision, stopping, bootstrap, and power rules were incomplete | `Monte Carlo summaries`, `Confirmatory contrasts, tests, and multiplicity`, and `Fixed-run and monitoring rule` freeze 2,000 summary draws, seed material, adequacy boundaries, blinded checkpoints, fixed 50,000-run confirmatory/H2 analysis, and conservative 80% MDEs. | all `P2-CONFIRMATORY-V1` tests, H2, and every registered scenario's fixed final R |

### Architecture-decision replacement map

| Superseded clause | Frozen replacement |
| --- | --- |
| Sign-flip randomization test for paired differences | One-sided studentized mean test on replicate-level differences, with `d_bar`, MCSE, one-sided 95% lower bound, raw p-value, and Holm-adjusted p-value. |
| Confirmatory analysis fixed at the first 10,000 replicates, with later precision extensions | Every confirmatory test uses exactly replicate IDs `0..49999`; checkpoints at 10k/20k/30k/40k are blinded run-quality monitoring only, with no early stopping. |
| C6 direction described only in prose | `d_r = I_cover_1000 - I_cover_050`; positive values support greater coverage at `N=1000`. |
| H2 stratified bootstrap sampled reliability states separately, then an interim union bootstrap did not define paired units | Five AIR-keyed units pair each `N025` scenario with the equal-weight mean of its four reliable-N scenarios. One shared five-index vector resamples both sides through `delta_a`; fewer than 1,900 valid draws yields `not_estimable`. |
| H2 scenario set expressed by brace grammar and aliases | The normative section lists all 25 unique IDs explicitly; aliases are excluded. |
| 10,000-pair power bound (`0.0317` SD; `0.0159` worst-case proportion) | 50,000-pair bound (`0.0142` SD; `0.0071` worst-case proportion) at conservative one-sided planning level `0.01` and 80% power. |
| Generator seed included `scenario_id` while prose claimed different scenarios shared row streams; separate summary/H2 formats created multiple roots | One seven-field root format covers all purposes. Generator rows use frozen `pair_id` plus explicit `shared` or `scenario:{scenario_id}` scope; summary/H2 use disjoint allowed analysis fields. The pair table freezes shared streams and deterministic transforms. |

## Protocol amendment log

### A1 — unify RNG root derivation and paired streams

- **Date:** 2026-10-08
- **Base protocol:** `main@9fd45de`
- **Reason:** post-merge method review found that the generator root included
  `scenario_id` while paired scenarios were required to share row streams. The
  base protocol also specified separate summary and H2 seed formats, leaving
  multiple plausible roots.
- **Change:** replace the RNG-only clauses with one seven-field seed-material
  format; replace `pairing_id` with `pair_id`; freeze shared versus
  scenario-specific scopes; place summary and H2 sampling under closed analysis
  purposes of the same root.
- **Affected registered analyses:** C1, C3, C4, C5, C6, H2, and all secondary
  summaries that consume random resampling indices.
- **Unchanged:** research questions, hypotheses, DGP probability distributions,
  scenario registry, estimands, test statistics, `R=50,000`, Holm family,
  stopping/monitoring rules, public-data cohort, and non-claims.
- **Random-stream compatibility:** breaking relative to the ambiguous RNG text
  in `9fd45de`; generated bytes and random streams must follow A1 only after A1
  is approved and merged. No prior stream is grandfathered.
- **Result exposure:** no data were downloaded, no experiment implementation
  was written or run, and no pilot, confirmatory, or public-data result was
  viewed before proposing A1.
- **Activation:** pending. Until this amendment is approved and merged, the
  authoritative protocol remains `main@9fd45de` and confirmatory runs remain
  frozen.

## Required outputs before a paper release

- approved protocol and amendment log;
- machine-readable scenario and seed manifests;
- data cards, source/license records, cohort rules, and SHA-256 manifests;
- locked environment and one-command clean reproduction;
- raw aggregate results sufficient to recompute every table and figure;
- baseline, ablation, sensitivity, and failure-case outputs;
- claim-to-evidence table with limitations;
- independent reproduction report; and
- immutable Git tag, GitHub Release, `CITATION.cff`, and Zenodo-ready archive.

The artifact may live in a dedicated research repository, but it must pin the
exact FairLendKit release and must not describe research-only code as a product
capability.
