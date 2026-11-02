# UCI South German Credit

- Candidate ID: `uci-south-german-credit-2019`
- Priority: 7
- Review status: `evidence_incomplete`
- Publisher: UCI Machine Learning Repository
- Original provenance: corrected South German credit representation; original
  collection context needs further review
- Publisher class: university repository
- Canonical page:
  <https://archive.ics.uci.edu/dataset/522/south+german+credit>
- DOI: <https://doi.org/10.24432/C5X89F>
- Repository release: the rendered page says donated 2019-11-28, while embedded
  official metadata reports `2019-11-29T00:00:00Z`; the one-day discrepancy is
  unresolved and `release_date` remains null in the manifest
- License: CC BY 4.0, linked by UCI:
  <https://creativecommons.org/licenses/by/4.0/legalcode>
- Redistribution: appears permitted with attribution, subject to package,
  provenance, and privacy confirmation
- Decision: none
- Trust tier: B pending original-provenance and privacy review

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

## Verified official metadata snapshot

Checked against the canonical UCI page on 2026-11-01 without downloading the
package:

- package URL:
  <https://archive.ics.uci.edu/static/public/522/south+german+credit.zip>;
- `SouthGermanCredit.asc`: 47,940 bytes;
- `read_SouthGermanCredit.R`: 7,550 bytes;
- `codetable.txt`: 3,154 bytes;
- total uncompressed size: 58,644 bytes;
- total compressed size: 13,130 bytes;
- official abstract: 1,000 cases, 700 good and 300 bad, 20 predictors, collected
  1973–1975, with bad credits heavily oversampled;
- target description: whether the credit contract was complied with (`good`) or
  not (`bad`); and
- official license presentation: CC BY 4.0 permits sharing and adaptation with
  attribution.

The metadata-only
[`uci-south-german-credit-2019-manifest.json`](uci-south-german-credit-2019-manifest.json)
pins these claims. Publisher checksums and repository SHA-256 values remain null
because data retrieval is not authorized by this documentation change.
The CC BY 4.0 presentation is affirmative license evidence, but manifest-level
and member-level redistribution remain `unverified` until admission closes the
package, provenance, and privacy checks.

Remaining admission work is narrower but material: resolve the release-date
discrepancy through UCI's official <https://archive.ics.uci.edu/contact> route,
confirm whether the archive has a stable revision identity/checksum, verify the
original collection/label horizon, and complete privacy plus benchmark-scope
review. Candidate status remains `evidence_incomplete`.

An explicitly unsent request is prepared at
[`../contact-drafts/uci-south-german-credit-request.md`](../contact-drafts/uci-south-german-credit-request.md).
It is a review artifact only and must not be sent without custice's explicit
authorization.

The independently reviewable AD-D1-UCI proposal is recorded at
[`../admission-proposals/uci-south-german-credit-2019.md`](../admission-proposals/uci-south-german-credit-2019.md).
It proposes a bounded one-time retrieval gate; it does not authorize retrieval,
populate hashes, or change this candidate's pending state.

## UCI-M1 response-metadata investigation

The first independently authorized retrieval attempt was consumed on
2026-11-02 and failed closed before body streaming because the normalized GET
response media type was not in the exact approved ZIP allowlist. Independent
review confirmed lifecycle `prepared -> started -> failed -> cleaned`, completed
cleanup, no quarantined bytes, a permanent single-use `.spent` marker, and no
admission or repository action. The candidate therefore remains
`evidence_incomplete` and cannot advance to byte-level Q3 review.

The metadata-only follow-up is recorded in
[`../investigations/uci-south-german-credit-response-metadata-2026-11-02.md`](../investigations/uci-south-german-credit-response-metadata-2026-11-02.md).
It shows that the package endpoint's HEAD response omits `Content-Type` and
`Content-Length`, including when sent the approved Harness `Accept` and
`User-Agent` headers. The failed GET audit did not persist raw response headers,
so the exact GET `Content-Type` cannot be reconstructed after the fact. HEAD and
GET semantics must not be assumed identical.

No second retrieval is proposed from this evidence. A future attempt requires a
new reviewed Harness version that safely records response metadata before media-
type rejection, or affirmative publisher evidence about the package delivery
headers; then a new contract, authorization, run ID, and independent approval.
The existing media-type allowlist is not widened and the consumed Run ID is
never reused.

## UCI-M2 successor-endpoint evidence

Custice subsequently supplied UCI dataset ID 573, DOI `10.24432/C5QG88`, and
package `south+german+credit+update.zip`. The metadata-only HEAD evidence is
recorded in
[`../investigations/uci-south-german-credit-successor-endpoint-2026-11-02.md`](../investigations/uci-south-german-credit-successor-endpoint-2026-11-02.md).
The DOI resolves to UCI's dataset 573 update record, so this is a materially new
endpoint rather than permission to retry the spent dataset-522 Run.

No GET or body read was performed. The dataset-573 package HEAD is reachable but
again omits media type, length, validators, and checksum. The existing manifest
therefore remains pinned to dataset 522 and `evidence_incomplete` until an
independent review decides whether 573 is a successor release and approves a
new single-use retrieval contract and Run ID.

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
