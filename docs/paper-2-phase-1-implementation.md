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
