#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Milestone 4 is cumulative: retain every locked Milestone 3 check and add the
# user-workflow artifact gate maintained by that verifier.
"$repo_root/scripts/verify_milestone3_release.sh"
