# UCI-M2 — South German Credit successor-endpoint metadata

Status: official-page and response-metadata investigation; no package download,
admission, promotion, repository inclusion, or redistribution approval.

- Existing candidate: `uci-south-german-credit-2019`
- Observation time: `2026-11-02T04:04:39Z`
- Custice-supplied landing URL:
  <https://archive.ics.uci.edu/dataset/573/south%2Bgerman%2Bcredit>
- Custice-supplied package URL:
  <https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip>
- Custice-supplied citation: `South German Credit [Dataset]. (2020). UCI
  Machine Learning Repository. https://doi.org/10.24432/C5QG88.`
- Initial method: HTTP HEAD with redirect following only
- Follow-up method after continuous evaluation authorization: GET of the public
  HTML landing page only, without saving it
- Prohibited and not performed: package GET, Range, package retrieval, member
  inspection, allowlist change, or reuse of the consumed Run ID

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

## Official-page license, fields, and fitness evidence

After the architect authorized continuous evaluation, the public landing page
was read without downloading the ZIP. The rendered page and its embedded UCI
record agree on:

- title: `South German Credit`;
- DOI: `10.24432/C5QG88`;
- citation: `South German Credit [Dataset]. (2020). UCI Machine Learning
  Repository. https://doi.org/10.24432/C5QG88.`;
- license: Creative Commons Attribution 4.0 International (`CC BY 4.0`), with
  sharing and adaptation allowed for any purpose subject to attribution;
- donation date: `2020-06-20`;
- sample: 1,000 historical German credits, 700 good and 300 bad;
- period and sampling: 1973–1975, stratified actual-credit sample with bad
  credits heavily oversampled;
- missingness claim: no missing values; and
- structure: 20 predictors plus the binary target `credit_risk`.

The 21 official variable names are `status`, `duration`, `credit_history`,
`purpose`, `amount`, `savings`, `employment_duration`, `installment_rate`,
`personal_status_sex`, `other_debtors`, `present_residence`, `property`, `age`,
`other_installment_plans`, `housing`, `number_credits`, `job`, `people_liable`,
`telephone`, `foreign_worker`, and `credit_risk`.

The official target definition is whether the credit contract was complied with
(`good`) or not (`bad`). The page states that `amount` is monotonically
transformed and that the actual values and transformation type are unknown.
The fields `personal_status_sex`, `age`, and `foreign_worker` require explicit
fairness/sensitive-attribute treatment; `personal_status_sex` combines sex and
marital status and does not permit clean recovery of sex categories.

This evidence supports evaluation as a bounded historical credit-risk benchmark
and generic metric/adapter fixture. It does not support modern-population,
cash-flow, rent, utility, underwriting, causal, or production-fairness claims.
Final suitability still depends on byte/member integrity, actual schema and
coding, attribution packaging, and privacy/provenance review after controlled
retrieval.

## Determination and execution handoff

The supplied identifiers pass metadata-only publisher-host, reachability, and
DOI-resolution checks. They do not yet establish that dataset 573 supersedes
522 byte-for-byte or semantically, and the existing candidate manifest must not
be silently repointed before review.

Under the architect's continuous evaluation authorization, the programmer's
new single-use Run must pin only:

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
manifest, admit the source, promote bytes, or authorize redistribution. The Run
must retain the reviewed exact media-type allowlist and a conservative package-
size ceiling; this document does not authorize a wildcard media type or
unbounded response.
