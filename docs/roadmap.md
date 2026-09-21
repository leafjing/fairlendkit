# Roadmap

## Phase 0 — Contracts and evidence baseline

- Finalize terminology, input schema, and report schema
- Create synthetic data specification
- Define hand-calculated metric fixtures
- Record architecture decisions and citation requirements

## V1 — Reproducible audit workflow

1. Structural and semantic validation, including explicit population, label,
   score, decision, reference-group, and unknown-value treatment
2. Data-quality observations covering missingness by group, sample sufficiency,
   unexpected categories, freshness, and version/distribution change where a
   baseline is available
3. A small, well-tested core of performance, selection, error, calibration, and
   disparity metrics with counts, uncertainty, and applicability guidance
4. Robust handling of small groups, imbalance, sparse outcomes, zero
   denominators, invalid inputs, and undefined or unreliable metrics
5. Threshold scanning and fairness-accuracy frontier
6. Layered HTML, JSON, and CSV reporting from one typed result model: executive
   summary, reviewer detail, transparent screening flags, and audit trail
7. Non-prescriptive investigation prompts and an integration contract for human
   ownership, disposition, remediation, and monitoring records
8. Exploratory screening for potential proxy-risk indicators
9. Synthetic end-to-end example and public-data example with documented
   limitations and realistic practitioner interpretation
10. Packaging, CI, documentation, contribution guide, and citation metadata

V1 prioritizes correctness, transparency, reproducibility, and usability before
breadth. A metric or flag is not release-ready until its semantics, applicability,
edge cases, tests, report representation, and limitations are documented.

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
