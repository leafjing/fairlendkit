#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
release_tmp="$(mktemp -d)"
trap 'rm -rf -- "$release_tmp"' EXIT

python_bin="${PYTHON:-python3}"
release_site="$release_tmp/site-packages"
"$python_bin" -m pip install --disable-pip-version-check --target "$release_site" \
  -r "$repo_root/requirements-release.txt"
"$python_bin" -m pip install --disable-pip-version-check --target "$release_site" \
  --no-deps "$repo_root"

PYTHONPATH="$release_site" "$python_bin" "$repo_root/examples/synthetic/run_audit.py" \
  > "$release_tmp/audit-result-v2.json"
cmp "$repo_root/examples/synthetic/audit-result-v2.json" \
  "$release_tmp/audit-result-v2.json"
actual_hash="$(sha256sum "$release_tmp/audit-result-v2.json" | cut -d' ' -f1)"
expected_hash="$(tr -d '\n' < "$repo_root/examples/synthetic/audit-result-v2.sha256")"
test "$actual_hash" = "$expected_hash"

cd "$repo_root"
PYTHONPATH="$release_site" "$python_bin" -m pytest -q
PYTHONPATH="$release_site" "$python_bin" -m pytest -q tests/test_architecture.py
git diff --check
