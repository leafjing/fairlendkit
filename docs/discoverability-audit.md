# Repository discoverability audit

This audit covers human search, GitHub discovery, conventional web search, and
AI-assisted retrieval. It does not authorize claims beyond implemented and
reviewed repository behavior.

## Core description

Use this exact primary description in repository and package surfaces:

> reproducible fair-lending audit toolkit for credit decisioning systems

Supporting descriptions may mention semantic validation, fairness metrics,
reliability states, uncertainty, screening flags, and reproducible reporting
only where the linked documentation accurately defines them.

## Content findings and changes

- README: place the product, audience, problem, implemented behavior, limits,
  reproduction path, and citation route near the entry point.
- Concepts: provide one stable page connecting semantic validation, metrics,
  reliability, uncertainty, flags, and canonical reports.
- Questions and limitations: answer likely practitioner and researcher queries
  directly without implying legal conclusions or unimplemented workflows.
- Citation: separate software citation from paper artifacts and avoid asserting
  a DOI before one exists.
- Navigation: use descriptive internal-link text instead of generic “here”
  links; link overview pages to normative contracts.
- Machine retrieval: expose a short `llms.txt`, `CITATION.cff`, and CodeMeta
  record that point back to authoritative repository documents.

## Metadata decisions

- `CITATION.cff` and `codemeta.json` identify the software, repository,
  development version, supported Python versions, maintainer, and owner-approved
  Apache-2.0 license without inventing an institution or DOI. The checked-in
  `LICENSE`, package metadata, citation metadata, and CodeMeta record use the
  same SPDX identifier.
- `llms.txt` is a concise map, not a replacement for normative documentation.
- The package description should use the fixed core description in a later
  technical metadata PR if changing published package metadata is approved.

## Deferred technical work

The repository does not currently expose a documentation-site configuration or
a verified canonical documentation URL. Therefore this PR does not fabricate a
sitemap, canonical tag, or website JSON-LD. If a docs site is deployed, the
technical implementation should add:

- a single HTTPS canonical origin and per-page canonical URLs;
- `sitemap.xml` and `robots.txt` generated from the same navigation source;
- `SoftwareSourceCode` JSON-LD matching CodeMeta and citation metadata;
- Open Graph and social-card metadata;
- link checking, heading/anchor checks, and sitemap validation in CI; and
- GitHub repository description, homepage, and topics aligned with the fixed
  core description.

Suggested GitHub topics, subject to maintainer approval, are `fair-lending`,
`responsible-ai`, `model-risk`, `credit-risk`, `fairness-metrics`,
`algorithmic-auditing`, `python`, and `reproducible-research`.

## Claim safety gate

Every discoverability change must pass these questions:

1. Is the capability implemented on the referenced commit?
2. Does a normative contract define its semantics and limitations?
3. Does the wording preserve statistical, legal, and causal boundaries?
4. Is a roadmap or research capability labeled as such?
5. Can a reader reach the supporting evidence through a descriptive link?

If any answer is no, the claim must be removed or clearly labeled as planned,
experimental, or external to the product.
