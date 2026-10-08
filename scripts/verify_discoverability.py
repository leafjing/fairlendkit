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


def verify_links() -> None:
    sources = (ROOT / "README.md", ROOT / "llms.txt", *(ROOT / "docs").glob("*.md"))
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            relative, _, fragment = target.partition("#")
            destination = (source.parent / unquote(relative)).resolve() if relative else source
            if not destination.is_relative_to(ROOT) or not destination.is_file():
                fail(f"Broken internal link in {source.relative_to(ROOT)}: {target}")
            if fragment and destination.suffix.lower() == ".md" and unquote(fragment) not in anchors(destination):
                fail(f"Broken heading anchor in {source.relative_to(ROOT)}: {target}")


def verify_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    codemeta = json.loads((ROOT / "codemeta.json").read_text(encoding="utf-8"))
    jsonld = json.loads(
        (ROOT / "docs/software-source-code.template.jsonld").read_text(encoding="utf-8")
    )
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    if project["description"] != DESCRIPTION or codemeta["description"] != DESCRIPTION or jsonld["description"] != DESCRIPTION:
        fail("Core software descriptions are inconsistent.")
    if {project["version"], codemeta["version"], jsonld["version"]} != {"0.1.0.dev0"}:
        fail("Software versions are inconsistent.")
    if project["urls"]["Repository"] != REPOSITORY or codemeta["codeRepository"] != REPOSITORY or jsonld["codeRepository"] != REPOSITORY:
        fail("Repository URLs are inconsistent.")
    if project["urls"]["Issues"] != ISSUES or codemeta["issueTracker"] != ISSUES or jsonld["issueTracker"] != ISSUES:
        fail("Issue tracker URLs are inconsistent.")
    if set(project["keywords"]) != KEYWORDS or set(codemeta["keywords"]) != KEYWORDS or set(jsonld["keywords"]) != KEYWORDS:
        fail("Discovery keywords are inconsistent.")
    if project["authors"] != [{"name": "Zijing Ye"}] or jsonld["author"]["name"] != "Zijing Ye":
        fail("Package and structured-data authors are inconsistent.")
    for required in ('title: "FairLendKit"', 'version: "0.1.0.dev0"', f'repository-code: "{REPOSITORY}"'):
        if required not in cff:
            fail(f"CITATION.cff is missing: {required}")
    if "license" in codemeta or "license" in jsonld:
        fail("Discovery metadata must not assert a license before owner approval.")
    if jsonld.get("@context") != "https://schema.org" or jsonld.get("@type") != "SoftwareSourceCode":
        fail("Schema.org structured data has an invalid context or type.")
    if jsonld.get("url") != "${CANONICAL_DOCS_URL}":
        fail("JSON-LD template must retain the unresolved canonical-origin token.")


def verify_deferred_site_boundary() -> None:
    for relative in ("sitemap.xml", "robots.txt", "software-source-code.jsonld"):
        if (ROOT / relative).exists() or (ROOT / "docs" / relative).exists():
            fail(f"{relative} requires an approved canonical documentation origin.")
    canonical_pattern = re.compile(
        r"<link\s+[^>]*rel=[\"']canonical[\"'][^>]*>", re.IGNORECASE
    )
    social_pattern = re.compile(
        r"<meta\s+[^>]*(?:property|name)=[\"'](?:og:|twitter:)", re.IGNORECASE
    )
    for page in ROOT.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        canonical_count = len(canonical_pattern.findall(text))
        if canonical_count > 1:
            fail(f"Duplicate canonical links in {page.relative_to(ROOT)}")
        if canonical_count or social_pattern.search(text):
            fail(f"Live site metadata requires an approved origin: {page.relative_to(ROOT)}")


def verify_installed_package() -> None:
    metadata = importlib.metadata.metadata("fairlendkit")
    if metadata["Summary"] != DESCRIPTION or metadata["Version"] != "0.1.0.dev0":
        fail("Installed wheel summary or version does not match source metadata.")
    if metadata["Author"] != "Zijing Ye":
        fail("Installed wheel author does not match source metadata.")
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
