#!/usr/bin/env bash
set -euo pipefail

: "${PR:?set reviewed PR number}"
: "${REVIEWED_MAIN_SHA:?set reviewed main SHA}"
: "${REVIEWED_RELEASE_SHA:?set reviewed release SHA}"

CURRENT_MAIN_SHA=$(git rev-parse origin/main)
test "$CURRENT_MAIN_SHA" = "$REVIEWED_MAIN_SHA"

gh pr checks "$PR" --watch --fail-fast
PR_STATE=$(gh pr view "$PR" --json headRefOid,reviewDecision,mergeStateStatus)
BASE_REF_OID=$(gh api "repos/{owner}/{repo}/pulls/$PR" --jq .base.sha)
test "$(printf '%s' "$PR_STATE" | jq -r .headRefOid)" = "$REVIEWED_RELEASE_SHA"
test -n "$BASE_REF_OID"
test "$BASE_REF_OID" = "$REVIEWED_MAIN_SHA"
test "$(printf '%s' "$PR_STATE" | jq -r .reviewDecision)" = "APPROVED"
test "$(printf '%s' "$PR_STATE" | jq -r .mergeStateStatus)" = "CLEAN"

gh pr merge "$PR" --merge --delete-branch=false --match-head-commit "$REVIEWED_RELEASE_SHA"
