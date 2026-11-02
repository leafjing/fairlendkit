# Federal Reserve SHED 2024 public-use data

- Candidate ID: `federal-reserve-shed-2024`
- Priority: 3
- Review status: `evidence_incomplete`
- Publisher: Board of Governors of the Federal Reserve System
- Publisher class: government
- Canonical page: <https://www.federalreserve.gov/consumerscommunities/shed_data.htm>
- Codebook:
  <https://www.federalreserve.gov/consumerscommunities/files/SHED_2024codebook.pdf>
- Official CSV package:
  <https://www.federalreserve.gov/consumerscommunities/files/SHED_public_use_data_2024_(CSV).zip>
- Exact release/version: 2024 survey; current data update dated 2026-02-09;
  publisher supplies no immutable release ID or checksum
- License/redistribution: no dataset-specific affirmative redistribution grant
  found; project disposition is `external_only`, `quality_only`, and
  `redistribution=prohibited`
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

SHED is household survey microdata with weights and responses about finances,
bills, credit, housing, and hardship. It can support coverage, representation,
and descriptive quality research. It is not bank transactions, rent ledgers,
utility bills, or observed loan performance. Reported inability to pay a bill
retains that survey meaning and is not converted to loan default.

Required content evidence: package members/hash, retrieved schema and row count,
weight and imputation aggregates, special-code handling, longitudinal-ID
containment, and outcome fitness. Default analytical disposition is
`quality_only`; this self-reported survey is not a loan-performance source.

## Enablement plan

- Target: `external_only` with pinned official ZIP verification; raw or
  transformed respondent rows must not enter the repository.
- Contact: SHED program/data-page contact and Board public website support,
  resolved from the canonical page rather than guessed email addresses.
- Ask for: data-use/redistribution statement, revision identifier, stable package
  checksum policy, and permitted treatment of longitudinal case IDs.
- Next evidence: enumerate the official ZIP members and page revision notes
  without retaining data, then obtain terms confirmation.
- Parallel work: synthetic weighted household survey fixture and codebook-driven
  mapping for bills, housing, credit access, hardship, and audit groups.
- Deliverables after approval: version verifier, survey adapter, data card,
  weighting tests, coverage/representation example, and no unsupported default
  outcome claim.
- Unacceptable condition: identifier/linkage restrictions incompatible with
  safe processing or terms that prohibit reproducible local analysis.

## Verified official metadata snapshot

Official page and HEAD metadata were rechecked 2026-11-02 without retrieving
the ZIP, CSV, or PDF bodies:

- current 2024 CSV ZIP: 3,787,684 bytes, last modified 2026-02-09;
- current 2024 codebook: 848,401 bytes, last modified 2026-02-09; and
- the canonical SHED page continues to expose both artifacts.

The page labels the codebook updated 2025-05-28 and the data updated 2026-02-09;
its update note says datasets and codebooks gained a new unique identifier. The
candidate therefore retains the observed 2026-02-09 HTTP metadata, but
`release_id` remains null. “2024” alone is not a sufficient version. The Board
linking-policy page is not affirmative dataset redistribution permission. The
metadata-only
[`federal-reserve-shed-2024-manifest.json`](federal-reserve-shed-2024-manifest.json)
therefore keeps member identity unverified pending content evaluation, while
the stricter project disposition prohibits redistribution.

The metadata findings, survey design, weighting, imputation, privacy boundary,
and citation are recorded in
[`../investigations/federal-reserve-shed-2024-metadata-2026-11-02.md`](../investigations/federal-reserve-shed-2024-metadata-2026-11-02.md).
