# FairLendKit

FairLendKit is an open-source framework for reproducible group-level audit evidence
for credit underwriting models.

The project is designed for reproducible practitioner review using public or synthetic data. It does not determine legal compliance and does not provide legal advice.

## Implemented capability

The current pre-alpha core accepts one pandas `DataFrame` and one immutable
`AuditConfig` through `run_audit(data, config)`. It provides:

- layered structural, semantic, reliability, and data-quality validation;
- deterministic overall and single-protected-attribute group metrics;
- explicit directed reference comparisons;
- typed undefined, not-applicable, unreliable, and reliable states;
- deterministic SHA-256 counter bootstrap intervals;
- reliability-gated adverse-impact-ratio screening prompts;
- renderer-neutral `AuditResult` Schema 2.0 JSON serialization; and
- a strict Schema 1.0 parser with explicit lossless 1.0-to-2.0 migration.

The engine does not make fairness, legal, or compliance determinations. A
screening flag is a prompt for practitioner review, not a pass/fail result.

## Quick start

Install the package and test dependencies from a checkout:

```bash
python -m pip install -e '.[test]'
```

Run the checked-in synthetic example:

```bash
python examples/synthetic/run_audit.py > audit-result-v2.json
```

The script uses a fixed execution timestamp, bootstrap seed, configuration, and
synthetic rows. Repeated runs in the same supported environment produce the same
compact canonical JSON. The result fingerprint intentionally includes dataframe row
order, index, columns, and dtypes.

The release-gate SHA-256 of the exact example stdout, including its final
newline, is:

```text
0f6e4daac8592661eaf32a5ccb4f5d445de568596521a81b843cc2a3f49668c3
```

From a clean checkout, this one command creates an isolated environment,
installs the package, runs the full suite, checks architecture boundaries and
whitespace, and reproduces the example digest:

```bash
python -m venv .venv && .venv/bin/python -m pip install -e '.[test]' && \
  .venv/bin/python -m pytest -q && \
  .venv/bin/python -m pytest -q tests/test_architecture.py && \
  git diff --check && \
  test "$(.venv/bin/python examples/synthetic/run_audit.py | sha256sum | cut -d' ' -f1)" = \
    "$(tr -d '\n' < examples/synthetic/audit-result-v2.sha256)"
```

The command exits non-zero if generation differs from the checked-in digest.
CI runs the full suite on Python 3.11 and 3.12.

Programmatic use starts with:

```python
from fairlendkit import AuditConfig, AuditResult, run_audit

result: AuditResult = run_audit(data, config)
payload = result.model_dump_json()
```

See [`examples/synthetic/run_audit.py`](examples/synthetic/run_audit.py) for a
complete configuration and dataframe. The existing
[`audit-result.json`](examples/synthetic/audit-result.json) is retained as the
Schema 1.0 compatibility and migration fixture; it is not current writer output.

## Explicitly not implemented

The following remain future milestones and are not exposed by the current core:

- threshold scanning or a fairness-accuracy frontier;
- HTML or CSV renderers and a user-facing JSON renderer;
- a CLI or notebook workflow;
- proxy-risk screening;
- governance integration or investigation lifecycle tooling; and
- mitigation, reweighing, threshold recommendations, or model retraining.

See the [Product brief](docs/product-brief.md), [Product requirements](docs/product-requirements.md), [Canonical glossary](docs/glossary.md), [Architecture](docs/architecture.md), [Metric contracts](docs/metric-contracts.md), [Undefined reasons](docs/undefined-reasons.md), [Report schema](docs/report-schema.md), [Methodology and guardrails](docs/methodology-and-guardrails.md), and [Roadmap](docs/roadmap.md).

Implementation is tracked as ordered, testable work packages in the
[V1 implementation plan](docs/implementation-plan.md).

## Status

Pre-alpha. Milestone 3 core audit engine and reliability contracts are
implemented and tested on Python 3.11 and 3.12. Reporting surfaces and the
remaining V1 workflow are still under development.

## Milestone 3 release evidence

- Public entry point: `run_audit(data, config)` from the package root.
- Current writer: strict `AuditResult` Schema 2.0.
- Compatibility: strict Schema 1.0 parser and explicit lossless migration.
- Determinism: fixed synthetic input, config, timestamp, seed, JSON order, and
  SHA-256 oracle above.
- Architecture: application orchestration is adapter-neutral; pandas and the
  concrete bootstrap estimator are composed only at the outer API boundary.
- Runtime gate: full tests on Python 3.11 and 3.12 plus `git diff --check`.
- Scope gate: repository exports no CLI, HTML/CSV renderer, threshold scan,
  proxy screening, governance integration, or mitigation workflow.
