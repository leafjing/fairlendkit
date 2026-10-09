# Paper 2 confirmatory execution preflight gate

Status: implementation only. This gate does not authorize or execute the
confirmatory matrix, public-data download, analysis, or result inspection.

## Frozen execution plan

- Protocol/A1 commit: `865a2baf549d691d602334379ed03a7883989d6f`.
- Protocol Amendment A2 commit:
  `4a83ff8872d3393fad4313927045777f65fd3da4`.
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
- Under A2, each scenario has 5 immutable shards of 1,000 replicate IDs:
  `[0,1000)`, ..., `[4000,5000)`. There are 145 shards and no dynamic
  repartitioning.
- Parallelism is a deterministic process-per-shard queue with 4 workers, a
  4-CPU budget, and a 16-GiB memory budget. Scheduling order cannot affect
  seeds, rows, filenames, or hashes.
- Checkpointing is whole-shard only. A valid successful shard is reused
  byte-for-byte; an interrupted incomplete pair is discarded and the whole
  shard is retried. Successful artifacts are immutable.

## Resource preflight

The versioned `paper2-resource-benchmark-v2` resource benchmark runs one
replicate each of `REG`,
`SEL-AIR081-N1000`, `MISS-MCAR30`, and `MISS-MNAR30` in the isolated smoke
namespace. An executable 29-row cost coverage matrix maps every frozen execution
scenario to a measured representative with the same family, missingness, and
calibration path and no smaller sample, missingness, bootstrap, or valid-resample
workload. The coverage check also proves these representatives cover every
frozen scenario family and missingness path and dominate the frozen
matrix on total sample size, missing fraction, bootstrap resamples, and the
minimum-valid-resamples threshold. The benchmark also fails unless the actual
audit result for each measured representative independently contains every
Schema 2.0 metric identity and round-trips through the frozen
`paper2-raw-replicate-v1` artifact schema without losing metric keys. This
covers performance, selection, and expensive missingness paths through DGP,
public `run_audit` metrics/reliability/1,000-resample uncertainty, raw-record
writing, and shard validation. It measures elapsed time, process CPU time,
peak RSS, and canonical artifact bytes but never serializes or reports a smoke
audit result. Projection applies the frozen mapping to every one of the 29
scenarios and sums the mapped CPU, wall, and serialized artifact costs; disk
cost is never derived from an average of the measured artifacts. CPU-hours,
wall time, and disk are extrapolated to 29 × 5,000 replicates with a frozen 2×
safety factor.
The evidence retains each representative's CPU seconds, wall seconds, peak RSS,
and serialized artifact bytes under its scenario ID; aggregate maxima and totals
must reconcile exactly with those sorted, unique measurements.
Each representative runs in a fresh child process, and its process identity and
peak RSS are retained independently alongside its complete metric identity set
and frozen raw-artifact schema. The memory upper bound is recomputed from those
representative RSS values through the same frozen 29-row mapping;
missing, extra, unknown, non-integer, non-isolated, or underestimated RSS
evidence fails closed.
Required memory is the greater of 16 GiB and 4× measured peak RSS.
Artifact bytes come from each complete `run_audit` result mapped into the
strict raw-record schema, including all metric states, uncertainty references,
flags, and limitations; no fixed dummy payload is used for disk projection.
The 2× runtime/disk factors, 4× RSS factor, 10,000 CPU-hour ceiling, and 3,000
wall-hour ceiling are constructor-enforced constants and cannot be overridden
through benchmark evidence.

Generate reproducible host-specific evidence on a clean locked environment:

```bash
python scripts/benchmark_paper2_execution_gate.py
```

Before an authorized run, the same command must use `--require-capacity`.
Preflight fails closed unless the host exposes at least 4 CPUs, 16 GiB memory,
and free disk no smaller than the conservative projected artifact size. The
evidence contains only resource measurements and capacity—not experimental
statistics or plots.

The execution-gate PR intentionally merged while its first trustworthy full-chain
projection exceeded the frozen 10,000 CPU-hour and 3,000 wall-hour limits. A
separate performance gate subsequently optimized only the smoke-measured product
path: SHA-256 counter blocks are consumed in batches, unweighted AUC aggregates
the same pair contributions by score, and count-based bootstrap primitives are
evaluated in batches. Golden streams and a slow reference path prove identical
indices, interval bounds, and canonical `AuditResultV2` bytes. Weighted metrics
and metrics whose floating-point reduction order matters retain the reference
path.

The performance gate does not alter DGP parameters, scenario or replicate sets,
bootstrap counts, valid-resample rules, formulas, thresholds, resource ceilings,
or safety factors. Its smoke-only representative evidence must be regenerated by
the command above in each clean locked environment. Passing resource preflight
is necessary but does not authorize the confirmation matrix: the architect's
separate one-time authorization and a reviewer-issued execution seal remain
mandatory.

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
unimplemented and therefore cannot run before all 5,000 replicates are
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
over the complete PR range; either non-zero result fails the gate. Inside that
fresh locked environment it also invokes the real, unmocked manifest builder
and the smoke resource benchmark, binding evidence to the observed clean HEAD,
interpreter, and installed freeze.

## Post-merge execution seal

The A2 implementation defines `paper2-execution-seal-v2`; it does not
self-issue a seal. The seal binds both the A1 RNG commit and the A2 protocol
merge commit. After
merge, the reviewer must generate canonical seal bytes and publish their
SHA-256 out of band. Runtime validation requires both the seal file and that
external digest, then binds the seal to the actual clean merge HEAD, manifest
hash, frozen 145-shard plan hash, protocol/A1 commit, A2 protocol commit,
protocol manifest,
normative RNG fixture, and environment lock. A missing, modified, symlinked,
self-reported, pre-merge, or identity-mismatched seal fails closed.
