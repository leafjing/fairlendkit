# AD-D0 source manifest contract

The manifest pins the source package expected after authorized retrieval. It is
written from official publisher documentation while pending, then verified
against bytes only after admission authorizes retrieval. A manifest is metadata,
not a downloader.

## Manifest identity

Each candidate has one `source-manifest.json` conceptually conforming to this
strict model. Until tooling exists, the same fields may be recorded in the
candidate Markdown file. Unknown fields are rejected.

```json
{
  "manifest_version": "1.0",
  "candidate_id": "publisher-dataset-release",
  "publisher_legal_name": "",
  "canonical_landing_url": "",
  "persistent_identifier": null,
  "release_id": "",
  "release_date": "YYYY-MM-DD",
  "retrieved_at": null,
  "license_id": "",
  "license_url": "",
  "terms_url": null,
  "redistribution": "unverified",
  "files": [],
  "documentation": [],
  "review_state": "evidence_incomplete"
}
```

Allowed `redistribution` values are `permitted`, `prohibited`, and `unverified`.
Allowed `review_state` values are `evidence_incomplete`, `verified`, `rejected`,
and `superseded`. Pending candidates use `unverified` and
`evidence_incomplete`; absence of license text never becomes `permitted`.

## File entry

Every expected source file has:

- `path`: publisher-relative logical path, with no absolute path or `..`;
- `media_type` and compression/container format;
- `expected_bytes`: publisher-documented integer or null while unverified;
- `publisher_checksum`: algorithm/value or null;
- `repository_sha256`: null before authorized retrieval, then exactly 64
  lowercase hexadecimal digits computed from the downloaded bytes;
- `role`: `data`, `data_dictionary`, `codebook`, `license`, `methodology`, or
  `other_documentation`;
- `contains_row_level_data`: boolean;
- `unit_of_observation`: exact publisher description or null for documentation;
- `expected_columns`: official names only, never values; and
- `redistribution_scope`: `repository`, `external_only`, or `prohibited`.

ZIP/tar containers and each consumed member receive separate entries and hashes.
Hashing an archive alone is insufficient to pin extracted inputs. Case, Unicode
normalization, delimiter, encoding, null tokens, and date parsing remain part of
the later adapter contract, not assumptions in discovery.

## Verification rules

- Canonical URLs use HTTPS when the official publisher supports it; URL
  shorteners and personal mirrors are not canonical sources.
- Official DOI/version metadata must agree with the landing page and file set.
- Repository-computed hashes are populated only after approved retrieval and
  never copied from an unofficial mirror.
- A file, version, terms, license, schema, byte-size, or checksum change marks
  the manifest `evidence_incomplete` and blocks use until re-review.
- The manifest cannot authorize a use broader than the admission decision.
- No access token, signed URL, cookie, consumer identifier, row sample, or local
  filesystem path is stored.

## Multi-source prohibition

Each manifest describes exactly one publisher release and population. Separate
manifests cannot share an entity namespace merely because column names or
demographics resemble each other. Cross-source record linkage is prohibited by
default. Population-level benchmarking may compare separately labeled results
only when definitions and windows are compatible and limitations remain visible.
