# EIA RECS 2020 public microdata v7 evaluation

Evaluation date: 2026-11-02. Disposition: suitable for an external-only,
`quality_only` research source. No downloaded source file is committed.

## Official artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `recs2020_public_v7.csv` | 56,044,261 | `8d5f6d3120d2cbc2535151c7d455e7a536ca9768f773e15edd45932ec38b3592` |
| `RECS 2020 Codebook for Public File - v7.xlsx` | 58,382 | `747f5a3d39a1f3b34c4f5041a388c556664497bb4c74c5cac71a97f157f0ad07` |
| `microdata-guide.pdf` | 581,524 | `db26d4e23ec544e19426e8553fbf8bba6305ba8bb9b7cae823188785ec7449fa` |

All three files were downloaded directly from the fixed EIA RECS 2020
endpoints. The workbook is an unencrypted, macro-free XLSX with no external
links. The guide has a valid PDF 1.6 signature. No third-party copyright or
license marker was found in the workbook package or PDF metadata; users must
still preserve EIA source/date acknowledgment and exclude any separately
identified third-party material under EIA's reuse terms.

## Data checks

The CSV parses as 18,496 rows and 799 columns, with no duplicate rows.
`DOEID` is present, non-null, and unique; it is an isolation/integrity key only
and must be dropped before features, outputs, logs, fixtures, or links. The file
contains `NWEIGHT` and exactly `NWEIGHT1` through `NWEIGHT60`, with no additional
replicate-weight columns. It contains 256 `Z*` columns, including documented
imputation indicators, and the reviewed hardship fields `SCALEE`, `NOHEATEL`,
and `NOHEATNG`.

There are 653 parser-null cells across 10 columns. These require field-specific
codebook handling; they must not be collapsed with documented negative or
not-applicable codes. Population estimates require `NWEIGHT`, and uncertainty
estimates require the official replicate-weight method. Raw row counts are not
national population estimates.

## Use boundary

Suitable uses are weighted, support-qualified research on energy coverage,
consumption/expenditure quality, imputation, household representation, and
proxy pathways. RECS is not payment-transaction data and supplies no verified
credit outcome, decision time, or performance window. It must not be used for
individual scoring, underwriting, creditworthiness inference, or as evidence
of delinquency/default or causal discrimination. Demographic, socioeconomic,
housing, hardship, geography/climate, fuel, consumption, and expenditure
variables can act as sensitive proxies and require aggregate fairness controls.

Suggested attribution (EIA supplies no DOI or publisher-issued citation):
“U.S. Energy Information Administration, Residential Energy Consumption
Survey (RECS), 2020 public microdata v7, January 2024.”
