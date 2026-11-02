# EIA Residential Energy Consumption Survey 2020 public microdata v7

- Candidate ID: `eia-recs-2020-v7`
- Priority: 5
- Review status: `evidence_incomplete`
- Publisher: U.S. Energy Information Administration
- Publisher class: government
- Canonical microdata page:
  <https://www.eia.gov/consumption/residential/data/2020/index.php?view=microdata>
- Official CSV:
  <https://www.eia.gov/consumption/residential/data/2020/csv/recs2020_public_v7.csv>
- Official codebook:
  <https://www.eia.gov/consumption/residential/data/2020/xls/RECS%202020%20Codebook%20for%20Public%20File%20-%20v7.xlsx>
- Method guide:
  <https://www.eia.gov/consumption/residential/data/2020/pdf/microdata-guide.pdf>
- Exact release/version: 2020 RECS public microdata v7
- License/redistribution: EIA's official Copyrights and Reuse page permits use
  and distribution of EIA data, files, and databases, subject to attribution
  guidance and exclusion of identified third-party material
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

RECS provides household-level energy characteristics, consumption/expenditure
estimates, housing context, demographics, weights, and replicate weights. It is
suited to utility coverage, expenditure, energy burden, representation, and
proxy-pathway research. It is not a monthly payment ledger and does not establish
timeliness, arrears, reversals, interruption, or credit default unless an exact
official field says so.

The official page describes nearly 18,500 sampled households statistically
selected to represent 123.5 million U.S. housing units occupied as primary
residences. Population estimates therefore require `NWEIGHT`, and uncertainty
requires the 60 replicate weights; unweighted rows are not nationally
representative estimates. Exact row-level geographic granularity remains
unverified. Separate EIA state tables do not establish that state or finer
geography exists in the public microdata.

Required evidence: terms, attribution, redistribution and automated-access
review, file size/hash, field/imputation/replicate-weight matrix, reference and
release times, and a `quality_only` approved-use record.

## Enablement plan

- Target: `repository` for the public CSV/codebook if EIA terms permit;
  otherwise `external_only` with official URL, byte hash, and cache workflow.
- Contact: EIA RECS program/data support through the official RECS contact route.
- Ask for: redistribution/attribution confirmation, stable v7 status, checksum
  availability, revision policy, and correct replicate-weight use.
- Next evidence: capture EIA website terms and v7 publication metadata, then
  verify the official file manifest after retrieval is authorized.
- Parallel work: synthetic RECS-shaped household fixture; adapter contracts for
  energy expenditures, service types, imputation flags, main and replicate
  weights, and annual reference periods.
- Deliverables after approval: adapter, weighted quality/coverage example,
  utility data card, variance tests, and source verifier.
- Unacceptable condition: official terms bar intended use or public fields have
  disclosure constraints incompatible with repository-safe outputs.

## Verified official metadata snapshot

Official HEAD metadata checked 2026-11-01 without retrieving bodies:

- v7 CSV: 56,044,261 bytes, last modified 2024-01-22;
- v7 codebook: 58,382 bytes, last modified 2024-01-22;
- microdata guide: 581,524 bytes, last modified 2023-06-07; and
- EIA's Copyrights and Reuse page states that U.S. government publications are
  public domain and that EIA data/files/databases may be used or distributed,
  with source/date acknowledgment requested; third-party protected items remain
  excluded from that permission.

The metadata-only [`eia-recs-2020-v7-manifest.json`](eia-recs-2020-v7-manifest.json)
records these facts. Publisher checksums, actual SHA-256, official release date,
column inventory, and confirmation that no member is third-party remain open.
Status stays `evidence_incomplete`; manifest-level and member-level
redistribution remain `unverified` despite a credible path to `repository`.

The 2026-11-02 metadata recheck is recorded in
[`../investigations/eia-recs-2020-v7-metadata-2026-11-02.md`](../investigations/eia-recs-2020-v7-metadata-2026-11-02.md).
It reconfirms all three fixed endpoint sizes, media types, modification times,
and validators without reading their bodies. It also confirms the official
July 2022 / June 2023 / January 2024 release history and EIA reuse terms. No DOI,
immutable publisher release ID, or publisher checksum was found, so those
fields remain null.

## Field, weight, and imputation evidence

The official v7 codebook was inspected as documentation only; the row-level CSV
was not retrieved. It establishes these semantics:

- `DOEID` is a respondent identifier and must be discarded before any report,
  log, exception, cache key, or exported fixture;
- `NWEIGHT` is the final analysis weight, and `NWEIGHT1` through `NWEIGHT60`
  are the 60 final analysis replicate weights;
- variables prefixed with `Z` are field-specific imputation indicators where
  the codebook explicitly pairs them with a measure; values are not inferred
  from the prefix alone;
- for many household fields, indicator values distinguish `1 Imputed`, `0 Not
  imputed`, and `-2 Not applicable`; these states must remain separate from
  ordinary missingness;
- `PERIODEL` records electricity billing-data coverage bands, while analogous
  period fields exist for other fuels; annual totals can therefore have
  unequal source coverage and cannot be treated as uniformly observed; and
- `ZELAMOUNT` distinguishes no imputation, amount-and-cost imputation, and an
  electricity-amount-only solar case. Other fuel amount flags have their own
  documented domains and must not inherit the electricity mapping.

The official microdata page says the first 2020 release contained preliminary
household characteristics, the June 2023 release added final consumption,
expenditure, and end-use estimates, and later updates added variables through
January 2024. This is why the adapter must require v7 rather than accepting an
unversioned “2020 RECS” file.

The official microdata guide is the required authority for estimate and
relative-standard-error calculations. Until its replicate-weight procedure is
encoded as an independently reviewed contract and golden fixture, the project
must not substitute an ordinary unweighted variance, silently normalize
weights, or publish uncertainty estimates.

## Proposed use boundary; no admission yet

Any future admission is `quality_only` by default. Permitted research claims
are limited to utility-data coverage, energy expenditure/consumption quality,
imputation prevalence, weighted representation, and coverage differences.

Demographics, income/socioeconomic context, household composition, housing and
tenure, geography/climate, energy equipment/fuels, hardship, consumption, and
expenditures can form protected-class or socioeconomic proxies and rare linkage
combinations. `DOEID` must never appear in outputs or joins. RECS must not be
used for individual scoring, underwriting, creditworthiness inference, or a
claim of causal or unlawful discrimination; group analysis must remain
descriptive, weighted, support-qualified, and explicit about proxy pathways.

`SCALEE`, `NOHEATEL`, `NOHEATNG`, and related hardship fields may support
clearly labeled survey-based coverage or hardship analysis. They are not loan
performance labels. A disconnection notice, inability to afford service, an
imputed amount, short supplier-data coverage, or missing utility service must
not be renamed as delinquency, default, adverse behavior, or a consumer credit
outcome. RECS supplies no verified credit decision time, performance window,
or mature binary credit outcome, so `risk_eligible` remains false.

Remaining blockers are publisher/repository hashes, row-level schema and null
token verification after retrieval authorization, third-party-member review,
the exact official release date, and an approved replicate-weight calculation
contract. No RECS data may be downloaded or committed while these remain open.
