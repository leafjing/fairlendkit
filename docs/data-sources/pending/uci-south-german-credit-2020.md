# UCI South German Credit (UCI 573)

- Candidate ID: `uci-south-german-credit-2020`
- Review status: `evidence_incomplete`
- Reviewer and review date: pending independent review
- Publisher/legal entity: UCI Machine Learning Repository
- Publisher class: university
- Canonical landing page:
  <https://archive.ics.uci.edu/dataset/573/south+german+credit+update>
- DOI: <https://doi.org/10.24432/C5QG88>
- Exact release/version and publication date: UCI dataset 573, 2020; official
  metadata reports last update 2024-03-16 but supplies no immutable package
  revision
- Retrieval date: 2026-11-02
- Documentation/data-dictionary URL: canonical landing page and the downloaded
  `codetable.txt` plus `read_SouthGermanCredit.R`
- File manifest supplied by publisher: no checksum manifest was found
- Publisher-supplied checksums: none found

## Authority and provenance

- Original publisher confirmed: yes for the repository package; the package is
  UCI's corrected representation of earlier German credit data
- Hosting site is original or mirror: original UCI repository host
- Collection method and stated purpose: stratified sample of actual credits
  from 1973–1975; 300 bad and 700 good credits, with bad credits heavily
  oversampled; historical benchmark use
- Chain of custody/version history: UCI explains that this representation
  corrects coding errors in the older Statlog/Open Data LMU representations;
  the current UCI package lacks an immutable revision identifier
- Stable citation: *South German Credit* [Dataset]. (2020). UCI Machine
  Learning Repository. <https://doi.org/10.24432/C5QG88>
- Authenticity concerns: exact upstream package revision is not pinned by UCI
- Evidence links and archived citation dates: landing page, DOI, and official
  ZIP inspected 2026-11-02

## License and terms

- License name and exact version: Creative Commons Attribution 4.0
  International (`CC BY 4.0`)
- License URL and quoted redistribution clause:
  <https://creativecommons.org/licenses/by/4.0/legalcode>; the UCI page states
  that sharing and adaptation are allowed for any purpose with attribution
- Research/analysis permitted: yes
- Modification/derivatives permitted: yes, with attribution and change notice
- Redistribution permitted: yes, with attribution and license notice
- Automated download permitted: yes for the supplied direct HTTPS package in
  the explicitly authorized one-attempt retrieval; no broader crawler claim
- Attribution/share-alike/noncommercial requirements: attribution and change
  notice; no share-alike or noncommercial restriction
- Separate website/API terms: none identified that narrow the dataset license
- Personal-data or jurisdiction restrictions: none stated by UCI
- License reviewer and rationale: pending independent review

## Data and signal coverage

- Unit of observation: one historical credit contract/case
- Population and geography: stratified historical German credit sample,
  1973–1975
- Collection dates: 1973–1975
- Cash-flow fields and semantics: none
- Rent fields and semantics: housing category only; no rent schedule or payment
- Utility fields and semantics: none
- Event time, observation time, and revision history available: no
- Provider/source/version fields available: source is package-level only
- Amount, currency, obligation, due-date, payment, adjustment, and reversal
  fields: transformed credit amount and duration only; actual amount transform
  is unknown, and due/payment/adjustment/reversal events are absent
- Data dictionary completeness: all 21 columns documented, but original amount
  transformation and temporal outcome details remain unavailable

## Outcome and time-window fitness

- Credit outcome definition: `kredit=0` means the credit contract was not
  complied with (bad); `kredit=1` means complied with (good)
- Outcome source and maturity rule: outcome source, performance horizon, and
  maturity rule are not documented sufficiently
- Feature observation window: unavailable
- Decision/index time: unavailable
- Performance window: unavailable
- Censoring and follow-up: unavailable
- Pre/post-decision separation possible: no
- Risk-analysis use: `quality_only`
- Leakage concerns: feature/decision/outcome ordering cannot be established

## Privacy and security

- Direct identifiers present: none found in the 21-column schema
- Quasi-identifiers and high-cardinality fields: age and transformed credit
  amount; combinations can create small historical cells
- Sensitive/protected attributes: age, `personal_status_sex`, and
  `foreign_worker`; the combined sex/status encoding cannot recover sex cleanly
- Free text, exact location, account/meter/device identifiers: none
- Consent/permission basis stated by publisher: not stated
- Reidentification and linkage risk: no direct identifiers, but row-level
  public redistribution still requires attribution and a data-card warning
- Minimum-cell or access restrictions: none stated by UCI
- Terms permit automated analysis: yes
- Safe local handling requirements: do not publish row examples; preserve the
  original schema and suppress sparse analytical releases under FairLendKit
- Repository-safe projection possible: yes, subject to independent approval

## Representation and bias

- Sampling/recruitment mechanism: stratified sample with bad credits heavily
  oversampled
- Traditional-credit-coverage evidence: historical bank credit cases only
- Underrepresented or excluded populations: not documented
- Provider, geography, device, account, tenancy, and service-coverage bias:
  single historical setting; no provider or geography strata are supplied
