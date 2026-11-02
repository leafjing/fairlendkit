# RECS-M1 — EIA 2020 RECS public microdata v7 metadata evidence

Status: metadata-only investigation; no CSV, XLSX, PDF, SAS archive, or other
data/document file body was downloaded or read. No admission, promotion,
repository inclusion, or redistribution approval is implied.

- Candidate: `eia-recs-2020-v7`
- Observation time: `2026-11-02T04:16:16Z` and immediately following
- Publisher: U.S. Energy Information Administration (EIA)
- Canonical page:
  <https://www.eia.gov/consumption/residential/data/2020/index.php?view=microdata>
- Reuse page: <https://www.eia.gov/about/copyrights_reuse.php>
- Method: HEAD for fixed file endpoints; GET only for the two public HTML pages

## Version and publication evidence

The official microdata page identifies the current CSV and codebook paths as
`recs2020_public_v7.csv` and
`RECS 2020 Codebook for Public File - v7.xlsx`. Its release history states:

- July 2022: first microdata version with preliminary household
  characteristics;
- June 2023: final consumption, expenditure, and end-use estimates; and
- January 2024: update to the final file adding nine electricity variables.

The page's table labels the v7 materials `January 2024`. This establishes the
human-readable candidate version `2020 RECS public microdata v7`, but not an
immutable publisher release ID or publisher checksum. No DOI or other
persistent identifier is presented for this file release.

## Population, sample design, weights, and geography

The official page describes RECS as a national sample survey of housing units
occupied as primary residences and their households. It reports nearly 18,500
sampled households, statistically selected to represent 123.5 million occupied
primary-residence housing units. This is a household/housing-unit survey, not a
census, transaction ledger, utility-account population, or sample of credit
applicants.

The previously inspected official v7 codebook metadata identifies `DOEID` as a
respondent identifier, `NWEIGHT` as the final analysis weight, and `NWEIGHT1`
through `NWEIGHT60` as final analysis replicate weights. Unweighted row counts
must never be presented as population estimates, and uncertainty must follow
the official replicate-weight method rather than ordinary unweighted formulas.

This metadata-only pass does not establish an exact allowable public-file
geography vocabulary. The landing page links separate published state tables,
but that does not prove the row-level microdata contains state or finer
geography. Until the codebook and CSV schema are jointly verified after an
authorized retrieval, no state, county, ZIP-code, address, or tract field may be
claimed or derived. Any available region/division/climate/urbanicity field must
be treated as contextual or proxy-sensitive, not precise residence location.

## Sensitive fields and proxy-discrimination boundary

The official description and existing codebook evidence cover household and
housing characteristics, energy sources and equipment, consumption and
expenditures, billing coverage, hardship, imputation, demographics, and survey
weights. These categories can expose or proxy income and socioeconomic status,
household composition, tenure/housing conditions, age or life stage,
race/ethnicity where present, disability or health-related energy needs where
present, geography/climate, and utility access.

`DOEID` is a respondent identifier and must be removed from reports, logs,
exceptions, fixtures, joins, and exported derived records. Rare combinations of
demographics, housing, geography, equipment, fuel, hardship, and expenditure
fields can create singling-out or linkage risk even without names or addresses.

No RECS field may be used to score an individual, infer creditworthiness, train
or validate an underwriting outcome, or treat energy burden, disconnection
notices, inability to afford service, fuel choice, missingness, or imputation as
delinquency/default. Group differences may be reported only as descriptive,
weighted, uncertainty-qualified `quality_only` evidence with support,
missingness, imputation, geography, and proxy limitations disclosed. They are
not findings of unlawful discrimination or causal effects.

## Fixed endpoint HEAD evidence

Each exact HTTPS endpoint returned `200`, no redirect, and successful TLS
verification:

- CSV `csv/recs2020_public_v7.csv`: `Content-Length: 56044261`,
  `Content-Type: application/octet-stream`, `Last-Modified: Mon, 22 Jan 2024
  12:48:28 GMT`, `ETag: "0f6b84b314dda1:0"`;
- codebook `xls/RECS 2020 Codebook for Public File - v7.xlsx`:
  `Content-Length: 58382`, OOXML spreadsheet media type, `Last-Modified: Mon,
  22 Jan 2024 16:58:41 GMT`, `ETag: "80f62a40544dda1:0"`; and
- method guide `pdf/microdata-guide.pdf`: `Content-Length: 581524`,
  `Content-Type: application/pdf`, `Last-Modified: Wed, 07 Jun 2023 14:19:53
  GMT`, `ETag: "80ca70204b99d91:0"`.

All three advertise byte ranges and HSTS. The CSV's generic
`application/octet-stream` is an observed official response type and must be
explicitly pinned if a future controlled retrieval is authorized; it must not
be generalized to other URLs.

The two HTML pages returned Akamai `503` to default HEAD, but `200 text/html`
to a browser-style GET with no redirect. This method difference affects page
availability checks only and is not evidence about the fixed file endpoints.

## Reuse and attribution evidence

EIA's Copyrights and Reuse page states that U.S. government publications are
public domain and that users may use and/or distribute EIA data, files,
databases, reports, graphs, charts, and other information products. It requests
an acknowledgment containing the source and publication date. It separately
warns that third-party-contributed or licensed material may remain protected
and require permission beyond fair use.

Accordingly, EIA-originated RECS files have a credible repository-use and
redistribution path, but manifest and member scope remain `unverified` until a
controlled retrieval confirms exact files, notices, and absence or handling of
third-party material. A future attribution should identify EIA, the January
2024 v7 update, the canonical page, retrieval date, and exact byte hashes.

EIA does not present a formal DOI citation for this release. The proposed
project attribution, subject to post-retrieval review, is: `Source: U.S. Energy
Information Administration, Residential Energy Consumption Survey (RECS), 2020
public microdata v7 (January 2024),
https://www.eia.gov/consumption/residential/data/2020/index.php?view=microdata,
accessed 2026-11-02.` This is a project-formatted acknowledgment implementing
EIA's source/date guidance, not a publisher-issued bibliographic record.

## Fitness and next gate

RECS is suitable for continued evaluation as `quality_only` evidence for
utility coverage, energy expenditure/consumption quality, imputation,
weighting, representation, and survey-based hardship analysis. It is not a
payment ledger or credit-outcome dataset and must not be used as evidence of
delinquency, default, underwriting performance, or FairLendKit's three
alternative-signal adapters.

Before any retrieval, a reviewed authorization must pin the three exact URLs,
observed sizes and media types, conservative limits, a new single-use Run ID,
repository-external isolation, audit lifecycle, `.spent` behavior, and
fail-closed cleanup. Retrieval would still not authorize admission or
promotion. Row-level CSV schema, null tokens, respondent identifier handling,
weights, replicate weights, imputation flags, hashes, notices, and third-party
content remain Q3 review items.
