# AD-D1-UCI — South German Credit admission proposal

Status: **pending independent review**. This document proposes a bounded
one-time retrieval gate. It does not authorize a download, populate a checksum,
or change the candidate manifest from `evidence_incomplete`.

- Candidate: `uci-south-german-credit-2019`
- Proposed disposition after successful retrieval verification: `repository`
- Proposed analytical use: generic credit-risk metric and adapter benchmark
- Prohibited claim: evidence about cash flow, rent, utilities, alternative-data
  coverage, present-day German or U.S. borrowers, or production lending
- Official identity: UCI dataset 573; DOI `10.24432/C5QG88`
- Official package URL:
  <https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip>
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
  Repository, DOI `10.24432/C5QG88`, and any creator/citation UCI identifies;
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

The reviewer may authorize exactly one metadata-recorded retrieval attempt only
after the deterministic harness and tests named below are committed and
independently reviewed. This prose is not executable authorization. Any unmet
control aborts without admitting bytes.

### Required harness and review command

The prepared implementation must consist of:

- `scripts/retrieve_uci_south_german_credit.py`, containing no import-time or
  default network action; and
- `tests/test_uci_south_german_credit_retrieval.py`, using an injected fake
  transport and temporary directories only.

The only permitted live invocation after a separate authorization is:

```text
python3 scripts/retrieve_uci_south_german_credit.py retrieve \
  --authorization-file <approved-absolute-read-only-json-path>
```

The URL, host allowlist, expected sizes, member allowlist, and limits in this
proposal are compiled constants, not caller-overridable flags. There is no retry
or resume mode. Before authorization, reviewers run only:

```text
python3 -m pytest tests/test_uci_south_german_credit_retrieval.py -q
```

The test suite must cover an allowed redirect chain plus wrong-host, downgrade,
IP-literal, credential-bearing, excessive-hop, oversized-header, oversized-
stream, truncated/interrupted-stream, and content-length-mismatch responses. ZIP
fixtures must cover valid structure plus absolute and parent traversal, NUL,
duplicate path, case collision, Unicode-normalization collision, symlink,
device/non-regular member, encryption, nested archive, excess member count,
member and total size excess, compression-ratio excess, trailing/concatenated
payload, missing member, unexpected member, and exact-size mismatch. Each
failure assertion also proves no source byte remains and no second attempt with
the same run ID can start.

### Authorization binding

The reviewer-issued JSON is created only after the harness commit passes review.
It is an absolute, regular, non-symlink file with mode `0400`, outside the
repository and quarantine. Its strict schema contains no unknown fields and
binds all of the following:

- authorization ID, single-use run ID, issue time, UTC expiry no later than 24
  hours after issue, candidate ID, and `max_attempts=1`;
- exact package URL, allowed redirect host `archive.ics.uci.edu`, HTTPS-only
  policy, maximum five redirects, expected final `Content-Length=13130`, maximum
  streamed bytes `16384`, and allowed final media types `application/zip`,
  `application/x-zip-compressed`, or `application/octet-stream`;
- exact three-member names and sizes, expected total uncompressed bytes `58644`,
  maximum uncompressed bytes `65536`, member count `3`, and compression-ratio
  ceiling `100`;
- reviewed harness Git commit, SHA-256 of the harness file, and SHA-256 of its
  test file; and
- exact absolute quarantine and audit roots.

Before any network access, the harness validates the authorization file mode,
schema, expiry, run ID, roots, compiled constants, its own file SHA-256, test-file
SHA-256, and reviewed Git commit. Any difference, dirty harness/test file, expired
record, missing field, or prior `.spent` tombstone fails closed and requires a
new independent authorization. The authorization record is an approval artifact,
not a caller-editable configuration file.

### Network controls

- Initial URL must exactly match the official HTTPS package URL above.
- TLS certificate and hostname verification are mandatory; HTTP downgrade,
  ignored certificate errors, credentials, cookies, query tokens, and proxy-
  supplied authentication are prohibited.
