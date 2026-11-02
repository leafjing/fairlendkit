# UCI-M2 — South German Credit successor-endpoint metadata

Status: metadata-only investigation; no download, response-body read, admission,
promotion, repository inclusion, or redistribution approval.

- Existing candidate: `uci-south-german-credit-2019`
- Observation time: `2026-11-02T04:04:39Z`
- Custice-supplied landing URL:
  <https://archive.ics.uci.edu/dataset/573/south%2Bgerman%2Bcredit>
- Custice-supplied package URL:
  <https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip>
- Custice-supplied citation: `South German Credit [Dataset]. (2020). UCI
  Machine Learning Repository. https://doi.org/10.24432/C5QG88.`
- Method: HTTP HEAD with redirect following only
- Prohibited and not performed: GET, Range, response-body read/save, package
  retrieval, member inspection, allowlist change, or reuse of the consumed Run
  ID

## Observations

The landing URL returned `200` with no redirect, `Content-Type: text/html`,
`Content-Length: 92227`, `ETag: "1e58dj4"`, and TLS verification success.

The exact package URL returned `200` with no redirect and TLS verification
success. Its HEAD response supplied none of `Content-Type`, `Content-Length`,
`ETag`, or `Last-Modified`. This proves only that the official UCI endpoint was
reachable at the observation time. It does not establish GET semantics,
package bytes, members, version, or checksum.

The DOI HEAD chain was:

1. `https://doi.org/10.24432/C5QG88` -> `302` to
   `https://archive.ics.uci.edu/dataset/573`;
2. `/dataset/573` -> `302` to
   `/dataset/573/south+german+credit+update`; and
3. the final UCI page -> `200`, `Content-Type: text/html`,
   `Content-Length: 92225`, `ETag: "1goad4d"`.

The DOI therefore binds dataset ID 573 to UCI's `south+german+credit+update`
record. This is materially different from the consumed Run, which pinned
dataset ID 522, DOI `10.24432/C5X89F`, and package
`/static/public/522/south+german+credit.zip`. The old Run remains spent and is
not a retry target.

## Determination and proposed next authorization

The supplied identifiers pass metadata-only publisher-host, reachability, and
DOI-resolution checks. They do not yet establish that dataset 573 supersedes
522 byte-for-byte or semantically, and the existing candidate manifest must not
be silently repointed before review.

Subject to independent review and a new explicit execution authorization, a
new single-use Run may pin only:

- landing host/path: `archive.ics.uci.edu`, dataset ID `573`;
- package host/path:
  `/static/public/573/south+german+credit+update.zip`;
- persistent identifier: `doi:10.24432/C5QG88`;
- method: one controlled GET through the already reviewed fail-closed Harness;
- isolation: a new repository-external quarantine and a new Run ID; and
- stop conditions: any redirect, status, media-type, size, member, cleanup, or
  identity mismatch, with no automatic retry.

The execution may compute byte/member hashes and capture the Harness audit in
quarantine for Q3 review, but retrieval alone must not update the pending
manifest, admit the source, promote bytes, or authorize redistribution. The new
authorization must explicitly decide whether the existing exact media-type and
size contract is suitable for endpoint 573; this document does not widen it.

