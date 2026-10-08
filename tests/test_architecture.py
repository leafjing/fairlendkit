"""Dependency-direction checks for stable inner contracts."""

from __future__ import annotations

import ast
from pathlib import Path


def test_domain_contracts_do_not_import_outer_layers():
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

    forbidden_roots = {"pandas", "fairlendkit.cli", "fairlendkit.report", "storage"}
    qualified_imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert imports.isdisjoint({"pandas", "storage"})
    assert not any(
        imported == forbidden or imported.startswith(f"{forbidden}.")
        for imported in qualified_imports
        for forbidden in forbidden_roots
    )


def test_group_orchestration_is_dataframe_and_io_independent():
    source = Path("src/fairlendkit/metrics/group.py").read_text()
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported_modules.update(
        name.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    )

    forbidden = {"pandas", "numpy", "fairlendkit.cli", "fairlendkit.report"}
    assert not any(
        module == root or module.startswith(f"{root}.")
        for module in imported_modules
        for root in forbidden
    )
