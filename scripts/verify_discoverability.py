#!/usr/bin/env python3
"""Fail-closed checks for repository discovery metadata and internal links."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = "Reproducible fair-lending audit toolkit for credit decisioning systems"
REPOSITORY = "https://github.com/leafjing/fairlendkit"
ISSUES = f"{REPOSITORY}/issues"
KEYWORDS = {
    "fair lending",
    "credit decisioning",
    "responsible AI",
    "model risk",
    "fairness metrics",
    "algorithmic auditing",
    "reproducible research",
}
VERSION = "0.1.0.dev0"
AUTHOR = "Zijing Ye"
AUTHOR_GIVEN = "Zijing"
AUTHOR_FAMILY = "Ye"
AUTHOR_URL = "https://github.com/leafjing"
LICENSE_ID = "Apache-2.0"
LICENSE_URL = "https://spdx.org/licenses/Apache-2.0"
REQUIRES_PYTHON = ">=3.11"
RUNTIMES = {"Python 3.11", "Python 3.12"}
CLASSIFIERS = {
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Financial and Insurance Industry",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
}
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def fail(message: str) -> None:
    raise SystemExit(message)


def slug(text: str) -> str:
    value = re.sub(r"[^\w\- ]", "", text.strip().lower(), flags=re.UNICODE)
    return re.sub(r"\s+", "-", value)


def anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    output: set[str] = set()
    for heading in HEADING_RE.findall(path.read_text(encoding="utf-8")):
        base = slug(re.sub(r"\s+#+$", "", heading))
        index = counts.get(base, 0)
        counts[base] = index + 1
        output.add(base if index == 0 else f"{base}-{index}")
    return output


def markdown_sources(root: Path = ROOT) -> tuple[Path, ...]:
    return tuple(
        sorted(
            {
                *(root.glob("*.md")),
                *(root.joinpath("docs").rglob("*.md")),
            }
        )
    )


def verify_links(root: Path = ROOT) -> None:
    sources = (*markdown_sources(root), root / "llms.txt")
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            relative, _, fragment = target.partition("#")
            destination = (source.parent / unquote(relative)).resolve() if relative else source
            if not destination.is_relative_to(root) or not destination.is_file():
                fail(f"Broken internal link in {source.relative_to(root)}: {target}")
            if fragment and destination.suffix.lower() == ".md" and unquote(fragment) not in anchors(destination):
                fail(f"Broken heading anchor in {source.relative_to(root)}: {target}")


def _cff_scalar(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if not match:
        fail(f"CITATION.cff is missing scalar field: {key}")
    value = match.group(1).strip()
    if value.startswith(('"', "'")):
        return value[1:-1]
    return value


def _cff_list(text: str, key: str) -> list[str]:
    match = re.search(
        rf"^{re.escape(key)}:\s*$\n((?:  - .+\n?)+)", text, re.MULTILINE
    )
    if not match:
        fail(f"CITATION.cff is missing list field: {key}")
    return [line.removeprefix("  - ").strip() for line in match.group(1).splitlines()]


def _cff_author(text: str) -> dict[str, str]:
    match = re.search(
        r"^authors:\s*$\n  - family-names:\s*\"([^\"]+)\"\n"
        r"    given-names:\s*\"([^\"]+)\"\n"
        r"    alias:\s*\"([^\"]+)\"",
        text,
        re.MULTILINE,
    )
    if not match:
        fail("CITATION.cff author structure is invalid.")
    return {"family": match.group(1), "given": match.group(2), "alias": match.group(3)}


def verify_metadata(root: Path = ROOT) -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    codemeta = json.loads((root / "codemeta.json").read_text(encoding="utf-8"))
    jsonld = json.loads(
        (root / "docs/software-source-code.template.jsonld").read_text(encoding="utf-8")
    )
    cff = (root / "CITATION.cff").read_text(encoding="utf-8")

    if project["description"] != DESCRIPTION or codemeta["description"] != DESCRIPTION or jsonld["description"] != DESCRIPTION:
        fail("Core software descriptions are inconsistent.")
    if {project["version"], codemeta["version"], jsonld["version"], _cff_scalar(cff, "version")} != {VERSION}:
        fail("Software versions are inconsistent.")
    if project["urls"]["Repository"] != REPOSITORY or codemeta["codeRepository"] != REPOSITORY or jsonld["codeRepository"] != REPOSITORY:
        fail("Repository URLs are inconsistent.")
    if project["urls"]["Issues"] != ISSUES or codemeta["issueTracker"] != ISSUES or jsonld["issueTracker"] != ISSUES:
        fail("Issue tracker URLs are inconsistent.")
    if set(project["keywords"]) != KEYWORDS or set(codemeta["keywords"]) != KEYWORDS or set(jsonld["keywords"]) != KEYWORDS:
        fail("Discovery keywords are inconsistent.")
    cff_author = _cff_author(cff)
    if (
        project["authors"] != [{"name": AUTHOR}]
        or jsonld["author"] != {"@type": "Person", "name": AUTHOR, "url": AUTHOR_URL}
        or codemeta["author"] != [{"@type": "Person", "givenName": AUTHOR_GIVEN, "familyName": AUTHOR_FAMILY, "identifier": AUTHOR_URL}]
        or cff_author != {"family": AUTHOR_FAMILY, "given": AUTHOR_GIVEN, "alias": "leafjing"}
    ):
        fail("Software authors are inconsistent.")
    if _cff_scalar(cff, "title") != "FairLendKit" or _cff_scalar(cff, "repository-code") != REPOSITORY:
        fail("CITATION.cff identity is inconsistent.")
    if set(_cff_list(cff, "keywords")) != KEYWORDS:
        fail("CITATION.cff keywords are inconsistent.")
    if (
        project.get("license") != {"text": LICENSE_ID}
        or _cff_scalar(cff, "license") != LICENSE_ID
        or codemeta.get("license") != LICENSE_URL
        or jsonld.get("license") != LICENSE_URL
        or not (root / "LICENSE").is_file()
        or "[Apache License 2.0](LICENSE)" not in (root / "README.md").read_text(encoding="utf-8")
    ):
        fail("Apache-2.0 license metadata is inconsistent.")
    if project.get("requires-python") != REQUIRES_PYTHON:
        fail("Requires-Python is inconsistent.")
    if set(project.get("classifiers", ())) != CLASSIFIERS:
        fail("Package classifiers are inconsistent.")
    if set(codemeta.get("runtimePlatform", ())) != RUNTIMES or set(jsonld.get("programmingLanguage", ())) != RUNTIMES:
        fail("Supported Python runtimes are inconsistent.")
    if codemeta.get("developmentStatus") != "pre-alpha":
        fail("CodeMeta development status is inconsistent with classifiers.")
    if jsonld.get("@context") != "https://schema.org" or jsonld.get("@type") != "SoftwareSourceCode":
        fail("Schema.org structured data has an invalid context or type.")
    if jsonld.get("url") != "${CANONICAL_DOCS_URL}":
        fail("JSON-LD template must retain the unresolved canonical-origin token.")


def verify_deferred_site_boundary(root: Path = ROOT) -> None:
    for relative in ("sitemap.xml", "robots.txt", "software-source-code.jsonld"):
        if (root / relative).exists() or (root / "docs" / relative).exists():
            fail(f"{relative} requires an approved canonical documentation origin.")
    canonical_pattern = re.compile(
        r"<link\s+[^>]*rel=[\"']canonical[\"'][^>]*>", re.IGNORECASE
    )
    social_pattern = re.compile(
        r"<meta\s+[^>]*(?:property|name)=[\"'](?:og:|twitter:)", re.IGNORECASE
    )
    for page in root.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        canonical_count = len(canonical_pattern.findall(text))
        if canonical_count > 1:
            fail(f"Duplicate canonical links in {page.relative_to(root)}")
        if canonical_count or social_pattern.search(text):
            fail(f"Live site metadata requires an approved origin: {page.relative_to(root)}")


def verify_installed_package() -> None:
    metadata = importlib.metadata.metadata("fairlendkit")
    if metadata["Summary"] != DESCRIPTION or metadata["Version"] != VERSION:
        fail("Installed wheel summary or version does not match source metadata.")
    if metadata["Author"] != AUTHOR:
        fail("Installed wheel author does not match source metadata.")
    if metadata["Requires-Python"] != REQUIRES_PYTHON:
        fail("Installed wheel Requires-Python does not match source metadata.")
    if set(metadata.get_all("Classifier") or ()) != CLASSIFIERS:
        fail("Installed wheel classifiers do not match source metadata.")
    wheel_keywords = {
        keyword.strip()
        for value in (metadata.get_all("Keywords") or metadata.get_all("Keyword") or ())
        for keyword in value.split(",")
    }
    if wheel_keywords != KEYWORDS:
        fail("Installed wheel keywords do not match source metadata.")
    wheel_license = metadata.get("License-Expression") or metadata.get("License")
    if wheel_license != LICENSE_ID:
        fail("Installed wheel license does not match source metadata.")
    project_urls = set(metadata.get_all("Project-URL") or ())
    expected_urls = {
        f"Homepage, {REPOSITORY}",
        f"Repository, {REPOSITORY}",
        f"Issues, {ISSUES}",
        f"Documentation, {REPOSITORY}/blob/main/docs/index.md",
    }
    if project_urls != expected_urls:
        fail("Installed wheel project URLs do not match source metadata.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    verify_metadata()
    verify_links()
    verify_deferred_site_boundary()
    if args.installed:
        verify_installed_package()
    print("discoverability metadata and links verified")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, importlib.metadata.PackageNotFoundError) as error:
        fail(f"Invalid discovery metadata: {error}")
