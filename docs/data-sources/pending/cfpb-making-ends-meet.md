# CFPB Making Ends Meet Survey public-use files

- Candidate ID: `cfpb-making-ends-meet`
- Priority: 2
- Review status: `evidence_incomplete`
- Publisher: U.S. Consumer Financial Protection Bureau
- Publisher class: government
- Official user guide:
  <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>
- The current CFPB Public Data Inventory still lists Making Ends Meet as raw,
  one-time data, while the public-data page redirects to the CFPB data-research
  root; official Sample 1/3/4/5/6 archives were nevertheless recovered from
  `files.consumerfinance.gov` and evaluated at `2026-11-02T05:05:26Z`
- Exact evaluated release set: official Samples 1, 3, 4, 5, and 6 plus the July
  2025 user guide; Sample 2 is intentionally excluded from the public release
- License/redistribution: access is conditioned on CFPB's MEM Terms and
  Conditions; project disposition is independently fixed to `external_only`
  with `redistribution=prohibited`
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

The guide documents survey samples, weights, survey variables, and
credit-derived variables. It is relevant to financial well-being, bill payment,
liquidity, hardship, and limited-credit context. It is not a transaction ledger
and must not be reshaped into fictitious cash-flow events. Self-reported
difficulty making ends meet is not loan default.

Required evidence: one exact official sample/wave and package, codebook,
questionnaire, file manifest, public-use agreement, redistribution/automated-
access terms, survey-to-credit-record time alignment, privacy restrictions,
hashes, and an approved `quality_only` or `risk_eligible` outcome mapping.

The latest metadata investigation is recorded in
[`../investigations/cfpb-making-ends-meet-metadata-2026-11-02.md`](../investigations/cfpb-making-ends-meet-metadata-2026-11-02.md).
It identifies Sample 6 Wave 1 as the latest guide-defined wave. Subsequent
official-file evaluation recovered Samples 1/3/4/5/6 from CFPB's file host.
Exact URLs, filenames, terms identity, byte sizes, and hashes must be pinned by
the superseding implementation evidence before this pending record closes.

Sample 6 has 2,630 responses and intentionally oversamples several credit,
income-area, and race/ethnicity-area proxy groups. Its online-only questions use
`_online` weights; other questions use `_paper` weights. These strata and
weights require explicit representation/proxy reporting and cannot be used as
individual risk labels.

## Enablement plan

- Target: `repository` for a redistribution-authorized small PUF; otherwise
  `external_only` with user-mediated official download and local verification.
- Contact: CFPB Making Ends Meet/Public Data Inventory owner or CFPB research-
  data support through the official agency contact route.
- Ask for: current public-data URL, sample/version history, public-use agreement,
  redistribution/automation terms, and survey-credit linkage timing guidance.
- Next evidence: identify one sample from the official user guide, recover its
  official package page, and capture the exact terms before touching bytes.
- Parallel work: synthetic survey/credit-derived fixture, questionnaire-to-
  canonical coverage mapping, weights and missing-state adapter tests.
- Deliverables after approval: manifest, wave adapter, data card, quality and
  limited-file coverage example; risk use only if temporal outcome review passes.
- Unacceptable condition: terms prohibit the intended automated research or
  linked credit-derived fields cannot be handled under the privacy boundary.

## Verified official metadata snapshot

Checked 2026-11-01 without retrieving a data package:

- the official Public Data Inventory lists “Making Ends Meet Survey,” describes
  it as a series of general financial surveys, and classifies it as raw,
  one-time data;
- the inventory's program link and the formerly indexed `/public-data/` route
  redirect to the generic CFPB data-research page rather than a package page;
- the official public-use-file user guide remains directly accessible at the
  CFPB file host; HEAD metadata reports 261,183 bytes and last modification on
  2026-03-17; and
- no current official package URL, publisher release identity, file/member
  inventory, checksum, or download terms were located.

The metadata-only
[`cfpb-making-ends-meet-manifest.json`](cfpb-making-ends-meet-manifest.json)
therefore pins only the official inventory and user guide. It uses
`release_id=null`, `package_url=null`, `redistribution=unverified`, and file
scope `unverified`. Candidate status remains `evidence_incomplete`; the guide is
evidence, not authorization to reconstruct, download, or redistribute a sample.

Samples 1/3/4/5/6 have been technically evaluated from official CFPB archives,
but remain `external_only` and non-redistributable under the project's stricter
disposition. Survey hardship is never a default label, and credit-derived
variables cannot become `risk_eligible` without explicit time alignment,
outcome semantics, maturity, privacy, and censoring review.

An unsent official inquiry is prepared at
[`cfpb-making-ends-meet-request.md`](../contact-drafts/cfpb-making-ends-meet-request.md).
It is a draft only and must not be sent without explicit authorization from
custice. Preparing the draft does not change the candidate or admission state.