- Permit at most five redirects, each to HTTPS on `archive.ics.uci.edu`; reject
  every other hostname, IP-literal target, port, scheme, embedded credential,
  query string, or fragment.
- Require a final `Content-Length` of exactly 13,130 bytes when supplied and
  enforce an absolute streamed-byte ceiling of 16,384 bytes regardless of the
  header. Timeout, truncation, excess bytes, or content mutation fails closed.
- Record only redirect scheme/host/path, final scheme/host/path, retrieval UTC
  time, safe HTTP validators, media type, compressed byte count, and SHA-256.
  Audit records never contain query strings, fragments, credentials, cookies,
  authorization headers, signed URL parameters, response content, or member
  content. The fixed package URL contains no query, and any redirect that adds
  one is rejected rather than redacted and followed.

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

- Both approved roots must resolve outside the repository worktree, outside the
  user's shared download directories, and outside each other. Symlinked roots,
  world/group-writable parents, relative paths, and pre-existing run paths are
  rejected.
- The harness creates `<quarantine-root>/<run-id>/` with mode `0700` using an
  exclusive create. It creates `<audit-root>/<run-id>.spent` exclusively with
  mode `0400` before the first request. This non-sensitive tombstone is retained
  indefinitely; its existence makes the same run ID fail before network access.
  The run can never be retried, resumed, or overwritten, including after failure.
- Partial response bytes use a newly and exclusively created file with mode
  `0600`. Temporary extraction, if needed after structural validation, uses only
  a private `0700` child directory. The harness never executes, imports, sources,
  or shells any downloaded member.
- On success, the ZIP and verified members remain only inside the non-repository
  run directory, with files changed to mode `0400` and directories kept `0700`.
  Nothing is copied, moved, linked, staged, or committed under `data/`, `docs/`,
  tests, fixtures, caches, or another repository path.
- Promotion to `data/vendor/uci-south-german-credit-2019/raw/` is a later action
  requiring a follow-up reviewed commit proposal containing the completed
  manifest, hashes, NOTICE, data card, schema-validation evidence, and privacy
  result. Retrieval authorization is neither promotion nor admission approval.

### Cleanup, retention, and audit lifecycle

- The audit root contains one `<run-id>.json` record created exclusively with
  mode `0600`. It records authorization identity, state transitions, timestamps,
  redirect metadata, byte counts, hashes or failure reason, cleanup outcome, and
  retention deadline, but never source bytes or row/member content.
- State transitions are append-safe and monotonic:
  `prepared -> started -> succeeded` or `prepared -> started -> failed`. A final
  `cleaned` transition records byte removal; no terminal state can return to
  `started`.
- On failure or interruption, a `finally` path closes handles and unlinks the
  partial ZIP plus every temporary member before returning. It then removes
  empty temporary directories and records whether cleanup completed. The tests
  inject interruption at every write/extraction phase. The contract requires
  unlinking and directory synchronization; it does not claim forensic secure
  erasure on copy-on-write or journaled storage.
- A failed run retains only its non-sensitive audit JSON for 30 calendar days,
  then the approved cleanup command removes it. The `.spent` tombstone remains.
  Failed source and extracted bytes have zero retention and are removed before
  the command exits.
- A successful quarantined package is retained for at most 7 calendar days from
  `succeeded`. It remains `0400`/`0700` and inaccessible to product code. If the
  follow-up review has not approved promotion by the deadline, the cleanup
  command deletes all source/member bytes and marks the audit `cleaned`.
- The only cleanup invocation is:

  ```text
  python3 scripts/retrieve_uci_south_german_credit.py cleanup \
    --authorization-file <same-approved-absolute-read-only-json-path>
  ```

  It performs no network operation, is scoped to the exact run ID, preserves
  the `.spent` tombstone, and refuses paths outside the two approved roots.
  Automatic retry, scheduled redownload, and cleanup by broad glob or recursive
  repository path are prohibited.

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
