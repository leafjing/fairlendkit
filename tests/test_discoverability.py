"""Repository discoverability metadata and navigation checks."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_discoverability", ROOT / "scripts/verify_discoverability.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY_MODULE)
verify_links = VERIFY_MODULE.verify_links
verify_metadata = VERIFY_MODULE.verify_metadata


def test_discoverability_metadata_and_links_are_consistent():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_discoverability.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "discoverability metadata and links verified"


def test_recursive_link_check_covers_contributing_nested_docs_and_fragments(tmp_path):
    (tmp_path / "README.md").write_text("[nested](docs/decisions/note.md#valid-heading)\n")
    (tmp_path / "CONTRIBUTING.md").write_text("[readme](README.md)\n")
    (tmp_path / "llms.txt").write_text("[index](docs/index.md)\n")
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "index.md").write_text("# Index\n")
    (tmp_path / "docs" / "decisions" / "note.md").write_text("# Valid heading\n")

    verify_links(tmp_path)


@pytest.mark.parametrize(
    ("source", "target", "message"),
    (
        ("CONTRIBUTING.md", "missing.md", "Broken internal link"),
        ("docs/decisions/note.md", "../index.md#missing-heading", "Broken heading anchor"),
    ),
)
def test_recursive_link_check_fails_closed(source, target, message, tmp_path):
    (tmp_path / "README.md").write_text("# Readme\n")
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n")
    (tmp_path / "llms.txt").write_text("docs\n")
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "index.md").write_text("# Index\n")
    (tmp_path / "docs" / "decisions" / "note.md").write_text("# Note\n")
    path = tmp_path / source
    path.write_text(path.read_text() + f"[broken]({target})\n")

    with pytest.raises(SystemExit, match=message):
        verify_links(tmp_path)


def _metadata_fixture(tmp_path):
    (tmp_path / "docs").mkdir()
    for relative in (
        "pyproject.toml",
        "codemeta.json",
        "CITATION.cff",
        "LICENSE",
        "README.md",
        "docs/software-source-code.template.jsonld",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


@pytest.mark.parametrize(
    ("relative", "field", "value", "message"),
    (
        ("codemeta.json", "license", "https://example.invalid/license", "license metadata"),
        ("codemeta.json", "runtimePlatform", ["Python 3.12"], "Python runtimes"),
        ("codemeta.json", "keywords", ["fair lending"], "keywords"),
    ),
)
def test_metadata_cross_validation_fails_closed(relative, field, value, message, tmp_path):
    _metadata_fixture(tmp_path)
    path = tmp_path / relative
    payload = json.loads(path.read_text())
    payload[field] = value
    path.write_text(json.dumps(payload))

    with pytest.raises(SystemExit, match=message):
        verify_metadata(tmp_path)
