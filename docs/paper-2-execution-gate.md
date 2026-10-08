# Paper 2 confirmatory execution preflight gate

Status: implementation only. This gate does not authorize or execute the
confirmatory matrix, public-data download, analysis, or result inspection.

## Frozen execution plan

- Protocol/A1 commit: `865a2baf549d691d602334379ed03a7883989d6f`.
- Implementation base: `main@1143d0e5795eefa1abb3de4bf52fdc9eaf8f9b91`.
  The manifest verifies this commit is an ancestor of the real current HEAD.
- Code commit is read directly from `git rev-parse HEAD`; callers cannot supply
  it. A dirty tree, branch name, tag, or abbreviated SHA is rejected.
- The manifest records SHA-256 values for `protocol.json`, the normative A1
  fixture, `requirements-release.txt`, the actual installed
  `pip freeze --all`, and the resolved Python executable. It also records the
  actual Python version. The installed freeze must byte-match the checked-in
  `docs/milestone-3-release-pip-freeze.txt`; these values are derived at
  runtime and cannot be supplied by a caller.
- The frozen scenario set is the union of C1/C3–C6 inputs and the 25 H2
  scenarios: 29 unique scenario IDs.
- Each scenario has 50 immutable shards of 1,000 replicate IDs: `[0,1000)`,
  ..., `[49000,50000)`. There are 1,450 shards and no dynamic repartitioning.
- Parallelism is a deterministic process-per-shard queue with 4 workers, a
  4-CPU budget, and a 16-GiB memory budget. Scheduling order cannot affect
  seeds, rows, filenames, or hashes.
- Checkpointing is whole-shard only. A valid successful shard is reused
  byte-for-byte; an interrupted incomplete pair is discarded and the whole
  shard is retried. Successful artifacts are immutable.

## Artifact boundary

Each shard writes one canonical JSONL file of raw replicate records and one
canonical metadata file. Metadata contains scenario, shard ID, half-open
replicate range, row count, records SHA-256, code/protocol/environment
identities, Python version, and success status.

The raw payload is the versioned `paper2-raw-replicate-v1` recursive allowlist
schema: canonically sorted finite metric values, boolean definedness, closed
reliability states, finite uncertainty bounds, registered flag codes, and
registered limitation codes. All four metric-key sections must contain the
same unique registered metric keys. Unknown top-level or nested shapes, opaque
mappings, non-finite numbers, and extra fields are rejected, so an aggregate
result cannot be hidden under a new key.

Artifacts are addressed only through an absolute, already-resolved
`ExecutionWorkspace` root. The implementation appends the fixed
`paper2-smoke-raw-v1` or `paper2-confirmatory-raw-v1` directory itself; callers
cannot provide filenames or scenario paths. Namespace mismatches, absolute or
relative user paths, `..`, output symlinks, and resolved paths escaping the
workspace root fail closed. Shard identity and half-open range are independently
unique, and every confirmatory boundary is derived from the frozen plan.

Intermediate payloads must not contain estimates, standard errors, p-values,
Holm outputs, figures, or plots. No code in this gate calculates those values.
The complete-set validator checks every expected file, identity, hash, row,
scenario, and replicate ID. It rejects missing, duplicate, unexpected,
out-of-order, corrupted, or mismatched shards. Downstream aggregation remains
unimplemented and therefore cannot run before all 50,000 replicates are
complete and a separate one-time authorization is issued.

## Smoke-only counterexamples

`tests/test_paper2_execution_gate.py` uses only the isolated smoke range and
proves successful and interrupted resume behavior plus fail-closed handling of
duplicate identity/ranges, missing, corrupted, unexpected, path-escaping, or
identity-mismatched shards. It also rejects nested derived-result fields,
unknown schema versions, non-finite values, and confirmatory replicate ranges.

Run the clean-environment preflight with:

```bash
./scripts/verify_paper2_execution_gate.sh
```

Passing this command is evidence only. It is not permission to run the matrix.
The verifier runs the phase-one clean-environment gate and `git diff --check`
over the complete PR range; either non-zero result fails the gate.
