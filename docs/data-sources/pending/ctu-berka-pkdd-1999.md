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

## Verified institutional evidence

Checked 2026-11-01 without retrieving any dataset or mirror content:

- the current VŠE profile for Petr Berka is reachable at
  <https://insis.vse.cz/lide/clovek.pl?id=454>;
- the current VŠE Department of Information and Knowledge Engineering research
  page states that its data-mining group co-organized ECML/PKDD Discovery
  Challenges and identifies Petr Berka, but its challenge link points to the
  historical `sorry.vse.cz` host;
- the current VŠE Library Open Science support page identifies the university
  library as an institutional route for research-data management and repository
  questions; and
- the historical `sorry.vse.cz` and `lisp.vse.cz` hosts did not resolve in the
  current check.

These records establish an institutional connection and two official inquiry
routes, not an authoritative package. No current VŠE/CTU archive, package
identity, dictionary, license, redistribution permission, checksum, or privacy
terms were located. A web archive, GitHub repository, Kaggle entry, or other
mirror may help locate former filenames, but none may supply authoritative
metadata or bytes for admission. The candidate therefore remains
`evidence_incomplete`, with no manifested release and no download authorization.

## Enablement plan

- Target: `repository` if the rightsholder grants redistribution; otherwise
  `external_only` from an official archive.
- Contact: dataset author Petr Berka, CTU/VŠE research-data or library steward,
  and the historical PKDD challenge rights contact, verified through current
  institutional directories before outreach.
- Ask for: authoritative archive, exact file manifest, codebook, license or
  written permission, redistribution scope, and citation/version identity.
- Next evidence: ask the current author profile contact and VŠE Library Open
  Science support for the authoritative archive, package identity, dictionary,
  rights holder, license, redistribution scope, and privacy conditions. Sending
  that request requires separate authorization.
- Parallel work: implement a synthetic relational bank fixture with accounts,
  dated transactions, loans, revisions, and outcomes; draft mappings only from
  the official codebook once recovered.
- Deliverables after approval: pinned manifest, relational adapter, leakage
  tests, cash-flow data card, and a limited historical-risk benchmark.
- Unacceptable condition: rightsholder denial, unverifiable provenance, or
  consumer-level privacy risk that cannot be removed without destroying use.
