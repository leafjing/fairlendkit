# CTU-M1 — Berka PKDD'99 Financial metadata evidence

Status: official-page and metadata-only investigation. No database connection,
SQL export, mirror download, row read, admission, promotion, or redistribution
approval was performed.

- Candidate: `ctu-berka-pkdd-1999`
- Observation date: `2026-11-02`
- Current institutional page:
  <https://relational.fel.cvut.cz/dataset/Financial>
- Repository owner context: CTU Prague Faculty of Electrical Engineering
- Historical source linked by CTU:
  <https://web.archive.org/web/20180506061559/http://lisp.vse.cz/pkdd99/Challenge/chall.htm>
- CTU repository citation page: <https://relational.fel.cvut.cz/about>

## Source authority and version identity

The CTU Relational Learning Repository page is live over HTTPS and returned
`200`, no redirect, and successful TLS verification. The repository identifies
itself as a CTU-hosted collection offered to the relational machine-learning
community and lists a current institutional contact and authors on its contact
page.

The dataset page identifies three repository transformations:

- `Financial`, by Jan Motl, with foreign keys added and Czech birth-number data
  split into date of birth and gender;
- `Financial_ijs`, by Janez Kranjc; and
- `Financial_std`, by Oliver Schulte.

The page does not expose an immutable release number, publication timestamp,
file URL, byte size for an export, checksum, or snapshot identifier. It serves a
live MariaDB database and instructs users to export a chosen database. Therefore
the exact candidate version must remain unresolved until an export records the
database variant, UTC time, schema, row counts, and byte/table hashes. The
repository's displayed `78.8 MB` is database metadata, not a promised export
size.

The later `7fefb5e` live snapshot, accessed from `2026-11-02T04:48:08Z` through
`2026-11-02T04:48:28Z`, recorded 8 tables, 55 columns, and 1,079,680 rows,
differing from the page's 1,090,086-row catalog value. This reinforces that the
database is mutable/live and that every evaluation must pin its access time,
exact schema, per-table counts, and normalized hashes rather than treating the
landing-page count as an immutable release identity.

The historical VŠE challenge and the former `relational.fit.cvut.cz` address do
not currently resolve. The live institutional endpoint is
`relational.fel.cvut.cz`; mirrors on GitHub, Kaggle, or elsewhere are not
authoritative substitutes.

## Structure, task, and temporal semantics

CTU describes `Financial` as a real relational dataset with 8 tables,
1,090,086 rows, 55 columns, missing values, numeric/string/temporal types, 682
total loan instances, target table `loan`, target column `status`, target identifier
`account_id`, and target timestamp `date`.

The standard task is restricted to finished loans: predict `A` versus `B` at
loan start. Separately, CTU summarizes the full 682-loan dataset as 606
successful and 76 unsuccessful loans. The subsequent official-live-database
evaluation in `feat/ctu-berka-financial-evaluation@7fefb5e` independently
recorded `A=203`, `B=31`, `C=403`, and `D=45`. Thus the finished-only A/B task
contains 234 loans (`203/31`), while CTU's overall summary is exactly
`A+C=606` and `B+D=76`. `C` and `D` are unfinished-loan states and must not be
silently combined with the finished-loan task. These content measurements
remain subject to independent review of `7fefb5e`.

CTU explicitly warns that ignoring time causes target leakage: future
transaction balances can perfectly separate good and bad loans, and loan date
plus duration can distinguish finished from unfinished loans relative to
1999-01-01. Any FairLendKit use must enforce an as-of boundary at `loan.date`,
exclude same-day and post-start transactions plus outcome-derived fields, and
document label maturity. Because the source records dates without decision-time
timestamps, the fail-closed rule is strictly `trans.date < loan.date`, never
`<=`. This is potentially relevant to historical cash-flow/risk research, but
only after table-level temporal and linkage review.

The final implementation evidence in
`feat/ctu-berka-financial-evaluation@25ccbd0` records 17,621 strictly pre-loan
transactions across all 234 finished loans, 55 same-day transactions across 40
finished loans, and 73,013 post-loan transactions across all 234 finished
loans. The same-day 55 and post-loan 73,013 are excluded from every feature
snapshot.

The commonly documented relational entities are accounts, clients,
dispositions, districts, cards, orders, transactions, and loans. Exact current
columns, types, keys, nulls, code domains, dates, currency units, and row counts
must be verified from the selected CTU variant; historical descriptions or
third-party mirrors must not be treated as the live schema.

