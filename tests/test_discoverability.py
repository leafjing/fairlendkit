"""Repository discoverability metadata and navigation checks."""

import importlib.util
import json
import re
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
verify_deferred_site_boundary = VERIFY_MODULE.verify_deferred_site_boundary
verify_installed_package = VERIFY_MODULE.verify_installed_package


def test_discoverability_verification_matrix_is_complete():
    matrix = (ROOT / "docs/discoverability-verification-matrix.md").read_text()
    expected_ids = {f"DV-{index:02d}" for index in range(1, 18)}
    rows = [line for line in matrix.splitlines() if re.match(r"^\| `DV-\d{2}` ", line)]
    observed_ids = {re.search(r"`(DV-\d{2})`", row).group(1) for row in rows}

    assert observed_ids == expected_ids
    assert len(rows) == len(expected_ids)

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_discoverability.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    collected_nodes = {line.strip() for line in collected if line.startswith("tests/")}
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        verifier_names = re.findall(r"`(verify_[a-z_]+)`", cells[2])
        test_nodes = re.findall(r"`(tests/test_discoverability\.py::[^`]+)`", cells[3])
        assert verifier_names, row
        assert test_nodes, row
        assert all(callable(getattr(VERIFY_MODULE, name, None)) for name in verifier_names)
        assert set(test_nodes).issubset(collected_nodes)


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
    ids=("broken-link", "broken-anchor"),
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


def test_recursive_link_check_rejects_path_escape(tmp_path):
    (tmp_path / "README.md").write_text("[escape](../outside.md)\n")
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n")
    (tmp_path / "llms.txt").write_text("docs\n")
    (tmp_path / "docs").mkdir()
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n")
    try:
        with pytest.raises(SystemExit, match="Broken internal link"):
            verify_links(tmp_path)
    finally:
        outside.unlink()


def test_duplicate_heading_suffix_fails_closed(tmp_path):
    (tmp_path / "README.md").write_text("[bad](docs/note.md#same-heading-2)\n")
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n")
    (tmp_path / "llms.txt").write_text("docs\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("# Same heading\n# Same heading\n")

    with pytest.raises(SystemExit, match="Broken heading anchor"):
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
        ("codemeta.json", "name", "Wrong", "Software names"),
        ("codemeta.json", "@context", "https://example.invalid", "identity or maintainer"),
        ("codemeta.json", "@type", "Dataset", "identity or maintainer"),
        ("codemeta.json", "maintainer", {}, "identity or maintainer"),
        ("codemeta.json", "author", [], "authors"),
        ("codemeta.json", "version", "9.9", "versions"),
        ("codemeta.json", "codeRepository", "https://example.invalid", "Repository URLs"),
        ("codemeta.json", "issueTracker", "https://example.invalid", "Issue tracker"),
        ("codemeta.json", "description", "Wrong", "descriptions"),
        ("codemeta.json", "developmentStatus", "stable", "development status"),
    ),
    ids=(
        "license",
        "runtime-platform",
        "keywords",
        "name",
        "context",
        "type",
        "maintainer",
        "author",
        "version",
        "repository-url",
        "issue-url",
        "description",
        "development-status",
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


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    (
        ("requires-python = \">=3.11\"", "requires-python = \">=3.12\"", "Requires-Python"),
        (
            '"Programming Language :: Python :: 3.11",',
            '"Programming Language :: Python :: 3.10",',
            "classifiers",
        ),
    ),
    ids=("requires-python", "classifier"),
)
def test_package_metadata_source_fields_fail_closed(field, replacement, message, tmp_path):
    _metadata_fixture(tmp_path)
    path = tmp_path / "pyproject.toml"
    path.write_text(path.read_text().replace(field, replacement))

    with pytest.raises(SystemExit, match=message):
        verify_metadata(tmp_path)


