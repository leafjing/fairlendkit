# Federal Reserve SHED 2024 metadata investigation

- Investigation date: `2026-11-02`
- Scope: official-page and HTTP-metadata review only
- Body retrieval: official HTML pages only; no ZIP, CSV, or PDF body retrieved
- Candidate: `federal-reserve-shed-2024`
- Result: suitable for direct content evaluation under an `external_only` and
  `quality_only` ceiling; redistribution and production-credit use remain
  prohibited

## Official identity

The publisher is the Board of Governors of the Federal Reserve System. The
canonical SHED data page is:

<https://www.federalreserve.gov/consumerscommunities/shed_data.htm>

The page currently identifies the following 2024 artifacts:

- codebook:
  <https://www.federalreserve.gov/consumerscommunities/files/SHED_2024codebook.pdf>
- CSV package:
  <https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2024_(CSV).zip>

The page labels the codebook `Last updated: May 28, 2025` and the 2024 survey
data `Last updated: February 9, 2026`. Its update note says the CSV remains
available after discontinuation of SAS files and that datasets and codebooks
were updated to include a new unique identifier. Consequently, `2024` is the
survey year, not an immutable package version. The publisher supplies neither a
release ID nor a checksum. Retrieval evidence must therefore pin the exact URL,
byte count, ETag, Last-Modified value, retrieval time, archive members, and a
locally computed SHA-256.

HEAD observations at `2026-11-02T05:24:10Z`:

- codebook: `200`, `application/pdf`, 848,401 bytes,
  `Last-Modified: Mon, 09 Feb 2026 17:04:16 GMT`, ETag
  `"18424d1fe699dc1:0"`;
- CSV ZIP: `200`, `application/x-zip-compressed`, 3,787,684 bytes,
  `Last-Modified: Mon, 09 Feb 2026 17:04:16 GMT`, ETag
  `"95a18d1fe699dc1:0"`.

The page label and HTTP `Last-Modified` are separate facts and must not be
silently converted into one release date.

## Survey design and weights

The official 2024 report says the survey was fielded from 2024-10-18 through
2024-10-31 using Ipsos KnowledgePanel, a probability-based online panel
recruited through address-based sampling. Of 17,884 invited panel members,
12,393 completed the survey; after 98 quality exclusions, the report uses
12,295 respondents. The cumulative response rate is 4.0 percent.

The target population is U.S. adults age 18 or older. Post-stratification
adjusts for age, gender, race, ethnicity, census region, metropolitan status,
education, and household income against March 2024 Current Population Survey
benchmarks. The weighted sample represents an estimated 259 million U.S.
adults. All population estimates must use the appropriate weight; unweighted
row counts are not population estimates.

About one-third of respondents also participated in the 2023 survey. The public
file includes prior-year case identifiers and weights for this repeated subset.
All current and prior-year case identifiers are linkage-sensitive: they may be
used only for isolated integrity checks and approved longitudinal research, and
must not enter features, user-facing output, routine logs, or cross-source
linkage.

The official methodology also records important representation limits:

- address-based sampling may miss people experiencing homelessness;
- institutionalized people and active-duty military personnel are outside the
  stated benchmark population;
- the English-language online mode can leave residual coverage and response
  bias even after weighting; and
- weighting corrects observed margins, not every form of non-response or
  selection bias.

## Missingness and imputation

The report states that item non-response was generally below one percent, but
was higher for some questions. Binary, categorical, ordered, and continuous
items use regression-based imputation; rent and mortgage amounts use hot-deck
imputation. Each public variable normally has a corresponding `_iflag` field
whose value identifies an imputed observation. Some open-text questions and
`ND1_e` are not imputed.

Content evaluation must keep at least four states distinct:

1. observed answer;
2. imputed answer identified by its `_iflag`;
3. structurally out-of-universe or skipped answer; and
4. unresolved missing or special response code.

It must validate weight and imputation-flag types, finite values, ranges, and
counts, and fail closed when schema, row count, archive identity, weight
statistics, or missing/special-code aggregates drift.

## Fields and FairLendKit boundary

The survey covers household financial well-being, income and expenses,
savings, banking and credit, housing, employment, care work, education and
student loans, and demographics. These are self-reported survey responses, not
bank transactions, payment ledgers, verified income, or observed loan
performance.

Permitted evaluation is limited to `quality_only` research such as weighted
coverage, representation, missingness, imputation behavior, survey robustness,
and aggregate financial-well-being benchmarks. Self-reported hardship, bill
difficulty, credit denial, or inability to cover an emergency expense must not
be relabeled as default or used as an individual credit outcome.

Protected and proxy-sensitive fields include age, gender, race, ethnicity,
education, income, household composition, geography, disability-related
responses, housing, and credit experiences. They may support aggregate fairness
audits under minimum-cell and disclosure controls, but not production scoring.
The low cumulative response rate, online-panel mode, imputation, and historical
survey context further rule out production underwriting use.

## Terms and redistribution

No dataset-specific license or affirmative redistribution grant was found on
the canonical SHED data page. The general Board website-linking policy governs
links and third-party material; it is not a public-use-data redistribution
license. Public download availability therefore does not authorize repository
redistribution.

Project disposition is fixed to:

- storage: `external_only`;
- analytical ceiling: `quality_only`;
- redistribution: `prohibited`;
- raw or transformed rows in the repository: prohibited.

If later publisher terms affirm broader reuse, that must undergo a separate
review; it does not retroactively change this investigation.

## Official citation

The Board does not publish a dataset-specific citation string on the data page.
Use a publisher-and-title citation that identifies both the data page and the
associated report:

> Board of Governors of the Federal Reserve System. “Survey of Household
> Economics and Decisionmaking: Data — 2024 Survey Data.” Updated February 9,
> 2026. <https://www.federalreserve.gov/consumerscommunities/shed_data.htm>.

> Board of Governors of the Federal Reserve System. *Economic Well-Being of
> U.S. Households in 2024*. Washington, DC, May 2025.
> <https://www.federalreserve.gov/publications/2025-economic-well-being-of-us-households-in-2024-executive-summary.htm>.

The first date describes the page's current data update, not the survey field
period or an immutable release identifier.

## Content-evaluation requirements

Before any adapter or benchmark is approved, the implementation must:

- pin the official CSV URL and current HTTP identity;
- compute archive and member hashes without committing row data;
- enumerate members, schema, rows, columns, and exact weight/case-ID fields;
- validate weight, imputation, skip, missing, and special-code aggregates;
- quarantine current and prior-year case identifiers;
- enforce `external_only`, `quality_only`, and redistribution prohibited; and
- document any difference between the 12,295-report sample and retrieved rows.
