# UNSENT draft: UCI South German Credit metadata request

Status: draft only. Do not send without explicit authorization from custice.

Intended recipient: UCI Machine Learning Repository support through the
official contact route at <https://archive.ics.uci.edu/contact>.

Suggested subject: South German Credit package response headers, version, and provenance metadata

## Message draft

Hello UCI Machine Learning Repository team,

We are documenting a reproducible, bounded benchmark use of the South German
Credit dataset, DOI `10.24432/C5X89F`, and would appreciate clarification of a
few metadata points. We have not redistributed or incorporated the package into
our repository.

During one authorized, controlled request to the official package URL, our
client stopped before retaining or processing any response body because the
normalized response media type did not match its reviewed ZIP allowlist. The
failed run was not retried and retained no package bytes. Separate metadata-only
`HEAD` requests to the same official URL returned HTTP 200 without a redirect,
but did not include `Content-Type` or `Content-Length`; this does not establish
which headers a `GET` response would return.

1. For a current `GET` request to the official package URL, what status code,
   redirect chain, `Content-Type`, `Content-Length`, and `Content-Disposition`
   should a client expect? Can request method or headers cause these values to
   differ?
2. Is the omission of `Content-Type` and `Content-Length` from `HEAD` responses
   intentional, and is there a recommended metadata-only method for verifying
   the package before a bounded download?
3. The rendered dataset page reports a donation date of 2019-11-28, while the
   page's repository metadata reports `2019-11-29T00:00:00Z`. Which date should
   be treated as the authoritative release/donation date?
4. What is the current authoritative package revision or version, release date,
   and publisher-issued checksum (including algorithm and value)? Is the object
   at the official package URL immutable, and, if it can change in place, is
   there an official revision history?
5. Can you confirm the authoritative ZIP member names and exact uncompressed
   sizes? Is there a publisher member manifest or per-member checksum, and may
   future revisions add, remove, or replace members or change the container or
   compression policy?
6. Can you confirm the authoritative original source/citation and the exact
   semantics of the `good` and `bad` target values, including the observation
   or performance horizon and when the outcome was determined?
7. Does the repository have additional documentation for the 1973–1975 sample,
   sampling/oversampling procedure, decision or index time, and the provenance
   of the personal-status/sex and age fields?
8. Beyond the displayed CC BY 4.0 license, are there privacy, re-identification,
   attribution, automated-analysis, or redistribution restrictions that apply
   to the archive or any member?

For reference, the package metadata currently visible to us lists
`SouthGermanCredit.asc`, `read_SouthGermanCredit.R`, and `codetable.txt`, with a
total compressed size of 13,130 bytes. We will keep the candidate unavailable
until the response behavior, version, provenance, label, and privacy review is
complete. A reply would be treated as evidence for a new independent review; it
would not itself authorize another download, data admission, repository
promotion, or redistribution.

Thank you.

## Send gate and response handling

- Sending requires a separate, explicit instruction from custice.
- Before sending, re-check the official contact URL and remove no questions
  without recording why.
- Store no personal respondent data or unpublished attachment in the repo.
- Record any reply as cited evidence; do not convert a non-answer into approval.
- Do not use the draft or a reply to modify the retrieval allowlist, create a
  new authorization, or initiate a network request without a separate contract
  and independent approval.
- A reply about licensing does not by itself establish label maturity, temporal
  fitness, privacy safety, or modern-population representativeness.
