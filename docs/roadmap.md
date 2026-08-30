# Roadmap

## Phase 0 — Contracts and evidence baseline

- Finalize terminology, input schema, and report schema
- Create synthetic data specification
- Define hand-calculated metric fixtures
- Record architecture decisions and citation requirements

## V1 — Reproducible audit workflow

1. Configuration and data validation
2. Performance, selection, error, and calibration metrics
3. Threshold scanning and fairness-accuracy frontier
4. Exploratory proxy-risk screening
5. HTML, JSON, and CSV reporting
6. Synthetic end-to-end example
7. Public-data example with documented limitations
8. Packaging, CI, documentation, contribution guide, and citation metadata

## V1.1 — Mitigation experiments

- Reweighing
- Threshold-policy simulation
- Fairness-constrained modeling experiments
- Before/after re-audit comparison

Mitigation features remain research and review tools, not production decision recommendations.

## Paper alignment

- Paper A defines and evaluates the practitioner audit framework implemented by V1.
- Paper B applies the framework to a synthetic/public cash-flow underwriting study and maps the fairness-accuracy frontier.
- Debiasing work builds on V1.1 and may become a later workshop paper.

## Adoption evidence

The project will prioritize a small number of verifiable external uses over vanity metrics. Evidence may include reproducible third-party examples, substantive issues, external contributions, citations, and documented practitioner use with permission.

## Change management

- Material architectural or methodological decisions receive an ADR in `docs/decisions/`.
- Behavioral changes require tests and documentation in the same pull request.
- Methodology changes must identify affected paper claims and report fields.
- Security, legal-interpretation, data-rights, or label-semantics concerns block release until reviewed.

