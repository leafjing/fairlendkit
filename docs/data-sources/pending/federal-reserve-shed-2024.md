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
- Exact release/version: 2024 SHED public-use CSV; codebook last updated May 28,
  2025; package identity and aggregate evidence pinned in
  [the technical evaluation](../federal-reserve-shed-2024-evaluation.md)
- License/redistribution: public download verified, but no dataset-specific
  redistribution grant located; project redistribution prohibited
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

SHED is household survey microdata with weights and responses about finances,
bills, credit, housing, and hardship. It can support coverage, representation,
and descriptive quality research. It is not bank transactions, rent ledgers,
utility bills, or observed loan performance. Reported inability to pay a bill
retains that survey meaning and is not converted to loan default.

Technical content evidence is complete. Admission remains incomplete pending a
verified redistribution/rights basis. Maximum analytical disposition is
`external_only + quality_only`; no mature credit-performance outcome exists.

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
