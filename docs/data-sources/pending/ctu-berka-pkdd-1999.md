# CTU/Berka PKDD'99 financial dataset

- Candidate ID: `ctu-berka-pkdd-1999`
- Priority: 1
- Review status: `evidence_incomplete`
- Publisher/legal entity: CTU Prague Relational Learning Repository for the
  current transformed database; original PKDD'99 rights remain unverified
- Publisher class: university repository
- Current institutional page:
  <https://relational.fel.cvut.cz/dataset/Financial>
- Historical landing page:
  <https://sorry.vse.cz/~berka/challenge/pkdd1999/berka.htm> was unreachable on
  2026-11-01
- Exact release/version: CTU variants `Financial`, `Financial_ijs`, and
  `Financial_std`; no immutable release or export snapshot is published
- License/redistribution: no official license text verified
- Decision: none; content evaluation authorized, but repository inclusion and
  redistribution prohibited pending an explicit rights basis
- Trust tier: B for current CTU source authority; underlying-data rights and
  immutable snapshot identity remain unverified

The current CTU page characterizes relational banking records such as accounts,
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

The 2026-11-02 current-source investigation is recorded in
[`../investigations/ctu-berka-pkdd-1999-metadata-2026-11-02.md`](../investigations/ctu-berka-pkdd-1999-metadata-2026-11-02.md).
It identifies the live CTU FEL repository page, its three transformed variants,
8-table/1,090,086-row/55-column metadata, 682 total loan instances, CTU's
overall 606 successful / 76 unsuccessful summary, and its explicit temporal-
leakage warning. The later live content evaluation at
`feat/ctu-berka-financial-evaluation@7fefb5e` measured `A=203`, `B=31`, `C=403`,
and `D=45`: finished-only A/B is 234 (`203/31`), while the overall summary is
`A+C=606` and `B+D=76`. C/D remain unfinished and are excluded from the A/B
task. The same snapshot measured 1,079,680 live rows versus the page's
1,090,086 catalog value during access from `2026-11-02T04:48:08Z` through
`2026-11-02T04:48:28Z`, confirming the need for access-time snapshot hashes.
The original implementation identity was superseded by `25ccbd0`, independently
approved, and merged through PR #49 as
`main@c4420494918ba185609c170cd65068076dc7c54d`.

The final superseding implementation `25ccbd0` applies the strict cutoff
`trans.date < loan.date`: 17,621 eligible pre-loan transactions across all 234
finished loans, 55 same-day transactions across 40 finished loans, and 73,013
post-loan transactions across all 234 finished loans. Same-day and post-loan
transactions are excluded. Its adjacent manifest fixes the schema SHA-256,
total shape, and every table's shape and canonical SHA-256; any drift fails
closed. No raw or transformed row was committed.

The live CTU page is an authoritative current access route, but it offers a
live MariaDB export rather than an immutable package and states no explicit
dataset license or redistribution grant. Public access does not establish
rights. The candidate therefore remains `evidence_incomplete`; repository
redistribution is prohibited and the maximum provisional disposition is
`external_only` pending rights confirmation.

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
