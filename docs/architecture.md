# Architecture

## Design principles

- Dependencies point from frequently changing details toward stable abstractions.
  Domain contracts must not depend on CLI, dataframe, rendering, storage, or
  integration implementations.
- Concrete adapters implement inward-facing protocols. Core use cases accept
  abstractions through explicit composition and never import outward adapters.
- Credit-specific semantics are explicit, validated, and recorded.
- Core logic lives in a tested Python package; notebooks are demonstration clients.
- Every reported value is traceable to configuration, data fingerprint, and metric definition.
- Findings are separated from screening flags, uncertainty, limitations, and reviewer notes.
- Public APIs remain small while internal metric and reporting components remain extensible.

## Proposed package layout

```text
src/fairlendkit/
  config/       Typed audit configuration and semantic validation
  data/         Input schemas, validation, fingerprints, public/synthetic loaders
  metrics/      Performance, selection, error, calibration, and group metrics
  thresholds/   Threshold scan and frontier construction
  proxy/        Exploratory feature-association and predictability screening
  report/       Report model, renderers, templates, and exports
  cli.py        Command-line interface
```

Mitigation becomes a separate `mitigation/` package in V1.1 so V1 does not blur measurement and intervention.

## Core domain model

`AuditConfig` records:

- Outcome column and favorable label
- Score column and score direction
- Optional decision column or configured threshold
- Protected attributes, type-sensitive allowed categories, explicit reference
  groups, and separate missing/unknown policies
- Minimum group size and confidence interval settings
- Candidate proxy features
- Output formats and run metadata

`AuditResult` contains typed sections for validation, overall performance, group outcomes, group errors, calibration, thresholds, proxy screening, uncertainty, warnings, limitations, and review prompts.

Validation results are layered so a technical pass cannot be mistaken for
fitness for use:

1. Structural validity: columns, types, allowed values, uniqueness, ranges, and
   missingness policy.
2. Semantic validity: outcome and decision meaning, score direction, population,
   reference group, threshold semantics, and unknown-group treatment.
3. Analytical reliability: sample sufficiency, class support, zero denominators,
   estimability, and uncertainty.
4. Data-quality observations: freshness, distribution shifts, missingness by
   group, anomalous values, and model/dataset-version changes when comparison
   metadata is supplied.

All four entries are mandatory in canonical order and use derived `passed`,
`warning`, `failed`, or `not_evaluated` statuses. Overall status does not encode
applicability: Epic 1.4 records it as `not_assessed` and requires practitioner
review. See the normative
[`epic-1.4-layered-validation-results.md`](epic-1.4-layered-validation-results.md).

The domain-owned validation contract represents group-category declarations,
eligibility decisions, stable issue/reason codes, per-reason counts, and the
de-duplicated excluded total using framework-neutral types. Missing means null/NA;
unknown means a non-null value outside the declared allowed set. Concrete
dataframe adapters detect those conditions and implement an eligibility mask,
but cannot choose categories, normalize values, change policy, or define reason
codes. This keeps pandas-specific null detection and masking dependent on the
stable semantic contract rather than making domain semantics depend on pandas.

Reference-group validation spans both boundaries: the domain configuration
requires the reference to be in the allowed set, while the input adapter supplies
evidence that it remains present after the composed eligibility rules. The use
case fails before metrics when either invariant is false.

`ScreeningFlag` records a stable code, severity, transparent rule identifier,
supporting metric references, affected groups, limitations, and suggested human
review prompts. It never records an automated legal or compliance verdict.

`ReviewDisposition`, when imported from a governance workflow, records owner,
status, rationale, evidence references, and timestamps separately from computed
results. This separation preserves the boundary between analysis and decisions.

Renderers consume `AuditResult`; they must not recompute metrics. This keeps HTML, JSON, and CSV mutually consistent.

## CLI contract

```bash
fairlendkit audit \
  --data examples/synthetic/credit.csv \
  --config examples/synthetic/audit.yml \
  --output reports/
```

## Dependency direction

```text
CLI / notebooks
      |
      v
application orchestration
      |
      v
domain contracts and use cases
      ^
      |
dataframe / report / storage / governance adapters
```

The domain layer owns stable configuration semantics, validation issue types,
metric contracts, result contracts, and review-lifecycle interfaces. Application
services coordinate domain operations through those contracts. Pandas ingestion,
CLI parsing, HTML/JSON/CSV rendering, persistence, and governance integrations are
replaceable outer adapters.

Outer layers may import inner layers. Inner layers must not import outer layers.
Composition occurs at the CLI or another application entry point. Analysis
components cannot depend on HTML templates, notebook code, storage clients, or
governance systems.

Any necessary dependency inversion uses a small typed protocol owned by the
consumer-side inner layer. A new abstraction requires at least two credible
implementations or a demonstrated test seam; speculative interfaces are avoided.

## Testing strategy

- Unit tests against hand-calculated metric fixtures
- Property tests for bounds and invariants where useful
- Golden-file tests for the versioned synthetic report
- Integration test for the complete CLI workflow
- Regression tests for label direction and reference-group reversals
- Edge-case tests for zero denominators, sparse outcomes, unknown categories,
  outliers, insufficient groups, and undefined or unreliable metrics
- Contract tests ensuring every screening flag exposes its rule and evidence
- Golden tests for executive summary, analyst detail, and audit-trail consistency
- Architecture tests that reject imports from domain modules into CLI, renderer,
  storage, dataframe-adapter, or governance-integration modules
- Contract tests that run the same missing/unknown/reference-group fixtures
  through each input adapter and assert identical domain reason codes and counts
