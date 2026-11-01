# Frequently asked questions

## What is FairLendKit?

FairLendKit is a reproducible fair-lending audit toolkit for credit decisioning
systems. Its current Python core validates audit semantics, computes group and
reference-comparison metrics, represents reliability and undefined states,
estimates eligible uncertainty intervals, produces gated screening flags, and
serializes a typed Schema 2.0 audit result.

## Who is it for?

The intended users are model validators, responsible-AI teams, quantitative
risk practitioners, data scientists, auditors, and researchers who understand
their datasets and can explicitly configure outcome, score, decision, group,
and reference semantics.

## Does it determine whether a lender or model is fair or lawful?

No. FairLendKit produces statistical evidence for human review. It does not
determine discrimination, intent, business necessity, fairness, legality, or
regulatory compliance, and it does not provide legal advice.

## What does `reliable` mean?

It means that a defined metric passed the documented metric-specific support
gates. It does not mean that the data are unbiased, representative, causal, or
free of measurement and dataset-shift risk.

## Why can a metric be undefined or not applicable?

A denominator may be zero, a required outcome class may be absent, a score may
be constant, or a metric may not apply to the configured scope. FairLendKit
preserves these cases explicitly rather than converting them into zero or
silently dropping them.

## Is the four-fifths rule a compliance test?

No. The adverse impact ratio threshold is used only as a screening heuristic.
The current flag is emitted only when the ratio is defined and the two source
selection rates pass their reliability gates.

## Is the output reproducible?

The checked-in synthetic example fixes its input, configuration, timestamp,
bootstrap seed, serialization, and SHA-256 oracle. The release verifier checks
byte-identical output under the supported locked environments. Real audit
reproducibility still depends on preserving the exact input data and config.

## Does FairLendKit include threshold optimization or mitigation?

No. Milestone 5 is implementing a descriptive scan of explicitly configured
candidate thresholds and a fairness-accuracy frontier, but it will not optimize,
recommend, or deploy a threshold. Mitigation, reweighing, threshold
recommendations, and model retraining remain outside the implemented core.

## How should I interpret a threshold scan?

Each candidate applies the configured inclusive score direction to the same
validated audit population, then recomputes counterfactual decision metrics.
The ordinary audit still uses its configured observed or derived decision
source. A frontier point shows a non-dominated trade-off among the contract's
fixed accuracy and disparity axes; it does not mean “best,” “fair,” lawful, or
appropriate for production. Undefined and unreliable points remain visible but
are ineligible for the frontier.

## Does it provide HTML reports, CSV reports, or a CLI?

Yes. The `fairlendkit audit` command writes canonical JSON, metrics CSV, and a
self-contained HTML report from one typed audit result. These formats present
the same analysis and do not independently recompute metrics.

## How should I cite it?

Use the repository's `CITATION.cff` and include the exact version or commit.
Do not cite a changing `main` branch as if it were an immutable research
release. See [Citation and research relationship](citation-and-research.md).
