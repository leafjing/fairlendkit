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


def test_metrics_package_does_not_depend_on_report_package():
    for source_path in Path("src/fairlendkit/metrics").glob("*.py"):
        tree = ast.parse(source_path.read_text())
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

        assert not any(
            module == "fairlendkit.report"
            or module.startswith("fairlendkit.report.")
            for module in imported_modules
        ), f"{source_path} imports the outer report package"


def test_reliability_policy_does_not_depend_on_bootstrap_implementation():
    tree = ast.parse(Path("src/fairlendkit/metrics/reliability.py").read_text())
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "fairlendkit.metrics.bootstrap" not in imported_modules


def test_product_packages_do_not_depend_on_research_artifacts():
    for source_path in Path("src/fairlendkit").glob("**/*.py"):
        if "research" in source_path.parts:
            continue
        tree = ast.parse(source_path.read_text())
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
        assert not any(
            module == "fairlendkit.research"
            or module.startswith("fairlendkit.research.")
            for module in imported_modules
        ), f"{source_path} imports research-only code"


def test_paper2_execution_gate_cannot_compute_dgp_or_statistics():
    source = Path("src/fairlendkit/research/paper2/execution.py").read_text()

    assert "paper2.dgp" not in source
    assert "paper2.statistics" not in source
