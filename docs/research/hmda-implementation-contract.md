# HMDA conditional-disparity implementation contract

Status: `implementation_ready / no_results`

Contract ID: `HMDA-CA-2024-CD-V1`

This document makes the reviewed
[`conditional-disparity-and-hmda-case-study.md`](conditional-disparity-and-hmda-case-study.md)
design executable. It authorizes deterministic acquisition, validation, cohort
construction, and analysis infrastructure. It does not authorize result prose,
causal claims, discrimination findings, or legal conclusions.

## 1. Frozen source identity

The only admissible primary input is the official 2024 Snapshot National
Loan-Level Dataset, Loan/Application Records (LAR), CSV archive.

```yaml
source_id: ffiec_hmda_2024_snapshot_public_lar_csv
publisher: FFIEC / CFPB
landing_page: https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2024
download_url: https://files.ffiec.cfpb.gov/static-data/snapshot/2024/2024_public_lar_csv.zip
activity_year: 2024
snapshot_freeze_date: 2025-05-19
format: application/zip
archive_bytes: 664242987
archive_sha256: 9383890f38c2ae1ef46942e72e1a2a211aa0b979c0e46db5fd6d7eb8669f22c1
observed_last_modified: 2025-11-21T18:27:51Z
observed_etag: '086bfba8d9c79b73925bfb5476b0b9ec-26'
identity_checked_at: 2026-11-03T03:02:28Z
redistribution: do_not_commit_or_redistribute_row_level_archive
```

The SHA-256 was computed by streaming the exact official archive without
retaining it in the repository. `ETag` is supporting metadata, not a substitute
for SHA-256. A byte mismatch, redirect outside `files.ffiec.cfpb.gov`, more than
one regular CSV member, encryption, path traversal, or uncompressed-size limit
violation fails with `hmda_source_identity_mismatch`. A publisher revision
requires a versioned contract review.

Admission records the ordered header, member name and size, row count, and
header SHA-256. These are derived evidence, never caller declarations. Raw rows
and application-level extracts must not be committed to Git.

## 2. Executable field and code rules

The implementation checks in a machine-readable rule table. Categorical codes
are trimmed strings and are never silently coerced to numbers.

### 2.1 Ordered cohort rules

| Order | Field | Required value | Exclusive exclusion reason |
| ---: | --- | --- | --- |
| 10 | `activity_year` | `2024` | `hmda_wrong_activity_year` |
| 20 | `state_code` | `CA` | `hmda_outside_california` |
| 30 | `loan_type` | `1` conventional | `hmda_nonconventional_loan` |
| 40 | `lien_status` | `1` first lien | `hmda_not_first_lien` |
| 50 | `loan_purpose` | `1` home purchase | `hmda_not_home_purchase` |
| 60 | `occupancy_type` | `1` principal residence | `hmda_not_owner_occupied` |
| 70 | `construction_method` | `1` site-built | `hmda_not_site_built` |
| 80 | `total_units` | `1` | `hmda_not_one_unit` |
| 90 | `action_taken` | primary: `1`, `2`, `3` | `hmda_action_outside_primary_contrast` |

Primary `favorable_action` is `1` for action `1` (originated) or `2`
(approved but not accepted), and `0` for action `3` (denied). No other code is
relabeled. `HMDA-SENS-ACTION-13` reruns the flow with only `1` versus `3`.

Exact duplicate physical rows are not collapsed. A fingerprint over the full
ordered source row is reported. Any duplicate fails with
`hmda_duplicate_rows_detected` until a reviewed deduplication amendment exists.

### 2.2 Required fields and parsing

```text
activity_year, lei, state_code, county_code, census_tract,
action_taken, loan_type, lien_status, loan_purpose, occupancy_type,
construction_method, total_units, loan_amount, income,
debt_to_income_ratio, combined_loan_to_value_ratio, property_value,
loan_term, applicant_age, derived_ethnicity, derived_race, derived_sex
```

Missing fields fail with `hmda_schema_required_field_missing`. Unknown codes
fail with `hmda_code_value_invalid`; they are not converted to missing. Numeric
parsing rejects separators, infinity, and non-finite values. Empty, `NA`,
`Exempt`, ranges, and publisher special codes remain distinct typed states.

## 3. Protected and reference groups

Each dimension is analyzed separately and never used as a risk control.

