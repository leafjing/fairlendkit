# RECS-Q2 — controlled retrieval contract

Status: proposed offline contract. This document and its future Harness do not
authorize network access, admission, promotion, repository inclusion, or
redistribution.

## Exact source allowlist

One single-use Run retrieves exactly these three HTTPS resources from
`www.eia.gov`, with no query, fragment, credentials, alternate port, or
cross-host redirect:

| Role | Exact path | Bytes | Required media type |
|---|---|---:|---|
| data | `/consumption/residential/data/2020/csv/recs2020_public_v7.csv` | 56044261 | `application/octet-stream` |
| codebook | `/consumption/residential/data/2020/xls/RECS%202020%20Codebook%20for%20Public%20File%20-%20v7.xlsx` | 58382 | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| methodology | `/consumption/residential/data/2020/pdf/microdata-guide.pdf` | 581524 | `application/pdf` |

The Harness requires status 200, the exact normalized media type, exact
`Content-Length`, exact streamed byte count, and a per-file ceiling equal to
the expected size. It permits no generic missing-type exception. A failure in
any resource fails and cleans the whole Run.

## File validation

The CSV validator streams without logging rows and requires UTF-8-compatible
ASCII header syntax, one header, a stable field count for every nonblank row,
no NUL bytes, and conservative field/record ceilings. The header must contain
exactly one `DOEID`, exactly one `NWEIGHT`, and every `NWEIGHT1` through
`NWEIGHT60` exactly once. Extra replicate-weight names matching
`NWEIGHT[0-9]+` are rejected. Duplicate columns are rejected.

`DOEID` is an isolation identifier only. The Harness may verify that each value
is nonblank and unique in the retrieved file, but it must never write a value
to an audit, error, log, fixture, cache key, derived filename, feature list, or
model input. Later adapters must discard it before producing canonical records.

The XLSX validator requires ZIP local/end signatures, a single non-encrypted
OOXML package, safe normalized member paths, no symlinks or nested archives,
bounded member count/uncompressed size/compression ratio, and required
`[Content_Types].xml` plus workbook relationships. The PDF validator requires
`%PDF-` at byte zero, a terminal `%%EOF` within the bounded tail, and rejects
embedded-file indicators. Both documentation files are scanned for explicit
third-party/licensed/copyright notices; matches are recorded only as bounded
term/count evidence and force `third_party_review_required=true`. Absence of a
match is not a legal conclusion.

## Lifecycle and authorization

The authorization is an external mode-`0400` JSON snapshot bound to the exact
Harness commit, Harness/test SHA-256 values, three URLs, sizes, types and limits,
one Run ID, `max_attempts=1`, validity no longer than 24 hours, and separate
repository-external mode-`0700` quarantine/audit roots.

Before transport, the Harness creates an exclusive mode-`0400` `.spent`
marker. The audit records `prepared -> started -> succeeded` or
`prepared -> started -> failed -> cleaned`. Failure removes all partial,
archive, and extracted bytes. Audit output contains only response metadata,
byte counts, SHA-256 values, structural results, third-party scan counts, and
safe failure classes; it never contains CSV rows or `DOEID` values. A consumed
Run ID is never retried.

## Required offline tests

- exact three-resource success with hashes and read-only quarantine files;
- missing, duplicate, or extra replicate-weight columns;
- missing/duplicate `DOEID`, duplicate CSV columns, malformed width, NUL,
  truncation, oversize stream, wrong length, wrong media type, and interruption;
- invalid XLSX signature, traversal, symlink, encryption, nested archive,
  missing OOXML members, size/count/ratio excess, and third-party notice flag;
- invalid PDF signature/EOF and embedded-file indicators;
- redirect/host/scheme/query rejection;
- failure on resource two or three removes bytes from earlier resources;
- exclusive `.spent`, exact state transitions, audit-write failure fallback,
  cleanup verification, and second-attempt rejection before transport; and
- assertions that no audit, exception, path, or fixture contains a `DOEID`
  value or CSV row.

Passing these tests is necessary but not sufficient for execution. The exact
implementation commit and authorization must receive independent approval
before any live Run.
