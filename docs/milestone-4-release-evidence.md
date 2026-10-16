# Milestone 4 Release Evidence

## Candidate identity

Milestone 4 adds the first installed command-line audit workflow and three
renderer views of the existing `AuditResult` Schema 2.0. The implementation is
carried by the `docs/milestone-4-user-workflow` branch and must be reviewed and
merged before this evidence becomes release evidence for `main`.

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

The clean Python 3.12 verification on the implementation candidate reports:

- exact locked dependency freeze;
- all three workflow artifact hashes matched;
- `372 passed` for the complete suite;
- `6 passed` for the independent architecture suite;
- discoverability metadata and links verified; and
- `git diff --check` clean.

CI must independently run the same cumulative gate on Python 3.11 and 3.12
before merge. A green local runtime is not a substitute for both CI jobs.

## Scope boundary

Milestone 4 adds presentation and execution adapters only. It does not add
threshold scanning, a fairness-performance frontier, proxy-risk screening,
governance dispositions, mitigation, recommendations, retraining, or legal and
compliance conclusions. Paper 2 confirmatory execution remains frozen and no
research seal or result is produced by this release gate.