- Ethnicity: focal `Hispanic or Latino`; reference `Not Hispanic or Latino`.
- Race: focal `Black or African American`; reference `White`.
- Sex: focal `Female`; reference `Male`.

Use the corresponding published `derived_*` field exactly. Joint/multiple,
free-form, unknown, not provided, not applicable, and unavailable categories
remain in the descriptive flow and are excluded only from the named binary
estimand with a stable `hmda_group_not_in_binary_*_contrast` reason. Reference
groups cannot change after results are viewed. Intersectional analysis is
exploratory and inherits every support and disclosure gate.

## 4. Control manifest

The checked-in manifest contains `field`, `role`, `coding`, `missing_rule`,
`rationale`, and `allowed_analyses`.

### 4.1 Core controls

- `loan_amount`: dollars; `log1p`; nonpositive/invalid is missing.
- `income`: published thousands of dollars; primary coding preserves signed
  values in the flow and treats nonpositive values as missing for log models.
- `debt_to_income_ratio`: reviewed bands below; `Exempt` is distinct.
- `combined_loan_to_value_ratio`: numeric percentage; `Exempt` is distinct;
  numeric values outside `[0,1000]` are invalid.
- `property_value`: dollars; `log1p`; nonpositive/invalid is missing.
- `loan_term`: integer months `[1,600]`; otherwise invalid.
- `applicant_age`: published categories; special values remain typed.
- `county_code`: geography; missing is retained statewide and excluded only
  from county specifications.
- `lei`: allowed only in the named lender fixed-effect/cluster sensitivity.

The cohort fields in section 2 are constants, not risk controls.

### 4.2 Prohibited controls and unavailable concepts

No adjusted model may use `action_taken`, derived outcomes, denial reasons,
purchaser type, rate spread, interest rate, prepayment term, origination
charges, discount points, lender credits, total costs, points and fees, HOEPA
status, loan price, or any post/joint-decision field. Protected fields and their
components define groups, not controls.

Complete credit history, verified assets, lender score, fraud indicators,
pricing exceptions, and detailed underwriting judgment are unavailable and
must not be replaced with invented proxies. Manifest drift fails with
`hmda_control_manifest_mismatch`.

## 5. Strata, bins, support, and overlap

All boundaries are frozen before outcome computation:

```yaml
income_thousands: ['(-inf,0]', '(0,50]', '(50,100]', '(100,150]', '(150,250]', '(250,inf)']
loan_amount_dollars: ['(0,100000]', '(100000,250000]', '(250000,500000]', '(500000,750000]', '(750000,inf)']
dti_percent: ['<30', '30-36', '37-43', '44-49', '50-60', '>60', 'Exempt']
cltv_percent: ['[0,60]', '(60,80]', '(80,90]', '(90,100]', '(100,1000]', 'Exempt']
```

The primary stratum key is their Cartesian product. A stratum is supported only
when each group has at least 30 rows and at least 5 favorable and 5 unfavorable
outcomes. No post-result pooling is allowed. The target is the pooled empirical
distribution restricted to common-support strata.

Report retained/excluded rows by group, retained strata, one-group strata,
sparse-outcome strata, and supported target fraction. Standardization is
`not_estimable` with `hmda_common_support_insufficient` if either group retains
less than 70%, overall supported fraction is below 70%, or fewer than 20 strata
remain.

Regression uses the same common-support population. Continuous transformations
are fixed by the manifest; categorical terms use treatment coding with the
lexically first nonmissing category as reference. No stepwise selection or
unregistered interactions. Separation, non-convergence, singular design, or
invalid predictions fail closed. Propensity scores are diagnostics only;
weighting requires a reviewed amendment.

## 6. Estimands and formulas

All differences are `focal - reference`; ratios are `focal / reference`.

- Unadjusted: `p_g = favorable_g / eligible_g`; report rates, difference, and
  ratio only when the reference rate is positive.
- Standardized: for supported stratum `s`, `w_s = n_s / sum(n_s)` over the
  pooled target. Group rate is `sum(w_s * p_gs)`; zero denominators are never
  imputed.
- Regression adjusted: fit the frozen logistic model with group plus core
  controls. Predict every supported row once as focal and once as reference;
  report the mean paired prediction difference.

The three estimands are separate artifact objects. Adjusted estimates are
conditional associations, not causal effects or explanations.

## 7. Variance, confidence intervals, and multiplicity

