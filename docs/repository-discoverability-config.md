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
- [`software-source-code.template.jsonld`](software-source-code.template.jsonld)
  is a non-published Schema.org template. Deployment must replace
  `${CANONICAL_DOCS_URL}` with an owner-approved HTTPS origin and validate the
  resulting document before publishing it.
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

At deployment time, the site build must use the same approved origin for:

- the JSON-LD `url`;
- exactly one canonical link per HTML page;
- every sitemap entry and the sitemap URL in `robots.txt`; and
- Open Graph `og:url` and social-preview image URLs.

The repository verifier rejects live site-discovery artifacts before that
origin exists and rejects duplicate canonical links in any checked-in HTML.
