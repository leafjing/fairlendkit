# Development Workflow

## Governance

FairLendKit follows an issue-to-branch-to-pull-request-to-review workflow. `main` represents reviewed, releasable project history.

## Responsibility flow

1. Architect defines scope, contracts, dependencies, risks, and acceptance criteria in an issue.
2. Documenter verifies terminology, methodology explanations, citations, examples, and paper alignment.
3. Programmer implements on an issue branch with tests and documentation.
4. Reviewer independently checks correctness, regression risk, methodology boundaries, and CI evidence.
5. Architect confirms cross-project consistency and closes the milestone gap.

## Issue states

- `status:triage`: incomplete or awaiting prioritization
- `status:ready`: scoped and unblocked
- `status:in-progress`: an owner is actively working
- `status:review`: pull request is open
- `status:blocked`: requires a documented dependency or decision
- `status:done`: acceptance criteria are verified

## Priority

- `priority:P0`: correctness, security, privacy, confidential-data, or materially misleading report issue
- `priority:P1`: release-critical capability or regression
- `priority:P2`: planned improvement
- `priority:P3`: backlog

## Escalation rules

Open or update an issue immediately when implementation reveals an ambiguous label meaning, a metric-definition conflict, unreliable statistical behavior, a data-rights concern, misleading compliance language, or a mismatch with paper claims. Do not silently work around these problems in code.

