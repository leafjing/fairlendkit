# AD-D1-UCI — South German Credit admission proposal

Status: **pending independent review**. This document proposes a bounded
one-time retrieval gate. It does not authorize a download, populate a checksum,
or change the candidate manifest from `evidence_incomplete`.

- Candidate: `uci-south-german-credit-2019`
- Proposed disposition after successful retrieval verification: `repository`
- Proposed analytical use: generic credit-risk metric and adapter benchmark
- Prohibited claim: evidence about cash flow, rent, utilities, alternative-data
  coverage, present-day German or U.S. borrowers, or production lending
- Official identity: UCI dataset 522; DOI `10.24432/C5X89F`
- Official package URL:
  <https://archive.ics.uci.edu/static/public/522/south+german+credit.zip>
- Current manifest:
  [`../pending/uci-south-german-credit-2019-manifest.json`](../pending/uci-south-german-credit-2019-manifest.json)

## Bounded purpose

The dataset may exercise binary-outcome schema validation, deterministic
adapters, train/test plumbing, and generic risk-metric calculations only. It is
a historical cross-sectional credit sample with no verified decision/index time
or performance window. It therefore cannot establish temporal predictive
validity, label maturity, modern representativeness, fairness of a production
decision, or any of FairLendKit's three alternative signal families.

No row may be interpreted as an underwritten applicant, a thin-file consumer,
or a consumer observed through cash-flow, rental, or utility events. No dataset
record may be linked to another source.

## Field-level privacy review

This review is based only on UCI's official API metadata and accompanying field
descriptions, not on consumer rows.

- **No documented direct identifiers:** the published schema lists no name,
  postal address, email address, telephone number, account/contract number,
  government identifier, exact location, or persistent row identifier.
- **No documented free text:** all documented predictors are quantitative,
  ordinal, binary, or categorical. `telephone` is a landline-registration flag,
  not a telephone number.
- **Financial and behavioral fields:** checking-account status, credit history,
  purpose, transformed credit amount, savings, employment duration, installment
  rate, other debtors, property, other installment plans, number of credits, and
  the binary credit-risk label are sensitive even without direct identifiers.
- **Quasi-identifiers and linkage risk:** exact age plus residence duration,
  employment duration, job, housing, property, household dependants, telephone
  registration, and foreign-worker status can form rare combinations. The
  historical population and 1,000-row sample increase singling-out risk.
- **Protected or proxy-sensitive fields:** `personal_status_sex` combines sex
  and marital status and cannot cleanly recover sex; age is explicit;
  `foreign_worker` may proxy nationality or migration status. Housing,
  employment, property, savings, and telephone registration may proxy
  socioeconomic status. These fields must not be relabeled or treated as clean
  protected-attribute truth.

Proposed privacy disposition: repository inclusion is conditionally plausible
because the documented schema has no direct identifier, free text, account
identifier, or exact location. It is not approved until the authorized byte
inspection confirms the schema and scans for unexpected members, columns, free
text, or identifiers. Raw rows must never enter logs, exceptions, documentation,
or report fixtures. Tests use synthetic rows; benchmark outputs remain aggregate
and pass the existing disclosure boundary.

## Package and project snapshot identity

UCI has not exposed a publisher-issued package revision or checksum in the
verified metadata. `release_id` therefore remains `null`; neither the donation-
date discrepancy nor a project label may be presented as an official release.

If retrieval is authorized, the project snapshot identity is the tuple:

1. canonical package URL after approved redirects;
2. UTC retrieval timestamp;
3. final HTTP metadata recorded by the retrieval record;
4. SHA-256 of the exact ZIP bytes; and
5. SHA-256, exact byte size, and exact case-sensitive path of every accepted
   member.

The project may render a human-readable `project_snapshot_id` derived from the
ZIP SHA-256, but that field is explicitly project-issued and must remain
separate from `release_id`. A changed URL, byte count, member set, member size,
or hash creates a new unreviewed snapshot and fails closed.

## CC BY 4.0 compliance proposal

UCI presents the dataset under Creative Commons Attribution 4.0 International.
Repository inclusion must preserve the following obligations:

- give appropriate credit, including dataset title, UCI Machine Learning
  Repository, DOI `10.24432/C5X89F`, and any creator/citation UCI identifies;
- link to <https://creativecommons.org/licenses/by/4.0/>;
- state whether files, schema names, encodings, or derived artifacts were
  modified, without implying UCI endorsement;
