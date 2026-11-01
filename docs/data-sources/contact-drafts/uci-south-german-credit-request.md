# UNSENT draft: UCI South German Credit metadata request

Status: draft only. Do not send without explicit authorization from custice.

Intended recipient: UCI Machine Learning Repository support through the
official contact route at <https://archive.ics.uci.edu/contact>.

Suggested subject: South German Credit dataset version and provenance metadata

## Message draft

Hello UCI Machine Learning Repository team,

We are documenting a reproducible, bounded benchmark use of the South German
Credit dataset, DOI `10.24432/C5X89F`, and would appreciate clarification of a
few metadata points. We have not redistributed or incorporated the package into
our repository.

1. The rendered dataset page reports a donation date of 2019-11-28, while the
   page's repository metadata reports `2019-11-29T00:00:00Z`. Which date should
   be treated as the authoritative release/donation date?
2. Does the current ZIP have a stable package revision identifier, version
   number, publisher checksum, or member manifest? If the package can change in
   place, is there an official revision history?
3. Can you confirm the authoritative original source/citation and the exact
   semantics of the `good` and `bad` target values, including the observation
   or performance horizon and when the outcome was determined?
4. Does the repository have additional documentation for the 1973–1975 sample,
   sampling/oversampling procedure, decision or index time, and the provenance
   of the personal-status/sex and age fields?
5. Beyond the displayed CC BY 4.0 license, are there privacy, re-identification,
   attribution, automated-analysis, or redistribution restrictions that apply
   to the archive or any member?

For reference, the package metadata currently visible to us lists
`SouthGermanCredit.asc`, `read_SouthGermanCredit.R`, and `codetable.txt`, with a
total compressed size of 13,130 bytes. We will keep the candidate unavailable
until the version, provenance, label, and privacy review is complete.

Thank you.

## Send gate and response handling

- Sending requires a separate, explicit instruction from custice.
- Before sending, re-check the official contact URL and remove no questions
  without recording why.
- Store no personal respondent data or unpublished attachment in the repo.
- Record any reply as cited evidence; do not convert a non-answer into approval.
- A reply about licensing does not by itself establish label maturity, temporal
  fitness, privacy safety, or modern-population representativeness.
