# Census HTOPS / Household Pulse Survey

- Candidate ID: `census-htops-hps`
- Priority: 4
- Review status: `evidence_incomplete`
- Publisher: U.S. Census Bureau
- Publisher class: government
- HTOPS overview: <https://www.census.gov/programs-surveys/htops.html>
- Official data page linked there:
  <https://www.census.gov/programs-surveys/household-pulse-survey/data.html>
- Selected release: latest available July 2026 cross-sectional PUF, collected
  2026-07-15 through 2026-08-03; no immutable release ID or checksum published
- Rights/disposition: Census public-use and citation guidance supports analysis,
  but no file-specific redistribution grant was found; project use is
  `external_only`, `quality_only`, and redistribution prohibited
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

HTOPS succeeds/extends the experimental Household Pulse Survey. Topics may
cover housing payments, energy insecurity, expenses, hardship, demographics,
and weights. These are survey responses, not consumer transaction, rent-ledger,
or utility-account histories. HTOPS and HPS waves must not be silently pooled;
housing or energy difficulty is not a credit-default label.

Required content evidence: archive/member hashes and shape, dictionary and
replicate-weight identity, questionnaire/source-accuracy/user-note alignment,
weight and special-code aggregates, identifier containment, and field fitness.
The disposition remains `quality_only`; survey hardship is not credit default.

## Enablement plan

- Target: `external_only` with a July-wave-pinned Census download workflow; raw
  and transformed respondent rows must not enter the repository.
- Contact: Census HTOPS/HPS program office and official data-user support.
- Ask for: recommended current wave, revision/version identity, public-use and
  redistribution terms, archive stability, and questionnaire comparability.
- Next evidence: select one wave with rent or energy-insecurity fields and pin
  its package, codebook, questionnaire, weights, and technical note as one unit.
- Parallel work: synthetic wave fixture plus adapter enforcing survey identity,
  reference periods, weights, missing codes, and prohibition on silent pooling.
- Deliverables after approval: wave-specific manifest/adapter/data card and a
  quality/coverage example; later waves enter as separate manifests.
- Unacceptable condition: no stable wave archive or disclosure terms prevent
  safe reproducible use.

## Verified official metadata snapshot

The official PUF page states that every release includes a PUF, replicate-weight
file, and data dictionary. It also distinguishes 2025 longitudinal HTOPS from
the cross-sectional design beginning in March 2026. The July 2026 collection is
therefore a distinct cross-sectional release and must not be pooled with 2025.

Official page and HEAD metadata checked 2026-11-01 without retrieving bodies:

- CSV ZIP: 20,037,422 bytes, last modified 2026-09-10;
- English questionnaire: 397,247 bytes, last modified 2026-09-24;
- source and accuracy statement: 1,279,166 bytes, last modified 2026-09-24;
- quality measures workbook: 12,763 bytes, last modified 2026-09-24; and
- July user note dated 2026-10-30: 283,812 bytes.

The metadata-only
[`census-htops-hps-manifest.json`](census-htops-hps-manifest.json) pins these
artifacts with `release_id=null`, `redistribution=unverified`, and file scope
`unverified`. The ZIP member names, dictionary and replicate-weight placement,
checksums, license/terms, and revision identity remain unresolved. Candidate
status stays `evidence_incomplete`; no artifact is approved for download.

The official 2026 topical directory was also checked on 2026-11-01. It exposes
the March, May, and July SAS/CSV ZIPs, but no standalone July dictionary or
replicate-weight artifact. The release page says those components are included
with each release, while neither page publishes the July ZIP member listing.
Consequently, their exact member names, paths, formats, and placement cannot be
verified without inspecting package content, which remains prohibited.

The official user note resolves its relationship to the ZIP. The October 30
`Health1`/`Housing3` and October 7 `Transportation3` corrections affect
published tables only; both explicitly state that the underlying PUF is not
affected. The September 10 notice separately records July race/ethnicity
variable changes caused by questionnaire changes and disclosure-avoidance
recoding. Those September fields and recodes must be fixed in schema/content
validation, while the October table corrections must not be misrepresented as
new package versions. The remaining content evidence is the July member
manifest, dictionary and replicate-weight locations, stable byte identity, and
field/weight/special-code aggregates.

Any eventual use defaults to `quality_only`. Survey-reported rent, mortgage,
energy, or expense difficulty is not a transaction history or credit outcome.
Weights and replicate weights must remain wave-specific, and no uncertainty
estimate may be published before the official variance procedure receives an
independent calculation contract and golden fixture.

The refreshed source, rights, weight, special-code, privacy, and citation review
is recorded in
[`../investigations/census-htops-july-2026-metadata-2026-11-02.md`](../investigations/census-htops-july-2026-metadata-2026-11-02.md).