- retain notices supplied with the package and avoid additional legal or
  technical restrictions on the licensed material; and
- label FairLendKit adapter code and synthetic fixtures separately so their
  provenance is not confused with the licensed dataset.

The post-retrieval change must add a repository NOTICE/attribution record with
the exact snapshot hashes, source URL, retrieval timestamp, DOI, license link,
unchanged source members, and a modification log for every derived file. If the
package contains a conflicting notice or term, retrieval verification stops and
the candidate returns to review; this proposal does not resolve that conflict.

## Proposed one-time controlled retrieval gate

The reviewer may authorize exactly one metadata-recorded retrieval attempt with
all of these controls. Any unmet control aborts without admitting bytes.

### Network controls

- Initial URL must exactly match the official HTTPS package URL above.
- TLS certificate and hostname verification are mandatory; HTTP downgrade,
  ignored certificate errors, credentials, cookies, query tokens, and proxy-
  supplied authentication are prohibited.
- Permit at most five redirects, each to HTTPS on `archive.ics.uci.edu`; reject
  every other hostname, IP-literal target, port, scheme, or embedded credential.
- Require a final `Content-Length` of exactly 13,130 bytes when supplied and
  enforce an absolute streamed-byte ceiling of 16,384 bytes regardless of the
  header. Timeout, truncation, excess bytes, or content mutation fails closed.
- Record redirect chain, final URL, retrieval UTC time, HTTP validators, media
  type, compressed byte count, and SHA-256; do not log response content.

### Container controls

- Treat input solely as ZIP; reject encrypted, multi-disk, nested-archive,
  absolute, parent-traversal, NUL-containing, duplicate, case-colliding,
  Unicode-colliding, symlink, device, or non-regular members.
- Require exactly three case-sensitive members and no directory entries:
  `SouthGermanCredit.asc` (47,940 bytes), `read_SouthGermanCredit.R` (7,550
  bytes), and `codetable.txt` (3,154 bytes).
- Require exactly 58,644 total uncompressed bytes, at most 65,536 uncompressed
  bytes, at most three members, and a per-member compression ratio no greater
  than 100:1. Reject trailing or concatenated archive payloads.
- Stream each accepted member through SHA-256 while enforcing its exact size;
  never extract before every central-directory and path check passes.
- Validate text members as non-binary and scan the realized schema for
  unexpected columns, direct identifiers, free text, account/address fields,
  and undocumented row identifiers. A finding stops admission and requires a
  new privacy review.

### Storage and promotion

- Stage the single attempt in an isolated, non-repository quarantine directory
  created for this review; never use a shared user download folder.
- After verification, store the immutable source ZIP and accepted members under
  `data/vendor/uci-south-german-credit-2019/raw/`, with write bits removed. No
  transformed file belongs in `raw/`.
- Promotion into that path requires a follow-up reviewed commit containing the
  completed manifest, hashes, NOTICE, data card, schema-validation evidence,
  and privacy result. Retrieval authorization alone is not promotion approval.
- On any failure, retain only non-sensitive failure metadata needed for review;
  do not commit partial bytes or retry automatically.

## Post-retrieval admission checklist

All items are required in one independently reviewed follow-up change:

- manifest updated with retrieval timestamp, project snapshot identity, ZIP and
  member SHA-256 values, exact sizes, and final redistribution decision;
- data card documenting 1973–1975 provenance, 700/300 class composition, bad-
  credit oversampling, transformed amount, missing temporal semantics, privacy
  review, representation limits, and benchmark-only use;
- CC BY 4.0 license link plus NOTICE/attribution and modification record;
- deterministic adapter with explicit encoding, column order, target mapping,
  and rejection of unknown/missing/extra columns;
- schema validation for exactly 1,000 records and the officially documented
  variables, without emitting row content on error;
- benchmark-only tests using the real source only in the bounded integration
  path and synthetic fixtures for unit tests;
- tests proving the source is not registered as cash flow, rent, utilities,
  alternative-data coverage, or a production/fairness decision dataset; and
- independent sign-off on license, privacy, integrity, and approved/prohibited
  uses before the manifest can leave `evidence_incomplete`.

## Decision requested

The reviewer is asked only whether this proposal is sufficient to authorize the
single controlled retrieval attempt above. Approval would not itself admit,
redistribute, analyze, or commit the dataset. Until explicit approval, the
manifest stays `evidence_incomplete`, all hashes stay null, and no retrieval may
occur.
