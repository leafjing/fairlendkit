# Citation and research relationship

## Citing the software

Use the repository's [`CITATION.cff`](../CITATION.cff) and pin the exact release
or commit used. The current package version is pre-alpha and no DOI is asserted
by this repository. When an immutable DOI-backed release exists, its release
record should take precedence over a moving branch URL.

A citation should identify:

- FairLendKit and its software version or commit SHA;
- the repository URL;
- the audit configuration and schema version;
- the environment lock used for reproduction; and
- any separate research artifact, dataset, or paper release on which a result
  depends.

## Method summary suitable for citation

FairLendKit is an open-source Python toolkit that produces reproducible,
group-level audit evidence for credit decisioning systems. It validates explicit
outcome, score, decision, group, and reference semantics; computes documented
metrics and directed comparisons; preserves undefined and reliability states;
attaches deterministic uncertainty where eligible; and serializes a typed,
renderer-neutral audit record. Statistical flags are review prompts rather than
legal or normative conclusions.

## Software versus paper evidence

The product repository contains stable software contracts, implementation,
tests, examples, and release evidence. A paper may use a separate research
artifact containing frozen datasets, simulations, analysis scripts, and
results. A software milestone is therefore not automatically a paper release,
and research-only results must not be described as implemented product
capabilities.

Each paper-grade artifact should pin the FairLendKit release it uses and provide
its own immutable tag, environment, data manifest and licenses, random seeds,
one-command reproduction path, checked results or hashes, and DOI when
available.
