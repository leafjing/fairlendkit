# Contributing to FairLendKit

FairLendKit uses an issue-driven pull-request workflow. Every material change starts with a GitHub issue and ends with an independently reviewed pull request.

## Workflow

1. Open or select an issue with acceptance criteria and an owner role.
2. Create a branch from current `main`:
   - `feat/<issue>-<slug>`
   - `fix/<issue>-<slug>`
   - `docs/<issue>-<slug>`
   - `chore/<issue>-<slug>`
3. Keep commits focused and reference the issue.
4. Open a pull request using the repository template.
5. Update tests and documentation in the same pull request when behavior changes.
6. Resolve review findings with additional commits; do not hide review history by rewriting shared branches.
7. Squash-merge only after required checks and review pass.

Direct feature commits to `main` are not part of the development workflow.

## Roles

- Architect: requirements, architecture decisions, scope, risk escalation, and cross-artifact consistency
- Documenter: user and methodology documentation, citations, terminology, examples, and changelog quality
- Programmer: implementation, tests, developer notes, and issue-level technical evidence
- Reviewer: independent code and methodology review, test verification, and merge readiness

The implementer may not self-approve a pull request.

## Definition of done

- Linked issue and satisfied acceptance criteria
- Automated tests for behavioral changes
- Documentation updated with the code
- No proprietary or confidential data or intellectual property
- Metric semantics and limitations are explicit
- Reviewer approval and passing CI
- Changelog or release note when user-visible

## Methodology changes

Changes to metric definitions, threshold interpretation, proxy-risk logic, uncertainty, report language, or label semantics require an ADR under `docs/decisions/` and must identify affected paper claims.

