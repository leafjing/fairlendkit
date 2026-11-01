# AD-D0 — data-source discovery and admission

Status: required pre-implementation gate. No external dataset may be downloaded,
committed, scripted into a build, or used as product evidence until one completed
record under this contract receives independent approval.

This contract governs discovery and evidence collection. A public download link
does not establish permission to use, modify, automate access to, or redistribute
the data.

## Allowed outputs during discovery

AD-D0 may add only source metadata, citations, review records, and this template.
It must not add data samples, schema extracts containing consumer values,
screenshots of records, access tokens, acceptance cookies, or executable download
logic. Reviewers inspect source documentation and license text before any data
handling decision.

## Candidate record template

Create one Markdown record per candidate under
`docs/data-sources/candidates/<candidate-id>.md`. The candidate ID is a stable,
lowercase project identifier and must not contain a provider's access token or
user identity.

```markdown
# <dataset title>

- Candidate ID:
- Review status: proposed | evidence_incomplete | approved | rejected | superseded
- Reviewer and review date:
- Publisher/legal entity:
- Publisher class: government | university | international_organization |
  nonprofit | commercial | community | unknown
- Canonical landing page:
- DOI or persistent identifier:
- Exact release/version and publication date:
- Retrieval date:
- Documentation/data-dictionary URL:
- File manifest supplied by publisher:
- Publisher-supplied checksums:

## Authority and provenance

- Original publisher confirmed: yes | no | unclear
- Hosting site is original or mirror:
- Collection method and stated purpose:
- Chain of custody/version history:
- Stable citation:
- Authenticity concerns:
- Evidence links and archived citation dates:

## License and terms

- License name and exact version:
- License URL and quoted redistribution clause:
- Research/analysis permitted: yes | no | unclear
- Modification/derivatives permitted: yes | no | unclear
- Redistribution permitted: yes | no | unclear
- Automated download permitted: yes | no | unclear
- Attribution/share-alike/noncommercial requirements:
- Separate website/API terms:
- Personal-data or jurisdiction restrictions:
- License reviewer and rationale:

## Data and signal coverage

- Unit of observation:
- Population and geography:
- Collection dates:
- Cash-flow fields and semantics:
- Rent fields and semantics:
- Utility fields and semantics:
- Event time, observation time, and revision history available:
- Provider/source/version fields available:
- Amount, currency, obligation, due-date, payment, adjustment, and reversal fields:
- Data dictionary completeness:

## Outcome and time-window fitness

- Credit outcome definition:
- Outcome source and maturity rule:
- Feature observation window:
- Decision/index time:
- Performance window:
- Censoring and follow-up:
- Pre/post-decision separation possible: yes | no | unclear
- Risk-analysis use: eligible | quality_only | ineligible
- Leakage concerns:

## Privacy and security

- Direct identifiers present:
- Quasi-identifiers and high-cardinality fields:
- Sensitive/protected attributes:
- Free text, exact location, account/meter/device identifiers:
- Consent/permission basis stated by publisher:
- Reidentification and linkage risk:
- Minimum-cell or access restrictions:
- Terms permit automated analysis: yes | no | unclear
- Safe local handling requirements:
- Repository-safe projection possible: yes | no | unclear

## Representation and bias

- Sampling/recruitment mechanism:
- Traditional-credit-coverage evidence:
- Underrepresented or excluded populations:
- Provider, geography, device, account, tenancy, and service-coverage bias:
- Missing-not-at-random concerns:
- Known measurement/label bias:
- Generalizability limits:

## Reproducibility

- Expected filenames and byte sizes:
- Repository-computed SHA-256 after authorized retrieval:
- Deterministic preparation steps:
- Required software/environment:
- Upstream stability and expected update cadence:
- Offline fixture strategy:

## Decision

- Decision: repository | external_only | reject
- Trust tier: A | B | C | untrusted
- Approved analytical uses:
- Prohibited uses:
- Required attribution:
- Required controls and limitations:
- Decision evidence and signatures:
```

Blank, `unclear`, or unsupported answers remain blockers; they are not treated
as permission or absence of risk.

## Trust tiers

- **A — authoritative:** original government, university, or international-
  organization publication with stable version, documentation, provenance, and
  verifiable license.
