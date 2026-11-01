# Milestone 4 Release Evidence

## Final release identity

Milestone 4 adds the first installed command-line audit workflow and three
renderer views of the existing `AuditResult` Schema 2.0. The final reviewed
candidate is `68448f56444dd29ee50a8b64770178fd5f1f4bd0`. PR #46 merged it to
`main` as `2e1258fc6b970e982d663f4cc2f233b3a63efd17` on 2026-10-16.

Independent review initially identified a cross-runtime one-ULP artifact
divergence and requested changes at `99c506a`. After the deterministic summation
fix, the independent reviewer re-reviewed `68448f5` and approved it, explicitly
recording that the golden hash gate remained intact and both runtime jobs were
green.

## Shipped surface

- Installed command: `fairlendkit audit`.
- Inputs: one UTF-8 CSV dataset and one UTF-8 JSON `AuditConfig`.
- Outputs: `audit-result.json`, `metrics.csv`, and `report.html`.
- Format selection: repeatable `--format`; omission selects all formats.
- Publication: fixed filenames, overwrite protection, staging, rollback, and
  preservation of unrelated output-directory files.
- Expected failures: stable exit codes and concise diagnostics without record
  data or tracebacks.

## Cross-format evidence

The checked-in synthetic workflow input and configuration live under
`examples/workflow/`. The release gate builds and installs the wheel into a
clean environment, runs the installed console command, and verifies SHA-256
identities for all three artifacts using `artifact-sha256.txt`.

The JSON artifact is the canonical compact Schema 2.0 serialization plus one
newline. CSV preserves canonical metric order and joins uncertainty by metric
key. HTML contains the required sections, uses only escaped text, and has no
scripts or network assets. Neither renderer calls metric code or changes the
audit result.

## Failure-path evidence

Automated tests cover:

- missing and invalid command arguments;
- repeated singleton arguments;
- unreadable or unparseable inputs;
- validation failures without sensitive diagnostics;
- existing targets without explicit overwrite;
- refusal to overwrite non-regular targets;
- a renderer exception before publication;
- a simulated mid-publication failure with restoration of every prior selected
  artifact; and
- preservation of unrelated files when a format subset is selected.

## Verification commands

```bash
./scripts/verify_milestone4_release.sh
```

The clean Python 3.12 verification on the implementation candidate reported:

- exact locked dependency freeze;
- all three workflow artifact hashes matched;
- `372 passed` for the complete suite;
- `6 passed` for the independent architecture suite;
- discoverability metadata and links verified; and
- `git diff --check` clean.

## Independent approval and CI closure

The PR #46 CI run `38854126556` completed successfully for both required jobs:

- Python 3.11 job `116821664551`; and
- Python 3.12 job `116821664324`.

After merge, push run `38854319516` re-executed the complete Milestone 4 release
verifier and Paper 2 execution-freeze check on merge commit `2e1258f`. Python
3.11 job `116822270306` and Python 3.12 job `116822269903` both completed
successfully. The final approval, merge identity, two-runtime pre-merge gate,
and two-runtime post-merge gate therefore close Milestone 4; no candidate gate
remains outstanding.

Evidence URLs:

- PR and final review: <https://github.com/leafjing/fairlendkit/pull/46>
- pre-merge CI: <https://github.com/leafjing/fairlendkit/actions/runs/38854126556>
- post-merge CI: <https://github.com/leafjing/fairlendkit/actions/runs/38854319516>

## Scope boundary

Milestone 4 adds presentation and execution adapters only. It does not add
threshold scanning, a fairness-performance frontier, proxy-risk screening,
governance dispositions, mitigation, recommendations, retraining, or legal and
compliance conclusions. Paper 2 confirmatory execution remains frozen and no
research seal or result is produced by this release gate.
