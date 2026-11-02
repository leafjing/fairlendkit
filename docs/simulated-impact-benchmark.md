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

The required `evidence_class` field carries that exact value. A machine-
readable configuration summary also states that baseline and tool use the same
sample, outcome label, time window, risk rule, pre-decision credit amounts, and
group definition.

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
The executable policy produces 87 incremental approvals rather than the page's
350-person scenario target; the artifact preserves the measured simulation
result and does not rewrite it to match that target. Consequently the candidate
publication copy remains locked with reason code
`impact_risk_noninferiority_failed`: the observed approved bad rate increases
under the zero-tolerance contract. Group sample sizes and 95%
Wilson intervals accompany selection rates. The risk constraint, stable reason
code, source identity, allowed use, generation timestamp, code basis, runtime
mean, and runtime standard deviation are machine readable.

The artifact also freezes the canonical-input SHA-256, baseline and tool
approved-ID set digests, the synthetic outcome definition and observation
window, zero risk tolerance, and expected-versus-actual approval and group-gap
values. Targets are assertions, never inputs to the decision functions.

The internal evidence class remains unchanged. The machine-readable external
copy candidate uses the reader-facing terms “固定样本量化评估”, “预计”, and
“测算”, carries a production-pilot disclaimer, and avoids claims of realized
customer impact. It reports the derived 87 approvals—not the unreproduced
350-person expectation—and remains locked while the publication gate fails.

The benchmark does not recommend a policy or threshold and does not establish
fairness, legality, business value, or real-world impact.
