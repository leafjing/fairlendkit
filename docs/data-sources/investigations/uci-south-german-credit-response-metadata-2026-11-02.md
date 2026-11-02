# UCI-M1 — South German Credit response-metadata evidence

Status: metadata-only investigation; no download, new authorization, admission,
promotion, repository inclusion, or redistribution approval.

- Candidate: `uci-south-german-credit-2019`
- Investigation time: 2026-11-02T01:08:24Z through 2026-11-02T01:08:44Z
- Official landing page:
  <https://archive.ics.uci.edu/dataset/522/south+german+credit>
- DOI: <https://doi.org/10.24432/C5X89F>
- Official package URL:
  <https://archive.ics.uci.edu/static/public/522/south+german+credit.zip>
- Method: existing reviewed failure audit plus HTTP HEAD requests only
- Prohibited and not performed: GET/Range body probe, response-body read/save,
  retry, allowlist change, wildcard media type, new authorization, or package
  retrieval

## Consumed-run evidence

The independently reviewed audit has SHA-256
`62abd4dd5ec40637ad050c0fdc963793a8061370d36ff6662ad2a59c8dcb9032`.
The permanent `.spent` marker has SHA-256
`c60a409ccef2944d1b9440288fdca537e93febf40de548d5fa13a37854b821fa`.
The review established:

- authorization identity and bytes were unchanged at execution;
- state sequence was exactly `prepared -> started -> failed -> cleaned`;
- failure was `response media type is not an authorized ZIP type`;
- `cleanup_completed=true` and `remaining_bytes_state=absent`;
- quarantine contained no residual source or derived byte; and
- no promotion, repository data write, admission, or redistribution occurred.

The reviewed Harness normalizes the final GET header as
`headers["content-type"].split(";", 1)[0].strip().lower()` and rejects when the
result is not one of `application/zip`, `application/x-zip-compressed`, or
`application/octet-stream`. The failure proves the normalized value did not
match that set. The audit schema recorded the failure but not the raw response
headers, redirect chain, final status, or normalized value at this pre-stream
failure point. Consequently, the exact GET `Content-Type` is unavailable and
must not be guessed as empty or copied from a later HEAD response.

## HEAD observations

All observations below used HEAD and read no response body.

### Canonical landing page

At 2026-11-02T01:08:24Z the canonical landing URL returned:

- status `200`;
- no redirect;
- `Content-Type: text/html`;
- `Content-Length: 81018`;
- `ETag: "up6vws"`; and
- `Server: nginx/1.31.4` plus `x-sveltekit-page: true`.

This proves the landing endpoint was live at the observation time. It is not
package-byte or package-header evidence.

### DOI chain

At 2026-11-02T01:08:24Z the DOI HEAD chain was:

1. `https://doi.org/10.24432/C5X89F` -> status `302`, location
   `https://archive.ics.uci.edu/dataset/522`;
2. that UCI path -> status `302`, relative location
   `/dataset/522/south+german+credit`; and
3. canonical landing path -> status `200`, `Content-Type: text/html`,
   `Content-Length: 81018`.

The cross-host DOI redirect is documentation identity evidence only. It is not
an allowed package-download redirect; a future package authorization remains
bound directly to the official package host and package path.

### Package endpoint

At 2026-11-02T01:08:25Z a default HEAD to the exact package URL returned:

- status `200`;
- no redirect or `Location`;
- `Server: nginx/1.31.4`;
- no `Content-Type` header;
- no `Content-Length` header;
- no `ETag` or `Last-Modified`; and
- no observed HSTS, CSP, `X-Content-Type-Options`, or other package-response
  security header beyond the server/date/connection fields.

At 2026-11-02T01:08:44Z the same HEAD was repeated with exactly
`Accept: application/zip` and `User-Agent: FairLendKit-retrieval/1`, matching the
reviewed Harness request headers. It again returned status `200`, no redirect,
and none of `Content-Type`, `Content-Length`, `ETag`, or `Last-Modified`.

The repeated HEAD result is evidence of missing HEAD metadata at those times. It
does not prove the GET header was also absent, because the HTTP method can change
server behavior. No GET or Range probe was made in UCI-M1.

## Blocking determination

The official landing and DOI identity remain reachable, and the exact package
URL still returns a successful HEAD. However, current evidence cannot fix the
actual GET media type:

- the consumed GET failed the exact allowlist but did not retain the raw header;
- HEAD omits both media type and length; and
- HEAD cannot be substituted for GET semantics.

Therefore UCI stays `evidence_incomplete`. The previous run remains permanently
consumed, and no Q3 content, schema, privacy, license-member, or use review is
possible because no isolated byte was retained.

## Next contract recommendation

Do not add an empty value, `text/plain`, `text/html`, or a wildcard to the ZIP
media-type allowlist. Before another live attempt, independently approve one of:

1. affirmative UCI guidance that fixes the package GET status, redirect, media
   type, content length, version/revision behavior, and checksum/member policy;
   or
2. a new offline-tested Harness revision whose audit persists, before rejection,
   only safe response metadata: status, redirect scheme/host/path, header
   presence, normalized media type, content length, validators, and timestamp.

The revised Harness must still stop before body streaming when status, redirect,
media type, or length violates its new independently reviewed authorization. It
must not log credentials, query strings, cookies, response content, or consumer
data. Any future execution requires a new contract approval, new read-only
authorization, new single-use Run ID, and new repository-external quarantine and
audit records. No retry is implied by this recommendation.
