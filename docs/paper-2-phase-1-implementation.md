# Paper 2 phase-one implementation evidence

This phase implements the frozen experiment contracts without running or
summarizing the confirmatory matrix. Product APIs and report schemas are
unchanged.

Implemented components:

- strict machine-readable protocol manifest and production-run lock;
- exhaustive registered synthetic scenarios and frozen pair IDs;
- A1 seven-field SHA-256 counter RNG with closed routing, exact transforms,
  rejection sampling, and isolated generator/analysis streams;
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
| Strict A2 protocol identity, `R=5,000`, checkpoints, and five confirmatory IDs | `research/paper2/protocol.py` and `protocol.json` | manifest contract test |
| Confirmation remains locked until a later approval | `Paper2Protocol.authorize` | confirmatory rejection and isolated smoke-ID tests; phase-gate artifact scan |
| Exhaustive scenario registry and H2 paired units | `research/paper2/registry.py` | 124-entry registry contract and checked-in registry golden hash |
| A1 seven-field root, counter word order, endpoint-safe transforms, and unbiased bounded integers | `research/paper2/rng.py` | normative A1 seed/digest/word/endpoint/rejection fixtures plus independent test-only implementation |
| Closed pair/shared/scenario routing | `generator_scope` and frozen registry `pair_id` values | all four paired analyses, collision, scenario-isolation, and per-group prefix tests |
| Analysis RNG cannot generate experiment rows | registered `analysis_rng` purposes | exact H2/summary fixtures, complete `(2000,5)` and `(2000,17)` byte comparison/hashes, and invalid-route tests |
| Frozen selection, performance, and missingness DGPs | `research/paper2/dgp.py` | selection, performance, and MNAR DGP golden hashes; equation/solver tests |
| Shared prefixes for paired sample-size scenarios | `generate_audit` pairing logic | paired-prefix regression test |
| Studentized mean, Holm, Type 7, and H2 bootstrap definitions | `research/paper2/statistics.py` | hand-calculated component, tie-order, deterministic bootstrap, and fail-closed tests |
| Smoke validation cannot overlap the confirmatory seed | `research/paper2/smoke.py` | deterministic smoke test and explicit inequality with production stream |

The normative A1 fixture is `docs/fixtures/paper2-rng-a1-golden.json`; the
phase-one registry, DGP, and complete-index hashes are in
`tests/fixtures/paper2_phase1_golden.json`. They contain only contract inputs
and exact engineering oracles, never confirmatory estimates, standard errors,
p-values, or Holm output. The locked Paper 2 environment pins `scipy==1.17.1`
as required by A1.

## Non-execution evidence

- `Paper2Protocol.authorize` rejects every confirmatory-mode request in phase
  one, including partial ranges.
- Smoke IDs are restricted to `0..99` and use a distinct master-seed
  namespace.
- `verify_paper2_phase1.sh` fails if a confirmatory/production result artifact
  is checked in, before running any tests.
- The phase-one code contains no confirmatory matrix runner or result writer.
- Validation is limited to unit, golden, architecture, and isolated smoke
  tests; A2 confirmatory replicate IDs `0..4999` have not been executed or
  summarized.