- Unadjusted rates: two-sided Wilson 95% intervals; differences: two-sided
  Newcombe/Wilson; ratios: log-ratio only with positive counts/denominators.
- Standardized: cluster bootstrap by `lei`, 1,000 replicates, seed `20241119`,
  percentile `0.025/0.975`. Each replicate reapplies support. Fewer than 950
  valid replicates fails with `hmda_bootstrap_insufficient_valid_replicates`.
- Regression: lender-clustered sandwich covariance by `lei`, delta-method
  two-sided normal 95% intervals. Fewer than 30 lender clusters, covariance
  failure, or non-convergence makes the estimand not estimable.
- The three primary protected dimensions form one confirmatory family per
  estimand. Report raw intervals and Holm-adjusted two-sided p-values.

Artifacts record method IDs, versions, seed, replicate counts, valid counts,
cluster counts, and formula version. Any change alters configuration SHA-256.

## 8. Missingness and sensitivity

Primary adjusted analyses use complete cases for registered core controls,
reporting exclusions per field and group. They are not population estimates.
Mandatory named sensitivities retain the design IDs: action `1` versus `3`;
valid explicit missing categories; core versus reviewed extended controls;
alternate bins; statewide versus supported counties; lender structure;
alternate support; and adjacent year only after separate source admission.
Multiple imputation is not authorized in V1.

## 9. Cohort flow and reconciliation

The ordered flow records archive/member admission, parsed rows, each cohort
exclusion, invalid codes/numerics, primary outcome rows, group exclusions,
complete-case exclusions, support exclusions, and final rows per estimand.
At every stage `input = included + sum(excluded_by_reason)`. Reasons are
mutually exclusive within a stage. Failure to reconcile yields
`hmda_cohort_flow_not_reconciled`.

## 10. Artifacts and disclosure

Separate JSON artifacts cover source admission, cohort flow, field/control
manifests, configuration, support diagnostics, and each estimand. Each includes
schema version, contract ID, commit, command, UTC timestamp, environment,
source/configuration SHA-256, and deterministic row-set digest. Runtime paths
and timestamps are excluded from semantic equality.

Artifacts may not contain application rows, direct identifiers, free-form
responses, or cells below 30. Small cells are suppressed, not rounded into a
publishable value.

## 11. Fail-closed publication gate

Initial state is:

```yaml
evidence_class: public_data_associational_research
constraint_status: failed
candidate_copy_status: locked_research_only
results_emitted: false
```

Passing requires source/schema identity, cohort reconciliation, group and
control contracts, missingness, support, estimation, variance, sensitivities,
disclosure, and artifact reproduction. Failure clears normalized results and
conclusion fields, keeps the lock, and emits one primary plus ordered secondary
reasons. Required reasons include:

```text
hmda_source_identity_mismatch
hmda_archive_contract_invalid
hmda_schema_required_field_missing
hmda_schema_digest_mismatch
hmda_code_value_invalid
hmda_duplicate_rows_detected
hmda_control_manifest_mismatch
hmda_cohort_flow_not_reconciled
hmda_group_contract_invalid
hmda_common_support_insufficient
hmda_model_nonconvergence
hmda_model_separation
hmda_cluster_count_insufficient
hmda_bootstrap_insufficient_valid_replicates
hmda_disclosure_gate_failed
hmda_artifact_reproduction_mismatch
```

Computational success permits evidence review, not publication. Result prose
requires separate review and must retain the observed/conditional,
incomplete-underwriting, bounded-support, non-causal, non-discrimination, and
non-legal limitations.

## 12. Acceptance tests before analysis

Tests use synthetic fixtures only and cover:

1. exact archive SHA/size and one-byte mismatch;
2. unsafe, multiple, and encrypted archive members;
3. required columns, header order, and schema drift;
4. all cohort codes and exact flow reconciliation;
5. action `1/2` versus `3` and sensitivity `1` versus `3`;
6. group/reference categories and unknown preservation;
7. leakage rejection and control-manifest drift;
8. bin boundaries, sparse/one-group strata, and overlap failure;
9. all three estimand formulas on a tiny fixture;
10. interval methods, seed reproducibility, cluster and invalid-bootstrap paths;
11. missing/special/invalid values and complete-case counts;
12. suppression and absence of row-level output;
13. failed gates clearing values and retaining `locked_research_only`; and
14. identical source/config/code producing semantically identical artifacts.

Observed HMDA outcomes must never be embedded into tests to make assertions
pass.