- Missing-not-at-random concerns: the package has no blank cells, but selection
  into the sample and class oversampling are material
- Known measurement/label bias: coded historical categories, mixed
  sex/marital-status field, unknown amount transformation, undefined outcome
  horizon
- Generalizability limits: not representative of modern U.S. applicants,
  production lending, or alternative-data populations

## Reproducibility

- Preflight Run ID: `UCI573-20261102T0408Z-01`; permanently retired because
  it did not use the controlled Harness audit lifecycle. Its observed hashes
  and content findings are non-admission evidence only.
- Formal Harness Run ID: `uci573-formal-20261102t041415z-fe6d427`; permanently
  spent after the official response omitted an authorized ZIP media type. Its
  state sequence was `prepared`, `started`, `failed`, `cleaned`; cleanup
  completed and no source bytes remain. Authorization SHA-256 is
  `e7a190821ba0e6f8252bc63fc180ca8d3c6dffa48f4023e897dfec33e0a607e5`,
  audit SHA-256 is
  `8c497a2bef7076694b29bb24da75f3f8c0eb8d524e7a2f900fdc427fd495950a`,
  and the permanent `.spent` SHA-256 is
  `c60a409ccef2944d1b9440288fdca537e93febf40de548d5fa13a37854b821fa`.
- Expected filenames and byte sizes: archive 13,130 bytes; `codetable.txt`
  3,154; `read_SouthGermanCredit.R` 7,550; `SouthGermanCredit.asc` 47,940
- Repository-computed SHA-256 after authorized retrieval: unavailable; the
  formal Harness Run failed before retaining an archive, so all companion
  manifest `repository_sha256` values remain `null`
- Non-admission preflight observations: three UTF-8, unencrypted regular
  members; 58,644 total uncompressed bytes; 1,000 data rows, 21 columns, fixed
  row width, zero blank cells, zero exact duplicate rows, and numeric values
  only. These observations support content assessment but not promotion.
- Label check: 300 `bad` (`0`) and 700 `good` (`1`)
- Deterministic preparation steps: whitespace-delimited header plus 1,000 rows;
  apply the official R/code-table mappings without changing raw categories
- Required software/environment: ZIP reader and strict UTF-8/tabular parser
- Upstream stability and expected update cadence: not stated
- Offline fixture strategy: structure-equivalent synthetic binary-risk fixture
  for tests; no real row is committed as a fixture

## Coverage matrix

| Capability | Cash flow | Rent | Utilities |
|---|---|---|---|
| Explicit signal identity | no | no | no |
| Event/period time | no | no | no |
| Observation/availability time | no | no | no |
| Provider and source version | partial: package only | partial: package only | partial: package only |
| Amount and currency | partial: transformed credit amount | no | no |
| Obligation and due date | partial: credit duration only | no | no |
| Payment and partial payment | no | no | no |
| Adjustment/revision/reversal | no | no | no |
| Explicit reporting gap | no | no | no |
| Outcome and maturity | partial: binary label, no horizon | no | no |
| Decision/index time | no | no | no |
| Protected-group audit fields | partial: ambiguous historical proxies | partial | partial |
| Traditional-credit-coverage evidence | yes | no | no |

## Decision

- Decision: pending independent review; proposed `repository` for a bounded
  generic metric benchmark only
- Trust tier: C, research-limited
- Approved analytical uses: none until review; proposed use is parser and
  generic binary risk-metric mechanics under `quality_only`
- Prohibited uses: alternative-signal adapter validation, modern U.S.
  representativeness, production decision claims, leakage-free/risk-eligible
  claims, causal discrimination conclusions, and recovery of sex from the
  mixed `personal_status_sex` field
- Required attribution: dataset title, UCI Machine Learning Repository, 2020,
  DOI `10.24432/C5QG88`, and CC BY 4.0 notice
- Required controls and limitations: pin hashes, retain category semantics,
  document class oversampling and historical scope, and apply disclosure
  controls to outputs
- Decision evidence and signatures: content assessment complete; formal
  retrieval failed and admission evidence remains incomplete

## Enablement plan

- Target disposition: `repository`
- Value unlocked for FairLendKit: a small, reproducible input for bounded
  binary-metric and parser verification
- Fixable conditions before admission: independent license/privacy/semantic
  review and explicit repository-byte promotion approval
- Publisher/rightsholder contact or official support route: UCI dataset page
- Contact question and evidence requested: immutable package revision/checksum
  and fuller outcome horizon/provenance
- Next evidence-gathering action, owner, and due state: independent reviewer
  checks this record and manifest
- Canonical-schema mapping to implement: separate benchmark adapter; do not map
  rows into cash-flow, rent, or utility signal records
- Synthetic fixture that can proceed before data access: 1,000-row
  structure-equivalent binary fixture
- Adapter/downloader/data-card deliverables after approval: deterministic
  parser, attribution notice, data card, hash verification, and metric tests
- Condition that would make the source genuinely unacceptable: license or
  provenance contradiction, integrity mismatch, or intended use broader than
  this bounded quality-only benchmark
