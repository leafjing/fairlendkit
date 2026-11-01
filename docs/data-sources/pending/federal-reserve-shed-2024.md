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
- Exact release/version: 2024 SHED; package revision still to be pinned
- License/redistribution: package-specific terms not yet verified
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

SHED is household survey microdata with weights and responses about finances,
bills, credit, housing, and hardship. It can support coverage, representation,
and descriptive quality research. It is not bank transactions, rent ledgers,
utility bills, or observed loan performance. Reported inability to pay a bill
retains that survey meaning and is not converted to loan default.

Required evidence: package members/sizes/revision/hash, public-use and
redistribution terms, field matrix, survey reference periods, longitudinal ID
privacy review, and outcome fitness. Default analytical disposition is
`quality_only` unless later evidence establishes a mature outcome window.

## Enablement plan

- Target: `repository` if Federal Reserve terms affirm redistribution;
  otherwise `external_only` with pinned official ZIP verification.
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

Official HEAD metadata checked 2026-11-01 without retrieving bodies:

- current 2024 CSV ZIP: 3,787,684 bytes, last modified 2026-02-09;
- current 2024 codebook: 848,401 bytes, last modified 2026-02-09; and
- the canonical SHED page continues to expose both artifacts.

Because a 2024 survey artifact was updated in 2026, the manifest identifies this
snapshot as `shed-2024-public-use-current-2026-02-09`; “2024” alone is not a
sufficient version. The Board linking-policy page only resolves third-party
linked-content restrictions and is not yet affirmative dataset redistribution
permission. The metadata-only
[`federal-reserve-shed-2024-manifest.json`](federal-reserve-shed-2024-manifest.json)
therefore remains `redistribution=unverified` and defaults members to
`external_only` pending confirmation.
