# Product Brief

## Product summary

FairLendKit is an open-source, credit-specific audit framework for examining group outcome disparities, model-performance disparities, decision-threshold sensitivity, and potential proxy-risk indicators. It turns an explicitly configured dataset and model semantics into reproducible, review-ready technical evidence.

FairLendKit exists because general-purpose fairness libraries expose useful metrics but do not, by themselves, provide the semantic checks, credit-specific workflow, uncertainty context, provenance, and reporting boundaries needed for a defensible practitioner review. The project connects those pieces without turning a statistical screen into a legal conclusion.

## Intended users

- Fintech and lending model-risk teams conducting pre-deployment or periodic review
- Fair-lending and compliance practitioners working with technical teams and counsel
- Credit unions and lending startups that need a reproducible audit workflow
- Academic researchers studying responsible credit underwriting with public or synthetic data

Users are expected to understand their data, choose the audit groups and reference group, and explicitly configure outcome, score, and decision semantics. FairLendKit does not infer those meanings.

## V1 user outcome

Given an eligible dataset and an explicit audit configuration, a practitioner can run one documented command and receive consistent HTML, JSON, and CSV evidence containing:

- validated run semantics and provenance;
- overall and group-level observed metrics;
- threshold-sensitivity results;
- potential proxy-risk indicators;
- sample sizes, statistical uncertainty, warnings, and limitations; and
- fields suitable for independent review and reproducibility.

V1 measures and reports. Mitigation experiments and before/after re-auditing are deferred to V1.1.

## Differentiators

- **Credit-specific semantics:** favorable outcome, score direction, decision meaning, audit groups, and reference group are explicit and validated.
- **Evidence, not verdicts:** observed metrics, screening flags, uncertainty, limitations, and practitioner notes remain separate. Automated reports do not declare legal compliance.
- **Reproducibility:** outputs preserve configuration, input fingerprint, package version, execution time, warnings, and metric definitions.
- **Complete review artifact:** threshold analysis and proxy-risk screening use the same validated inputs and typed result model as the primary group analysis.
- **Publicly verifiable examples:** committed examples use public, appropriately licensed, or synthetic data and document their limitations.

## Non-goals

FairLendKit does not:

- determine whether conduct or a model is compliant, non-compliant, legal, or illegal;
- provide legal advice or replace fair-lending counsel or a complete model-risk process;
- establish causation, intent, business necessity, or the availability of a less-discriminatory alternative;
- serve as a production loan-decision engine;
- infer protected attributes for operational lending decisions;
- recommend group-specific production thresholds; or
- process or distribute Capital One confidential or proprietary data, models, artifacts, code, or documentation.

## Endeavor and paper alignment

The Endeavor narrative and project evidence must describe the same product defined here: an independent, open-source, reproducible practitioner audit framework. Claims should be supported by public artifacts such as versioned releases, reproducible examples, substantive issues, independent contributions, citations, or documented practitioner use with permission. Repository activity or adoption must not be overstated.

Paper A defines and evaluates the V1 practitioner framework. Its terminology, metric definitions, experimental configuration, report fields, and stated limitations must match the released implementation. Paper B uses the framework in a synthetic or public cash-flow underwriting study; it is an empirical application, not a separate implementation contract. Mitigation research builds on V1.1 and must not be presented as a V1 capability.

When an Endeavor statement, paper claim, or implementation behavior conflicts with the canonical documentation, the conflict must be raised in an issue. A methodological or architectural resolution requires an ADR and synchronized updates to affected artifacts.

## Success measures

### V1 release readiness

- One versioned synthetic example generates `audit.html`, `audit.json`, `metrics.csv`, and `threshold_frontier.csv` from a documented command.
- Hand-calculated fixtures verify metric direction, favorable-label behavior, and reference-group comparisons.
- Key disparity results include group sample sizes and configured uncertainty; small or undefined comparisons produce explicit warnings or suppression.
- HTML, JSON, and CSV values are derived from one typed result model and remain mutually consistent.
- A public-data case study is reproducible and states its data, missingness, and inference limitations.

### Adoption evidence

- Reproducible third-party uses or examples
- Substantive external issues and independently reviewed contributions
- Citations or documented practitioner use, shared only with permission

Stars, downloads, and repository traffic may be reported as context, but they are not sufficient evidence of practitioner impact.

## Canonical references

- [Product requirements](product-requirements.md)
- [Canonical glossary](glossary.md)
- [Architecture](architecture.md)
- [Methodology and guardrails](methodology-and-guardrails.md)
- [Roadmap](roadmap.md)

