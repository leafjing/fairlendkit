# CTU/Berka PKDD'99 financial dataset

- Candidate ID: `ctu-berka-pkdd-1999`
- Priority: 1
- Review status: `evidence_incomplete`
- Publisher/legal entity: attributed to Petr Berka / Czech academic sources;
  current authoritative publisher must be confirmed
- Publisher class: university, pending confirmation
- Historical landing page:
  <https://sorry.vse.cz/~berka/challenge/pkdd1999/berka.htm> was unreachable on
  2026-11-01
- Exact release/version: PKDD'99 discovery challenge dataset, unverified package
- License/redistribution: no official license text verified
- Decision: none; download and redistribution prohibited pending verification
- Trust tier: `untrusted` pending an authoritative current source

Published descriptions characterize relational banking records such as accounts,
transactions, loans, orders, cards, clients, and districts. This makes it a
potential cash-flow and credit-outcome source, but third-party mirrors are not
authoritative and no mirror may be downloaded under this record.

The historical period and database identifiers create material reidentification,
linkage, provenance, and representativeness concerns. Transaction dates may
support temporal ordering, but observation/revision time, label maturity,
currency semantics, and the authoritative loan-outcome mapping are unverified.

Required evidence: an author/CTU/VŠE-controlled current source, official
codebook, package manifest, license and redistribution permission, checksums,
outcome horizon, and privacy review. Availability on Kaggle, GitHub, or another
mirror does not change the disposition.

## Enablement plan

- Target: `repository` if the rightsholder grants redistribution; otherwise
  `external_only` from an official archive.
- Contact: dataset author Petr Berka, CTU/VŠE research-data or library steward,
  and the historical PKDD challenge rights contact, verified through current
  institutional directories before outreach.
- Ask for: authoritative archive, exact file manifest, codebook, license or
  written permission, redistribution scope, and citation/version identity.
- Next evidence: locate current institutional author and archive records, then
  send one documented permission request rather than relying on mirrors.
- Parallel work: implement a synthetic relational bank fixture with accounts,
  dated transactions, loans, revisions, and outcomes; draft mappings only from
  the official codebook once recovered.
- Deliverables after approval: pinned manifest, relational adapter, leakage
  tests, cash-flow data card, and a limited historical-risk benchmark.
- Unacceptable condition: rightsholder denial, unverifiable provenance, or
  consumer-level privacy risk that cannot be removed without destroying use.
