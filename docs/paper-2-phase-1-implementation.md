# Paper 2 phase-one implementation evidence

This phase implements the frozen experiment contracts without running or
summarizing the confirmatory matrix. Product APIs and report schemas are
unchanged.

Implemented components:

- strict machine-readable protocol manifest and production-run lock;
- exhaustive registered synthetic scenarios and frozen pairing IDs;
- SHA-256 counter RNG with isolated generator and analysis domains;
- selection/performance DGP equations, deterministic solvers, missingness
  transforms, and shared-prefix paired streams;
- generic studentized-mean, Holm, Type 7, and H2 paired-unit bootstrap
  primitives; and
- smoke-only orchestration using a seed namespace that cannot overlap the
  production master seed.

Run the phase gate with:

```bash
./scripts/verify_paper2_phase1.sh
```

The gate rejects checked-in confirmatory/production result artifacts, then
delegates to the existing clean-venv release verifier. That verifier installs
the exact locked environment, executes the complete suite (including contract,
smoke, and architecture tests), validates the existing product oracle, and
runs `git diff --check`. The gate does not expose confirmatory
estimates, standard errors, p-values, or Holm results.

## Frozen protocol traceability

| Frozen protocol clause | Implementation | Mechanical evidence |
| --- | --- | --- |
| Strict protocol identity, `R=50,000`, checkpoints, and five confirmatory IDs | `research/paper2/protocol.py` and `protocol.json` | manifest contract test |
| Confirmation remains locked until a later approval | `Paper2Protocol.authorize` | confirmatory rejection and isolated smoke-ID tests; phase-gate artifact scan |
| Exhaustive scenario registry and H2 paired units | `research/paper2/registry.py` | 124-entry registry contract and checked-in registry golden hash |
| Single pairing-aware generator root and isolated row/missingness streams | `research/paper2/rng.py` | exact eight-word fixtures for both generator roles |
| Analysis RNG cannot generate experiment rows | registered `analysis_rng` domains | exact summary/H2 stream fixtures and invalid-role tests |
| Frozen selection, performance, and missingness DGPs | `research/paper2/dgp.py` | selection, performance, and MNAR DGP golden hashes; equation/solver tests |
| Shared prefixes for paired sample-size scenarios | `generate_audit` pairing logic | paired-prefix regression test |
| Studentized mean, Holm, Type 7, and H2 bootstrap definitions | `research/paper2/statistics.py` | hand-calculated component, tie-order, deterministic bootstrap, and fail-closed tests |
| Smoke validation cannot overlap the confirmatory seed | `research/paper2/smoke.py` | deterministic smoke test and explicit inequality with production stream |

The checked-in fixture is `tests/fixtures/paper2_phase1_golden.json`. It
contains only contract inputs and exact engineering oracles; it contains no
confirmatory replicate, estimate, standard error, p-value, or Holm output.

## Non-execution evidence

- `Paper2Protocol.authorize` rejects every confirmatory-mode request in phase
  one, including partial ranges.
- Smoke IDs are restricted to `0..99` and use a distinct master-seed
  namespace.
- `verify_paper2_phase1.sh` fails if a confirmatory/production result artifact
  is checked in, before running any tests.
- The phase-one code contains no confirmatory matrix runner or result writer.
- Validation is limited to unit, golden, architecture, and isolated smoke
  tests; replicate IDs `0..49999` have not been executed or summarized.
