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
  fixture, and the actual installed `pip freeze --all`. The installed freeze
  must byte-match the checked-in environment lock.
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

The raw payload is a frozen allowlist schema: canonically sorted metric values,
definedness, reliability states, uncertainty bounds, registered flag codes,
and registered limitation codes. All four metric-key sections must contain the
same unique registered metric keys. No opaque mapping or extra field is
accepted, so an aggregate result cannot be hidden under a new key.

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
duplicate, missing, corrupted, unexpected, or identity-mismatched shards.
It also rejects derived result fields and confirmatory replicate ranges.

Run the clean-environment preflight with:

```bash
./scripts/verify_paper2_execution_gate.sh
```

Passing this command is evidence only. It is not permission to run the matrix.
