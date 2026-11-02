# Simulated impact benchmark

This research-only benchmark produces reproducible **simulated** evidence. It
is not a pilot record, customer outcome, production decision, causal estimate,
or compliance conclusion.

The fixed generator uses seed `20261102` and 10,000 synthetic applicants. The
baseline approves `credit_score >= 680`. The simulated tool preserves those
approvals and applies a second look only when `640 <= credit_score < 680`,
alternative data are available, and `alternative_score >= 0.72`. Requested
credit is generated before either decision and is summed only for reporting.

The canonical output reports:

- median baseline and tool decision runtime over 15 repetitions;
- covered applicants with alternative data available;
- approval increment `tool approvals - baseline approvals`;
- credit increment `tool approved requested credit - baseline approved requested credit`;
- average incremental credit `credit increment / approval increment`;
- approved bad rate, true-positive rate, and false-positive rate;
- selection rates by the fixed comparison/reference grouping, selection-rate
  difference `comparison - reference`, and adverse-impact ratio
  `comparison / reference`.

Every JSON result carries the machine-readable status
`simulation_not_production_evidence` in addition to the plain-language
disclaimer.

Runtime varies with the machine and is never treated as a fixed impact claim.
All other values are tied to the canonical synthetic-input SHA-256. Reproduce
the artifact with:

```bash
python scripts/run_simulated_impact_benchmark.py
```

The checked-in result is
[`artifacts/simulated-impact-benchmark-v1.json`](artifacts/simulated-impact-benchmark-v1.json).
Its two runtime fields are measurements from one invocation and will vary by
machine; every impact, risk, and fairness value is deterministic and tested
against the fixed input hash.

The JSON also records the Python/runtime environment, all policy thresholds,
the synthetic requested-credit range and increment, and the exact formulas for
approval, credit, risk, and fairness metrics.

It additionally records the one-page assessment's analyst-effort and review-
coverage assumptions as scenario inputs, never as wall-clock-derived savings.
The executable policy produces 247 incremental approvals rather than the page's
350-person scenario target; the artifact preserves the measured simulation
result and does not rewrite it to match that target. Group sample sizes and 95%
Wilson intervals accompany selection rates. The risk constraint, stable reason
code, source identity, allowed use, generation timestamp, code basis, runtime
mean, and runtime standard deviation are machine readable.

The benchmark does not recommend a policy or threshold and does not establish
fairness, legality, business value, or real-world impact.
