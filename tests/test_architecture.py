"""Dependency-direction checks for stable inner contracts."""

from __future__ import annotations

import ast
from pathlib import Path


def test_domain_contracts_do_not_import_pandas():
    source = Path("src/fairlendkit/data/contracts.py").read_text()
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert "pandas" not in imports
