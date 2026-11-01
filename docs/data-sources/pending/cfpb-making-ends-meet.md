# CFPB Making Ends Meet Survey public-use files

- Candidate ID: `cfpb-making-ends-meet`
- Priority: 2
- Review status: `evidence_incomplete`
- Publisher: U.S. Consumer Financial Protection Bureau
- Publisher class: government
- Official user guide:
  <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>
- The current CFPB Public Data Inventory still lists Making Ends Meet as raw,
  one-time data, but its Making Ends Meet link and historical public-data path
  redirect to the CFPB data-research root; no stable package URL is pinned
- Exact release/version: sample-specific public-use files, not yet selected
- License/redistribution: per-download public-use terms not yet captured
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

No sample is selected until CFPB restores or identifies an official package
page with sample identity and terms. Survey hardship is never a default label,
and credit-derived variables cannot become `risk_eligible` without explicit
time alignment, outcome semantics, maturity, privacy, and censoring review.
