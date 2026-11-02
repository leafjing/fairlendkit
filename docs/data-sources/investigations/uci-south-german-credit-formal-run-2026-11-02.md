# UCI dataset-573 formal Harness Run

Status: failed closed; no source bytes retained and no admission granted.

## Execution identity

- Candidate: `uci-south-german-credit-2019`, repointed to official UCI dataset
  573 by the approved metadata chain
- Package URL:
  <https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip>
- Run ID: `uci573-formal-20261102t041415z-fe6d427`
- Execution timestamp: `2026-11-02T04:15:11.189314+00:00`
- Authorization ID: `uci573-formal-auth-20261102-001`
- Authorization SHA-256:
  `e7a190821ba0e6f8252bc63fc180ca8d3c6dffa48f4023e897dfec33e0a607e5`
- Authorization file mode: `0400`
- Harness commit: `fe6d42795262fb39ed9e69d903890a4492225220`
- Harness SHA-256:
  `24dadc90f25751e76045fa5304f5278e339104af628dbbecee99ca57a200c75f`
- Harness-test SHA-256:
  `e99164ee49d888165cdd0dc22d92305e5c185d7936eaa05de53d8aba8f07ecfc`
- Maximum attempts: one

The authorization bound HTTPS and the single UCI host, maximum five redirects,
an exact expected compressed size of 13,130 bytes, a 16,384-byte streamed
ceiling, three exact expected members, 58,644 expected uncompressed bytes, a
65,536-byte uncompressed ceiling, and a maximum compression ratio of 100. The
allowed response media types were `application/zip`,
`application/x-zip-compressed`, and `application/octet-stream`.

## Recorded result

- Failure: `ValueError: response media type is not an authorized ZIP type`
- Lifecycle: `prepared -> started -> failed -> cleaned`
- `cleanup_completed`: `true`
- `remaining_bytes_state`: `absent`
- Retention deadline: `2026-12-02T04:15:11.189314+00:00`
- Audit file mode: `0600`
- Audit SHA-256:
  `8c497a2bef7076694b29bb24da75f3f8c0eb8d524e7a2f900fdc427fd495950a`
- Permanent `.spent` mode: `0400`
- Permanent `.spent` SHA-256:
  `c60a409ccef2944d1b9440288fdca537e93febf40de548d5fa13a37854b821fa`
- Quarantine after cleanup: empty
- Retained compressed bytes: zero
- Retained uncompressed bytes: zero

The Run ID is permanently consumed. It must not be retried, amended, or used to
claim a completed retrieval. Because no archive survived the fail-closed media-
type check, there is no formal ZIP SHA-256, member list, member size, or member
hash to add to the pending manifest.

## Admission consequence

UCI dataset 573 remains `evidence_incomplete`. The affirmative CC BY 4.0 page,
DOI, schema narrative, and bounded `quality_only` assessment remain valid
metadata evidence, but they do not substitute for the missing formally retained
package. `release_id` and `release_date` remain `null`, redistribution remains
`unverified`, `files` remains empty, and promotion or repository inclusion is
not authorized.
