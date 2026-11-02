#!/usr/bin/env bash
set -euo pipefail

: "${CURRENT_MAIN_SHA:?set current main SHA}"
: "${REVIEWED_MAIN_SHA:?set reviewed main SHA}"
: "${REVIEWED_RELEASE_SHA:?set reviewed release SHA}"
: "${PR_STATE:?set PR state JSON}"

test "$CURRENT_MAIN_SHA" = "$REVIEWED_MAIN_SHA"
test "$(printf '%s' "$PR_STATE" | jq -r .headRefOid)" = "$REVIEWED_RELEASE_SHA"
test "$(printf '%s' "$PR_STATE" | jq -r .baseRefOid)" = "$REVIEWED_MAIN_SHA"
test "$(printf '%s' "$PR_STATE" | jq -r .reviewDecision)" = "APPROVED"
test "$(printf '%s' "$PR_STATE" | jq -r .mergeStateStatus)" = "CLEAN"
