# Limitations and responsible use

FairLendKit structures reproducible statistical evidence; it does not replace
domain expertise, legal review, data governance, model validation, or a
human-owned investigation process.

## Interpretation limits

- Group differences and ratios are descriptive and do not identify causation,
  intent, discrimination, or legal non-compliance.
- A reliability gate addresses specified support conditions only. Passing it
  does not establish representativeness, correctness, calibration, or absence
  of bias.
- Bootstrap intervals describe sampling variability under the implemented
  procedure, not all uncertainty in the data or decision system.
- Results depend on configured outcome, favorable label, score direction,
  decision, favorable decision, audit groups, and reference group.
- Small, imbalanced, sparse, or missing-data populations can produce undefined,
  unreliable, or unstable evidence.

## Data and scope limits

- Users remain responsible for lawful data access, permissions, privacy,
  retention, and appropriate use of protected or sensitive attributes.
- The current core supports one protected attribute per audit execution; it
  does not claim to cover intersectional or causal analysis.
- Dataset shift, label bias, measurement error, selection bias, historical
  inequity, and omitted variables require analysis outside the metric engine.
- Public and synthetic examples demonstrate mechanics and reproducibility; they
  do not validate a production lender or establish external validity.

## Capabilities not currently implemented

The current core does not include threshold scanning, fairness-performance
frontiers, HTML/CSV renderers, a CLI, proxy-risk screening, governance workflow
integration, mitigation, threshold recommendations, reweighing, or model
retraining. Consult the [Roadmap](roadmap.md) before interpreting a planned
feature as available.

## Safe communication

Describe outputs as metrics, uncertainty intervals, reliability states,
limitations, and screening flags. Do not automatically label a model, feature,
group, or institution as fair, unfair, compliant, non-compliant, legal, or
illegal from FairLendKit output alone.
