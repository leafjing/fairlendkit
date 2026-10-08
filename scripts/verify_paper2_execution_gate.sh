#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if find . -path './.git' -prune -o -type f \
  \( -iname '*confirmatory*result*' -o -iname '*production*result*' \) \
  -print -quit | grep -q .; then
  echo "confirmatory or production result artifact found" >&2
  exit 1
fi

./scripts/verify_paper2_phase1.sh

base_ref="main"
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  base_ref="origin/$GITHUB_BASE_REF"
fi
merge_base="$(git merge-base HEAD "$base_ref")"
git diff --check "$merge_base"..HEAD