- **B — governed:** original nonprofit or commercial publisher with named legal
  entity, documented collection/governance, stable version, and verifiable
  license and terms.
- **C — research-limited:** credible provenance but material documentation,
  representation, label, or continuity limitations. It can be approved only for
  explicitly bounded research such as data-quality mechanics.
- **Untrusted:** unknown origin, mirror without chain of custody, unverifiable
  version, conflicting terms, or unresolved integrity/privacy concern.

Trust tier never overrides license, privacy, leakage, or label gates.

## License and redistribution decision

The reviewer records one exact decision:

- `repository`: redistribution, modification, and the intended use are
  affirmatively allowed; privacy review approves the repository-safe projection;
  the dataset is small enough for repository policy; attribution and notices are
  included.
- `external_only`: use is permitted but redistribution is prohibited,
  impractical, access-controlled, or too large. The repository may later contain
  an approved downloader/build recipe, metadata, hashes, and data card, but no
  source bytes.
- `reject`: origin, integrity, license, terms, privacy, leakage, or intended-use
  requirements fail or remain unclear.

Silence in a license, “free,” “open page,” a Kaggle/API listing, or successful
download does not grant redistribution. Custom or conflicting terms require
human legal/governance review outside FairLendKit before approval.

## Coverage matrix

The candidate record must include this matrix with `yes`, `partial`, `no`, or
`unknown` plus evidence references:

| Capability | Cash flow | Rent | Utilities |
|---|---|---|---|
| Explicit signal identity |  |  |  |
| Event/period time |  |  |  |
| Observation/availability time |  |  |  |
| Provider and source version |  |  |  |
| Amount and currency |  |  |  |
| Obligation and due date |  |  |  |
| Payment and partial payment |  |  |  |
| Adjustment/revision/reversal |  |  |  |
| Explicit reporting gap |  |  |  |
| Outcome and maturity |  |  |  |
| Decision/index time |  |  |  |
| Protected-group audit fields |  |  |  |
| Traditional-credit-coverage evidence |  |  |  |

`partial` must name the missing semantics. An absent outcome or inseparable time
window restricts the source to quality/profile research and prohibits AD-3 risk
claims.

## Admission gates

A `repository` or `external_only` decision requires all applicable gates:

1. Publisher identity, original source, exact version, and documentation are
   independently verifiable.
2. File integrity can be pinned with SHA-256 after authorized retrieval.
3. License and terms affirmatively permit the intended use; repository inclusion
   additionally permits redistribution and modification.
4. Direct identifiers are absent or removed under an approved transformation;
   residual reidentification risk and disclosure controls are documented.
5. Feature, decision, and performance time can be separated for any risk use.
6. Outcome meaning, source, follow-up, and maturity are explicit for any risk use.
7. Missing coverage cannot be mistaken for consumer nonpayment or adverse
   behavior under the supplied semantics.
8. Population, sampling, provider/geographic coverage, and representation limits
   are documented, especially for consumers with limited traditional files.
9. Field mappings preserve the canonical alternative-data dictionary without
   inventing categories or linkage.
10. Independent reviewer records approved and prohibited uses.

Failure of gates 1–4 requires rejection. Failure of gates 5–6 prohibits risk
analysis but may allow a documented quality-only decision. A source cannot be
approved merely because another paper or repository used it.

## Candidate comparison and final register

`docs/data-sources/register.md` is created only after at least one candidate has
completed review. It contains no data and lists candidate ID, publisher,
version, trust tier, signal families, label/time fitness, license decision,
privacy disposition, final decision, and link to the full record. Rejected
candidates remain visible with a neutral reason so they are not repeatedly
reintroduced.

When multiple candidates cover the same purpose, prefer the one with stronger
provenance, clearer permission, safer privacy profile, better temporal semantics,
and more relevant representation—not simply the largest row count.

## Post-approval handling

Approval authorizes only the recorded disposition and uses. Before any bytes are
added or downloader is merged, a separate change must verify actual filenames,
byte sizes, SHA-256, license/notice files, privacy scan, field mapping, and
reproduction instructions. Any upstream version, license, terms, schema, URL,
or checksum change returns the candidate to `evidence_incomplete` and blocks the
pipeline until re-review.