def test_readme_and_cff_positioning_fail_closed(tmp_path):
    _metadata_fixture(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(readme.read_text().replace("FairLendKit is a reproducible", "FairLendKit is an opaque", 1))

    with pytest.raises(SystemExit, match="descriptions"):
        verify_metadata(tmp_path)


def test_duplicate_canonical_links_fail_closed(tmp_path):
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir()
    page.write_text(
        '<link rel="canonical" href="https://example.invalid/one">\n'
        '<link rel="canonical" href="https://example.invalid/two">\n'
    )

    with pytest.raises(SystemExit, match="Duplicate canonical"):
        verify_deferred_site_boundary(tmp_path)


def test_unresolved_jsonld_template_token_fails_closed(tmp_path):
    _metadata_fixture(tmp_path)
    path = tmp_path / "docs/software-source-code.template.jsonld"
    payload = json.loads(path.read_text())
    payload["url"] = "https://example.invalid/docs"
    path.write_text(json.dumps(payload))

    with pytest.raises(SystemExit, match="unresolved canonical-origin token"):
        verify_metadata(tmp_path)


@pytest.mark.parametrize(
    ("relative", "content", "message"),
    (
        ("site/index.html", '<link rel="canonical" href="https://example.invalid">', "approved origin"),
        ("site/index.html", '<meta property="og:title" content="FairLendKit">', "approved origin"),
        ("site/index.html", '<meta name="twitter:card" content="summary">', "approved origin"),
        ("sitemap.xml", "<urlset/>", "sitemap.xml"),
        ("docs/robots.txt", "User-agent: *", "robots.txt"),
        ("docs/software-source-code.jsonld", "{}", "software-source-code.jsonld"),
    ),
    ids=(
        "single-canonical",
        "open-graph",
        "twitter",
        "sitemap",
        "robots",
        "published-jsonld",
    ),
)
def test_live_site_metadata_fails_closed(relative, content, message, tmp_path):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

    with pytest.raises(SystemExit, match=message):
        verify_deferred_site_boundary(tmp_path)


class FakeWheelMetadata(dict):
    def get_all(self, key):
        return self.get(key)


def _wheel_metadata():
    return FakeWheelMetadata(
        {
            "Name": "FairLendKit",
            "Summary": VERIFY_MODULE.DESCRIPTION,
            "Version": VERIFY_MODULE.VERSION,
            "Author": VERIFY_MODULE.AUTHOR,
            "Requires-Python": VERIFY_MODULE.REQUIRES_PYTHON,
            "Classifier": sorted(VERIFY_MODULE.CLASSIFIERS),
            "Keywords": [",".join(sorted(VERIFY_MODULE.KEYWORDS))],
            "License": VERIFY_MODULE.LICENSE_ID,
            "Project-URL": [
                f"Homepage, {VERIFY_MODULE.REPOSITORY}",
                f"Repository, {VERIFY_MODULE.REPOSITORY}",
                f"Issues, {VERIFY_MODULE.ISSUES}",
                f"Documentation, {VERIFY_MODULE.REPOSITORY}/blob/main/docs/index.md",
            ],
        }
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("Name", "Wrong", "wheel name"),
        ("Summary", "Wrong", "summary or version"),
        ("Version", "9.9", "summary or version"),
        ("Author", "Wrong", "wheel author"),
        ("Requires-Python", ">=3.12", "Requires-Python"),
        ("Classifier", [], "classifiers"),
        ("Keywords", ["wrong"], "keywords"),
        ("License", "MIT", "wheel license"),
        ("Project-URL", [], "project URLs"),
    ),
    ids=(
        "name",
        "summary",
        "version",
        "author",
        "requires-python",
        "classifiers",
        "keywords",
        "license",
        "project-urls",
    ),
)
def test_installed_wheel_metadata_fails_closed(field, value, message):
    metadata = _wheel_metadata()
    metadata[field] = value

    with pytest.raises(SystemExit, match=message):
        verify_installed_package(metadata)
