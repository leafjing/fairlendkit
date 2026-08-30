# ADR 0001: Project name and V1 scope

- Status: Accepted
- Date: 2026-08-30

## Decision

The project and Python package are named `FairLendKit` and `fairlendkit`. V1 delivers metrics, threshold analysis, exploratory screening for potential proxy-risk indicators, and reproducible audit reports. Mitigation is deferred to V1.1.

## Rationale

The scope supports the practitioner-framework paper while keeping the first release focused on a complete, testable audit workflow. Deferring mitigation prevents measurement and intervention from being conflated before the evidence and review contracts are stable.

## Consequences

- V1 reports observations and screening indicators, not compliance conclusions.
- The repository must use only public, appropriately licensed, or synthetic data.
- Future scope changes require a new ADR and corresponding updates to requirements, methodology, tests, and paper alignment.
