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
