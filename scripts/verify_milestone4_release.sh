#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Milestone 4 is cumulative: retain every locked Milestone 3 check and add the
# user-workflow artifact gate maintained by that verifier.
"$repo_root/scripts/verify_milestone3_release.sh"

base_ref="main"
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  base_ref="origin/$GITHUB_BASE_REF"
fi
merge_base="$(git -C "$repo_root" merge-base HEAD "$base_ref")"
git -C "$repo_root" diff --check "$merge_base"..HEAD
