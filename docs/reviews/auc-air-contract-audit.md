# ROC AUC and AIR 0.8 contract audit

Status: **audit complete; corrective implementation required for constant-score ROC AUC**

Audit baseline: `main@1d439eb63dedcf8175438f1148824061e6e85198`

Scope: read-only review of the metric implementation, tests, product contract,
undefined-reason vocabulary, screening gate, and reader-facing interpretation.
This review does not change product code and does not make a legal conclusion.

## Executive conclusion

1. **Constant-score ROC AUC is implemented inconsistently with the repository's
   own pairwise definition.** When both outcome classes have positive weight and
   every eligible score is equal, every favorable/unfavorable pair is a tie.
   Because the documented and implemented pairwise rule assigns `0.5` to a tie,
   ROC AUC is defined as `0.5`, with numerator
   `0.5 * favorable_weight * unfavorable_weight` and denominator
   `favorable_weight * unfavorable_weight`. The current early return of
   `undefined_reason="constant_score"` is therefore not mathematically required
   and contradicts the stated metric definition. No separate product rationale
   was found that justifies overriding the pairwise estimand.
2. **AIR 0.8 is implemented as a reliability-gated screening threshold, not a
   compliance verdict.** That implementation boundary is sound: a flag is
   emitted only for defined, reliable AIR strictly below the configured
   threshold, and equality at `0.8` does not flag. Existing general disclaimers
   also reject automated legal/compliance conclusions.
3. **AIR documentation still needs a more explicit provenance and credit-use
   boundary.** The four-fifths rule comes from the U.S. employment-selection
   Uniform Guidelines. It is a rule of thumb, not a legal definition. In a
   credit audit, `0.8` may be retained only as a configurable triage signal; it
   must not be described as a universal credit-law threshold, a finding of
   discrimination, or a safe harbor. Review must consider the underlying rates,
   effect size, uncertainty, sample size, risk-adjusted/conditional analyses,
   and human legal/compliance judgment.

## Finding AUC-1 — constant scores should return 0.5

Severity: **contract defect**

### Code and test evidence

- `src/fairlendkit/metrics/core.py:205-210` defines ROC AUC as the weighted
  favorable-versus-unfavorable ranking probability.
- `src/fairlendkit/metrics/core.py:242-248` returns undefined
  `constant_score` before applying the tie rule.
- `src/fairlendkit/metrics/core.py:250-281` assigns a contribution of `0.5` to
  equal-score favorable/unfavorable pairs in both the optimized unweighted path
  and the weighted pairwise path.
- `tests/test_metrics.py:142-153` freezes the current undefined behavior for
  `[True, False]` with scores `[0.2, 0.2]`.
- `docs/metric-contracts.md:165-172`,
  `docs/milestone-3-core-audit-engine.md:154-166`, and
  `docs/undefined-reasons.md:28` repeat the undefined-constant-score policy.

### Independent derivation

Let `W+` be the positive total weight for favorable outcomes and `W-` the
positive total weight for unfavorable outcomes. The repository's AUC estimand
is:

```text
sum_{i in favorable, j in unfavorable}
  w_i * w_j * [I(score_i > score_j) + 0.5 I(score_i = score_j)]
----------------------------------------------------------------
                         W+ * W-
```

For a constant score, every pair is tied. The numerator is therefore
`0.5 * W+ * W-`, the denominator is `W+ * W-`, and AUC is exactly `0.5`.
This is true for weighted and unweighted inputs, provided both class weights are
positive. Class absence and zero class weight remain genuinely undefined.

### Required correction

- Remove the constant-score undefined early return.
- Return `MetricValue(0.5, 0.5 * denominator, denominator)` through the normal
  tie calculation or an equivalent exact shortcut.
- Replace the constant-score undefined test with weighted and unweighted golden
  tests asserting value `0.5`, numerator, denominator, and no undefined reason.