## Final snapshot-integrity evidence

The `25ccbd0` manifest fixes schema SHA-256
`cd494eba2b2b80aaaf74ca0c32bb3d43ea76bff87d7a12976ed89c451c8ae129`, total
shape `1,079,680 x 55`, and these per-table shapes and canonical SHA-256 values:

- `account`: `4,500 x 4`,
  `75968bd956668686bee3c0862737978dbaa5e80e3bcbe4a384236fa4ff9ea75a`;
- `card`: `892 x 4`,
  `51cc2d890df840d50b66525281fc1a9492445934e902ab672f899b2e780e7b09`;
- `client`: `5,369 x 4`,
  `0dc07b5120bcd726cdc6b2d9c229d14dd7ea02e97a1c454c5fb19e26e2510178`;
- `disp`: `5,369 x 4`,
  `ccb76a4d1b5255b8eb8c2d98ff45487f74eec4169e0a671a109c20eac7bfaaeb`;
- `district`: `77 x 16`,
  `9d85a1bd8f7a0fcd85c238f3fc805ed4d65cd6420eb7fe0c259627dc7380c705`;
- `loan`: `682 x 7`,
  `a2c331ee1a4f1bd97e4e6c56e431a805b97a18d3b4d443af15244510bae64d2f`;
- `order`: `6,471 x 6`,
  `9b88d5bbdc6534cd630fea9fa311aa3fd931a43fd73916f9f5c429d202b8af0a`;
  and
- `trans`: `1,056,320 x 10`,
  `7d7498d12f57d39b3c7d7e1e02c95321e3324fa97f008093b35e1f46f29eb3a0`.

Canonical hashes use UTF-8 JSON Lines, a canonical schema line, primary-key row
order, ISO-8601 dates, exact decimal strings, and JSON nulls. The implementation
fails closed on any schema hash, total shape, table shape, or table hash drift.
These are project snapshot hashes, not publisher-issued release identifiers.

## License, privacy, and permitted-use determination

The live dataset, repository About page, and Contact page provide public access
and a repository citation, but no explicit dataset license, copyright grant,
commercial-use permission, redistribution permission, or terms covering the
underlying anonymous bank data. Public MariaDB access is evidence of
availability, not a license. No Creative Commons or public-domain status may be
inferred.

Consequently:

- research evaluation against the institutional live source may proceed under
  the architect's instruction;
- raw or transformed source rows must not be committed or redistributed;
- the disposition cannot be `repository` without an explicit rights basis;
- any retained artifact must remain outside the repository and be minimized;
  and
- if suitable technically, the maximum defensible disposition is
  `external_only` pending license/rightsholder confirmation.

The dataset contains longitudinal individual banking relationships and
transactions. Even if direct identifiers were transformed, account/client
keys, dates, locations/district attributes, birth-derived age/gender, balances,
amounts, transaction patterns, cards, loans, and rare relationship combinations
create substantial linkage and singling-out risk. Identifiers must be used only
for isolated relational integrity, never logged, exported, cross-source linked,
or treated as model features without a reviewed derivation. Gender, age,
geography, account history, product use, and transaction patterns are sensitive
or proxy-sensitive and must not support production scoring or causal/legal
discrimination conclusions.

## Citation

CTU's About page supplies this repository citation:

```bibtex
@misc{motl2024ctupraguerelationallearning,
  title={The CTU Prague Relational Learning Repository},
  author={Jan Motl and Oliver Schulte},
  year={2024},
  eprint={1511.03086},
  archivePrefix={arXiv},
  primaryClass={cs.LG},
  url={https://arxiv.org/abs/1511.03086}
}
```

A future analysis must cite both the CTU repository record and the original
PKDD'99 challenge provenance linked by CTU, plus the selected variant, access
date, and project-computed snapshot hashes. This is not evidence that the CTU
article grants rights in the underlying bank data.

## Handoff

The candidate is technically promising but rights-limited. Content evaluation
should verify the exact CTU `Financial` variant, schema, hashes, time boundary,
loan-status domain, currency/date semantics, identifiers, and privacy risk. A
suitable result should be recorded as `external_only` and `quality_only` or a
narrow historical-risk benchmark unless explicit license evidence is obtained.
An unsuitable result should record the concrete provenance, privacy, leakage,
or schema reason and move to CFPB Making Ends Meet.
