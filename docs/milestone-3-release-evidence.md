# Milestone 3 release evidence

This record accompanies the Milestone 3.5 release gate. It describes the
checked-in evidence; it does not expand product scope.

## Reproduction entry point

Run from a clean checkout:

```bash
./scripts/verify_milestone3_release.sh
```

The script bootstraps the exactly pinned `virtualenv` tool into a temporary
directory, creates a real temporary virtual environment, and installs the
exact build and application/test dependency versions in the three
`requirements-release*.txt` files. It installs the project without dependency
resolution or build isolation, records `python --version`, and strictly
compares the normalized final `pip freeze --all` with
`docs/milestone-3-release-pip-freeze.txt`. It then generates the synthetic
result, byte-compares it with the checked-in oracle, verifies SHA-256, runs all
tests and architecture tests, and runs `git diff --check`. Any mismatch exits
non-zero.

## Frozen artifact

- Generator: `examples/synthetic/run_audit.py`
- Canonical JSON: `examples/synthetic/audit-result-v2.json`
- SHA-256 file: `examples/synthetic/audit-result-v2.sha256`
- SHA-256: `19f9bce01b90186040346079d36ab6fd5be1f209db1ea08b064537c7ae3c02f0`
- Serializer: `AuditResult.model_dump_json()` with no indentation or alternate
  serialization path

## Verified environment and results

Local clean-environment verification on 2026-10-08 used Python 3.12.3 and the
complete final environment recorded in
`docs/milestone-3-release-pip-freeze.txt`:

- full suite: `239 passed`;
- architecture suite: `4 passed`;
- canonical JSON byte comparison: passed;
- fixed SHA-256 comparison: passed; and
- final `pip freeze --all` comparison: passed; and
- `git diff --check`: passed.

GitHub Actions runs this same fail-closed release verifier on the supported
Python 3.11 and 3.12 matrix. Each job therefore prints its exact Python version
and final `pip freeze --all`, and enforces the same locked environment, oracle
bytes, SHA-256, test, architecture, and diff checks used locally.

## Scope audit

Milestone 3 exports the core `run_audit` API and Schema 2.0 result only. The
release scan confirms no CLI entry point, HTML/CSV renderer, threshold scan,
proxy screening, governance integration, or mitigation workflow is claimed or
implemented. Those remain later milestones.