- Update the metric contract, milestone contract, FAQ, testing matrix, schema
  fixtures, and undefined-reason catalog. If `constant_score` remains in the
  versioned reason enum for backward parsing, mark it as legacy/non-emitting
  rather than silently deleting schema compatibility.
- Verify group orchestration, bootstrap definedness, report serialization, and
  migration behavior for constant-score populations.

## Finding AIR-1 — implementation is screening-only, but provenance is incomplete

Severity: **documentation boundary gap; no current threshold-code defect found**

### Code and test evidence

- `src/fairlendkit/config/models.py:97-111` makes `0.8` the finite,
  configurable default.
- `src/fairlendkit/metrics/reliability.py:117-133` emits a prompt only when AIR
  is defined, reliable, and strictly below the configured threshold.
- `tests/test_reliability_bootstrap.py:70-106` verifies the default, reliability
  gate, and emitted threshold.
- `src/fairlendkit/report/models.py:730-738` rejects automated legal/compliance
  verdict language.
- `docs/metric-contracts.md:98-114`, `docs/methodology-and-guardrails.md:3-10`,
  `docs/faq.md:37-41`, and `README.md:44-45` correctly call the output a
  screening heuristic or practitioner-review prompt.

### External provenance

The source context is employment selection, not a general credit safe harbor:

- [29 CFR part 1607, Uniform Guidelines on Employee Selection Procedures](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607)
  governs employee-selection procedures.
- [EEOC, Questions and Answers on the Uniform Guidelines, Question 12](https://www.eeoc.gov/laws/guidance/questions-and-answers-clarify-and-provide-common-interpretation-uniform-guidelines)
  describes four-fifths/80% as a **rule of thumb**, says it is **not intended as
  a legal definition**, and illustrates hiring, promotion, and other employment
  selection decisions.
- [12 CFR part 1002 (Regulation B)](https://www.ecfr.gov/current/title-12/chapter-X/part-1002)
  is the relevant federal credit-discrimination regulation. The repository does
  not cite it, or another credit authority, as establishing AIR `0.8` as a
  universal credit-law decision rule.

The audit therefore finds no support for describing `0.8` as a universal legal
threshold, proof of a violation, proof of compliance, or a safe harbor in a
credit setting.

### Required documentation clarification

Reader-facing metric and methodology documents should state together that:

- the default originates in the employment-selection four-fifths rule;
- its FairLendKit credit use is configurable triage only;
- a value below `0.8` does not prove discrimination or illegality;
- a value at or above `0.8`, or the absence of a flag, does not prove fairness,
  compliance, or safety;
- AIR must be accompanied by both group selection rates, group denominators,
  absolute rate difference/effect size, confidence intervals or uncertainty,
  missing/exclusion counts, and reliability limitations;
- interpretation should include predeclared conditional/risk-adjusted analysis,
  overlap and sensitivity checks where appropriate, followed by human review;
  these analyses remain associational and do not by themselves establish cause,
  intent, business necessity, or a legal conclusion.

## Acceptance tests for the corrective slice

1. Constant unweighted scores with both classes return AUC `0.5`.
2. Constant weighted scores with positive weight in both classes return AUC
   `0.5` with the correct normalized numerator and denominator.
3. A present class with zero total class weight remains undefined with its
   existing class-weight reason.
4. One-class inputs remain undefined with the existing absent-class reason.
5. Constant-score group, bootstrap, JSON, CSV, and HTML paths preserve defined
   `0.5`; legacy payload parsing remains explicit and deterministic.
6. AIR `<0.8` flags only after reliability gates; AIR `==0.8` does not flag.
7. AIR output and documentation prohibit legal verdict/safe-harbor language and
   retain the supporting rates, denominators, uncertainty, and limitations.

## Audit disposition

- **AUC:** corrective code, test, and documentation change required.
- **AIR implementation:** retain the configurable reliability-gated screen.
- **AIR documentation:** add authoritative provenance and the credit-specific
  interpretation boundary before presenting `0.8` outside technical contracts.
