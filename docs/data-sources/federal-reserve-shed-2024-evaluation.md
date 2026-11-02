# Federal Reserve SHED 2024 public-use data evaluation

Evaluation timestamp: `2026-11-02T05:25:25Z`. Admission remains
`evidence_incomplete`; the files are not formally adopted. The maximum
provisional boundary is `external_only + quality_only`, and project
redistribution is prohibited because no dataset-specific redistribution grant
was located.

## Official identity and structure

The official Board SHED page links the exact 2024 CSV ZIP and codebook pinned in
the adjacent manifest. The page identifies the codebook as last updated May 28,
2025. The unencrypted ZIP has one member, `public2024.csv`: 12,295 rows and 751
columns, with no duplicate rows. No raw or transformed respondent rows are
committed. The ordered, case-sensitive schema is pinned by SHA-256, so a renamed,
reordered, added, or removed field fails closed rather than passing on shape
alone. The complete 751-column ordered header is retained in the adjacent
`federal-reserve-shed-2024-schema.json` evidence file.

The longitudinal `shedid` is non-null and unique in this snapshot. It is used
only for local integrity checks and is prohibited from features, outputs, logs,
fixtures, or cross-source linkage. Its exact name and zero-based position `0`
are pinned; analysis-column construction removes exactly one case-sensitive
`shedid` and rejects missing or case-colliding variants. State, age, gender,
race/ethnicity, education,
income, disability, employment, housing, family, credit, debt, and hardship
fields are sensitive or proxy-bearing and require disclosure controls.
The actual schema contains no second case-ID column. The longitudinal `shedid`
values include current and historical case cohorts from 2013 through 2024;
their cohort counts are pinned, and blank, malformed, missing-cohort, or
unexpected-cohort evidence fails closed.

## Weights, missingness, and imputation

The codebook defines `weight` and `weight_pop` for the full 2024 cross-section,
and `panel_weight` and `panel_weight_pop` only for respondents in both the 2023
and 2024 surveys. All present weight values are finite and positive; panel
weights are blank for 8,280 non-panel rows. Exact blank/non-finite/zero/negative
counts and ranges are pinned and fail closed in code.

Across all cells, 2,159,319 are blank; 254 columns contain blanks and 497 are
complete. Blanks retain their field-specific skip/nonresponse meaning. The 342
`*_iflag` columns contain 4,191,995 zeros (“not imputed”) and 12,895 ones
(“imputed”), with no blanks. Codebook-labelled responses are separate from
missingness: 20,300 “not asked”, 4,313 “don't know”, and 537 “refused” cells.
These totals are derived from the manifest's codebook-specific column/value
mapping, including the unlabeled `ind1` codes `-2` and `-1`; the mapping has its
own deterministic SHA-256 and any column, value, or category drift fails closed.

## Fitness and boundaries

SHED supports weighted aggregate research on household financial well-being,
bill payment, emergency expenses, credit access, housing, representation,
missingness, imputation, and proxy pathways. It is a household survey, not a
transaction ledger, utility/rent ledger, underwriting record, or observed loan
performance dataset. Hardship, inability to cover expenses, denied credit, and
late bills must retain their survey meanings and are not default labels.

Prohibited uses include individual scoring, underwriting, eligibility or
adverse-action decisions, reidentification, cross-source linkage, fictional
cash-flow reconstruction, and production claims. Formal adoption and
redistribution require a verified rights basis beyond public download access.

Citation supplied by the codebook:

> Board of Governors of the Federal Reserve System. (2025). *Survey of
> Household Economics and Decisionmaking* [Dataset].
> <https://doi.org/10.17016/datasets.002>
