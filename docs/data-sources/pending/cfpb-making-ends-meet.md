# CFPB Making Ends Meet Survey public-use files

- Candidate ID: `cfpb-making-ends-meet`
- Priority: 2
- Review status: `evidence_incomplete`
- Publisher: U.S. Consumer Financial Protection Bureau
- Publisher class: government
- Official user guide:
  <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>
- Historical data paths under `/data-research/making-ends-meet-survey-data/`
  currently redirect to the CFPB data-research root; no stable package URL is
  pinned
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
