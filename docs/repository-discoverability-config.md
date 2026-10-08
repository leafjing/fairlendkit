# Technical repository discovery configuration

This page separates repository-native metadata from owner-controlled hosting
and GitHub settings. It is a configuration recommendation, not evidence that an
external setting or documentation site has already been published.

## GitHub repository settings

When the owner updates repository settings, use this description:

> Reproducible fair-lending audit toolkit for credit decisioning systems

Recommended topics are:

- `fair-lending`
- `responsible-ai`
- `model-risk`
- `credit-risk`
- `fairness-metrics`
- `algorithmic-auditing`
- `python`
- `reproducible-research`

Do not configure a homepage until a stable HTTPS documentation origin exists.

## Repository-native machine metadata

- [`pyproject.toml`](../pyproject.toml) is authoritative for Python package
  metadata.
- [`codemeta.json`](../codemeta.json) provides CodeMeta software metadata.
- [`software-source-code.jsonld`](software-source-code.jsonld) provides
  Schema.org `SoftwareSourceCode` data without asserting a deployed website.
- [`CITATION.cff`](../CITATION.cff) provides citation metadata.
- [`llms.txt`](../llms.txt) provides a concise, non-standard navigation map.

The automated discoverability verifier checks these surfaces for matching
name, description, version, author, repository URL, issue URL, Python support,
keywords, and resolvable internal links.

## Deferred site metadata

No canonical documentation origin is currently verified. Consequently the
repository intentionally does not publish a fabricated `sitemap.xml`,
`robots.txt`, canonical link, or Open Graph/Twitter page metadata. Add them
together from a single navigation source only after a documentation site and
stable HTTPS origin are owner-approved.
