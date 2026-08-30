# Architecture

## Design principles

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
- Protected attribute and explicit reference group
- Minimum group size and confidence interval settings
- Candidate proxy features
- Output formats and run metadata

`AuditResult` contains typed sections for validation, overall performance, group outcomes, group errors, calibration, thresholds, proxy screening, uncertainty, warnings, and limitations.

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
CLI -> orchestration -> validation -> analysis components -> AuditResult -> renderers
```

Analysis components cannot depend on HTML templates or notebook code.

## Testing strategy

- Unit tests against hand-calculated metric fixtures
- Property tests for bounds and invariants where useful
- Golden-file tests for the versioned synthetic report
- Integration test for the complete CLI workflow
- Regression tests for label direction and reference-group reversals

