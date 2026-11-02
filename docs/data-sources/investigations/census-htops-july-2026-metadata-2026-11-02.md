# Census HTOPS Household Pulse July 2026 metadata investigation

- Investigation date: `2026-11-02`
- Scope: official HTML pages and HTTP response metadata only
- Microdata/document bodies retrieved: none
- Candidate: `census-htops-hps`
- Selected release: July 2026 cross-sectional Household Pulse PUF
- Result: suitable for direct content evaluation under an `external_only` and
  `quality_only` ceiling

## Selection and official identity

The publisher is the U.S. Census Bureau. The authoritative entry points are:

- HTOPS overview: <https://www.census.gov/programs-surveys/htops.html>
- PUF page:
  <https://www.census.gov/programs-surveys/household-pulse-survey/data/datasets.html>

As of the investigation date, the PUF page lists March, May, and July 2026.
July is the latest available public microdata release. It was collected from
2026-07-15 through 2026-08-03. The page says the longitudinal HTOPS design was
used during 2025 and that the survey changed to a cross-sectional design in
March 2026. The July release must therefore remain isolated from every 2025
longitudinal file and from the March and May 2026 cross-sections.

The selected official artifacts are:

- CSV PUF package:
  <https://www2.census.gov/programs-surveys/demo/datasets/hhp/2026/topical/HTOPS_HPS_2607_CSV.zip>
- English questionnaire:
  <https://www2.census.gov/programs-surveys/demo/technical-documentation/hhp/HTOPS_2607_Questionnaire_ENGLISH.pdf>
- source and accuracy statement:
  <https://www2.census.gov/programs-surveys/demo/technical-documentation/hhp/HTOPS_2607_Source_and_Accuracy.pdf>
- user note:
  <https://www2.census.gov/programs-surveys/demo/technical-documentation/hhp/2607_HTOPS_Household_Pulse_User_Notes_10302026.pdf>
- quality measures:
  <https://www2.census.gov/programs-surveys/demo/tables/hhp/2026/2607/HTOPS_2607_Quality_Measures.xlsx>

HEAD observations at `2026-11-02`:

- CSV ZIP: 20,037,422 bytes, `application/zip`, last modified
  `2026-09-10T17:00:31Z`;
- questionnaire: 397,247 bytes, `application/pdf`, last modified
  `2026-09-24T13:02:14Z`;
- source and accuracy statement: 1,279,166 bytes, `application/pdf`, last
  modified `2026-09-24T12:47:12Z`;
- user note: 283,812 bytes, `application/pdf`, last modified
  `2026-10-30T16:00:27Z`; and
- quality measures: 12,763 bytes, Office Open XML workbook, last modified
  `2026-09-24T12:47:11Z`.

The publisher supplies no immutable release ID or checksum. The later user note
does not identify replacement ZIP bytes and must not be treated as a package
revision. Content evaluation must pin the exact archive hash, member inventory,
member hashes, and retrieval time, and must explain the user note's effect.

## Dictionary, weights, and variance

The PUF page states that each release includes a public-use file, a replicate-
weight file, and a data dictionary. It does not expose the July member names or
counts outside the ZIP. Their exact identity remains a content-evaluation fact,
not metadata that may be guessed.

The July evaluation must identify and validate:

- the final household/person weight field and every replicate-weight field;
- numeric type, missing/non-finite/zero/negative counts, and observed range;
- the number and naming sequence of replicate weights;
- the publisher's variance formula and scaling factors; and
- agreement between the dictionary, source-and-accuracy statement, and CSV.

Unweighted row counts are not population estimates. No standard error or
confidence interval may be published until the exact Census replicate-weight
procedure is implemented with an independently reviewed synthetic golden
fixture. Weights and replicate weights are release-specific and must never be
borrowed across waves.

## Topics, missingness, and special codes

The HTOPS overview identifies food and nutrition, transportation, employment,
and education among its topics. The selected Household Pulse component may also
contain housing, expenses, and demographic questions, but exact fields must be
derived from the July dictionary and questionnaire rather than from another
wave.

Content evaluation must separately aggregate:

- ordinary missing values;
- questionnaire skip or out-of-universe states;
- refusals and don't-know responses;
- edited or allocated values and any imputation flags; and
- valid substantive categories, including zero where zero is meaningful.

Special response codes must not be normalized into ordinary missingness or
silently interpreted as hardship. Schema, weight, replicate-weight, missing,
special-code, and imputation aggregates must be pinned and fail closed on
drift.

## Identifiers and sensitive/proxy fields

Any respondent, case, household, sample, or contact identifier is quarantined.
It may support isolated integrity checks only and must not enter features,
outputs, routine logs, or cross-source linkage. A cross-sectional release must
not be treated as a longitudinal panel merely because an identifier exists.

Sensitive and proxy-sensitive categories include race and ethnicity, sex or
gender, age, disability, household composition, education, employment, income,
housing tenure and costs, geography, food sufficiency, transportation access,
and hardship experiences. These fields may support aggregate coverage and
fairness audits with minimum-cell and disclosure controls; they may not be used
for individual production scoring.

Survey-reported inability to pay rent, mortgage, utilities, food, or other
expenses is a reported difficulty, not verified delinquency, default, or loan
performance. It must never be converted into a credit-default label.

## Rights, project disposition, and citation

The Census PUF page presents the files as public-use data. The Census citation
policy encourages reuse and requires users creating their own estimates to cite
the Census Bureau as the original source; analytical conclusions remain the
performing party's responsibility. The release page does not supply a file-
specific license or an affirmative statement about repository redistribution.

The project therefore applies the stricter disposition:

- storage: `external_only`;
- analytical ceiling: `quality_only`;
- redistribution: prohibited;
- raw or transformed row data in the repository: prohibited.

Official citation policy:
<https://www.census.gov/about/policies/citation.html>

Recommended project citation:

> U.S. Census Bureau. “HTOPS Household Pulse July 2026 Public Use File,”
> collected July 15–August 3, 2026. *Household Pulse Survey Public Use File
> (PUF)*. Accessed November 2, 2026.
> <https://www.census.gov/programs-surveys/household-pulse-survey/data/datasets.html>.

This is a project-formatted citation, not a publisher-issued release ID.

## Content-evaluation requirements

Before approval, implementation must:

- retrieve only the selected official July 2026 CSV ZIP and documentation;
- fix archive/member hashes, sizes, schema, rows, and columns;
- identify the dictionary and replicate-weight members from package contents;
- enforce July-only design identity and reject 2025, March, or May inputs;
- validate all weight, replicate-weight, missing, special-code, and imputation
  aggregates;
- quarantine every respondent/case/household identifier;
- document the October 30 user note's exact semantic effect;
- enforce `external_only`, `quality_only`, and no redistribution; and
- avoid committing any raw or transformed respondent rows.
