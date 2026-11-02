# UCI South German Credit

- Candidate ID: `uci-south-german-credit-2019`
- Priority: 7
- Review status: `superseded`
- Publisher: UCI Machine Learning Repository
- Original provenance: corrected South German credit representation; original
  collection context needs further review
- Publisher class: university repository
- Canonical page:
  <https://archive.ics.uci.edu/dataset/522/south+german+credit>
- DOI: <https://doi.org/10.24432/C5X89F>
- Repository release: donated 2019-11-28; exact package revision not pinned
- License: CC BY 4.0, linked by UCI:
  <https://creativecommons.org/licenses/by/4.0/legalcode>
- Redistribution: appears permitted with attribution, subject to package,
  provenance, and privacy confirmation
- Decision: none
- Trust tier: B pending original-provenance and privacy review

This record is superseded by the current official UCI 573 record,
[`uci-south-german-credit-2020`](uci-south-german-credit-2020.md). Its UCI 522
identity and DOI must not be used for the downloaded UCI 573 package.

UCI documents 1,000 cases, 700 good and 300 bad, with 20 predictor variables and
data from 1973–1975. It is a small cross-sectional credit-risk benchmark, not
cash-flow transactions, rent schedules, or utility bills. It cannot validate
the three signal-family adapters.

The historical German population, stratified sampling, encodings, age,
personal-status/sex field, and limited context create substantial fairness and
representativeness limits. No decision/index time and performance window have
been verified, so the class label does not yet make it `risk_eligible`.

Required evidence: official members/sizes/R documentation/hash, attribution,
original collection and label horizon, sampling, time semantics, and privacy
review. Any approval is limited to generic risk-metric mechanics, not modern
population or alternative-signal claims.

## Enablement plan

- Target: `repository` as the first directly included risk-metric benchmark,
  preserving CC BY 4.0 attribution and original limitations.
- Contact: UCI Machine Learning Repository dataset maintainers/support and the
  provenance contacts named by the official dataset documentation.
- Ask for: current package revision/member manifest, checksum or stable version
  identifier, original provenance citation, label definition/horizon, and any
  privacy/use caveats beyond CC BY 4.0.
- Next evidence: pin official downloadable members and documentation, review the
  license/attribution files, compute hashes only after retrieval approval, and
  decide whether missing time semantics restrict it to metric mechanics.
- Parallel work: structure-equivalent 1,000-row synthetic binary-risk fixture
  and generic risk adapter tests, clearly outside alternative-signal claims.
- Deliverables after approval: vendored small dataset if allowed, manifest,
  attribution notice, adapter, data card, binary outcome mapping, and AD-3 metric
  benchmark tests.
- Unacceptable condition: authoritative provenance or label meaning cannot be
  established sufficiently even for bounded benchmark use.
