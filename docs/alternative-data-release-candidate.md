# Alternative-data release-candidate evidence

Status: RC-1 integration evidence. This record does not authorize live data
access, download, admission, promotion, repository storage, or redistribution.

## Approved implementation lineage

The release-candidate branch is created directly from
`5a943692275a58c2db4d579da5667255b6780ea5`. Its approved functional ancestry is:

- AD-0: `489b7147b9141618f1ab5585a3b56d485508604f`
- AD-1: `13971bc48df5d0a7cb40c047382379f0967d964a`
- AD-2: `e2b49dfaa73a84224421b3e407d762eb16d4a866`
- AD-3: `8a448329ab196e473444901f69b1529b86125378`
- AD-4: `5a943692275a58c2db4d579da5667255b6780ea5`

The approved AD-4 contract is
`95e1ce0310147506d044efbe4678567f87e70485`. The contract commit is not an
ancestor of the implementation branch because it was authored on the isolated
documentation branch; the blob ID of
`docs/alternative-data-proxy-screening.md` is `88a0ef0cc137471a7b21f6795adce41b622babd3`
in both the contract commit and this release tree.

The separately reviewed UCI retrieval harness is not part of this release tree.
Its approval covered offline harness implementation only and granted no live
invocation or data permission.

## Public API and canonical release boundaries

Alternative-data APIs are namespaced under `fairlendkit.alternative_data`; the
package-root audit API is unchanged.

- AD-0 exports strict source, record, leakage, coverage, and reason contracts.
- AD-1's only public quality-report builder is
  `build_quality_report_release()`, returning `AggregateReportRelease`.
- AD-2 exports strict adapters and typed canonical signal records. It exposes no
  per-entity profile renderer or decision API.
- AD-3's public diagnostic builder is `build_risk_diagnostic_release()`,
  returning `RiskDiagnosticRelease`; exact internal diagnostic models are not
  exported.
- AD-4's public screening builder is `build_proxy_release()`, returning
  `ProxyRelease`; JSON, CSV, and HTML are deterministic projections of that
  disclosure-controlled typed release.

Quality, risk, and proxy release tests cover primary and complementary
suppression, historical-release constraints, privacy-safe serialization, and
the inability to bypass their public release boundaries.

## Scope and repository-content audit

RC-1 adds no metric, threshold, model, recommendation, or decision behavior.
The release tree contains:

- no alternative-data consumer dataset or downloaded archive;
- no live alternative-data downloader or retrieval command;
- no admitted data manifest with a completed checksum;
- no threshold recommendation, automated feature removal, or model-decision
  endpoint; and
- no causal, discrimination, legality, or compliance conclusion.

The checked-in `examples/workflow/credit.csv` is the pre-existing synthetic
Milestone 4 CLI fixture, not alternative-data consumer evidence.

## Verification

RC-1 is accepted only when all of the following pass from a clean worktree:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src pytest -q tests/test_architecture.py tests/test_discoverability.py
python3 -m compileall -q src tests
git diff --check
```

Observed RC-1 results:

- complete suite: `458 passed`;
- architecture and discoverability suite: `47 passed`;
- discoverability verifier: `discoverability metadata and links verified`;
- public API and prohibited-artifact audit: passed;
- `compileall`: passed; and
- `git diff --check`: passed.

The final RC handoff identifies the single RC commit containing this evidence.
