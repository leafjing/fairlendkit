#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
release_tmp="$(mktemp -d)"
trap 'rm -rf -- "$release_tmp"' EXIT

python_bin="${PYTHON:-python3}"
"$python_bin" -m venv --without-pip "$release_tmp/venv"
venv_python="$release_tmp/venv/bin/python"
"$python_bin" -m pip --python "$venv_python" install \
  --disable-pip-version-check --no-deps pip==24.2
"$venv_python" -m pip install --disable-pip-version-check \
  -r "$repo_root/requirements-release-build.txt"
"$venv_python" -m pip install --disable-pip-version-check --no-deps \
  -r "$repo_root/requirements-release.txt"
"$venv_python" -m pip install --disable-pip-version-check --no-deps \
  --no-build-isolation "$repo_root"

"$venv_python" --version
"$venv_python" -m pip freeze --all \
  | sed -E 's#^fairlendkit @ .*#fairlendkit==0.1.0.dev0#' \
  | tee "$release_tmp/pip-freeze.txt"
cmp "$repo_root/docs/milestone-3-release-pip-freeze.txt" \
  "$release_tmp/pip-freeze.txt"

"$venv_python" "$repo_root/examples/synthetic/run_audit.py" \
  > "$release_tmp/audit-result-v2.json"
cmp "$repo_root/examples/synthetic/audit-result-v2.json" \
  "$release_tmp/audit-result-v2.json"
actual_hash="$(sha256sum "$release_tmp/audit-result-v2.json" | cut -d' ' -f1)"
expected_hash="$(tr -d '\n' < "$repo_root/examples/synthetic/audit-result-v2.sha256")"
test "$actual_hash" = "$expected_hash"

cd "$repo_root"
"$venv_python" -m pytest -q
"$venv_python" -m pytest -q tests/test_architecture.py
"$venv_python" "$repo_root/scripts/verify_discoverability.py" --installed
git diff --check
