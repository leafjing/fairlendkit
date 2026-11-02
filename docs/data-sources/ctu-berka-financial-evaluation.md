# CTU/Berka PKDD'99 `financial` evaluation

Evaluation date: 2026-11-02. Disposition: suitable only as an `external_only`
historical research source. No raw, sampled, or transformed row data is
committed or approved for redistribution.

## Source and snapshot identity

The evaluation connected read-only to the CTU Prague Relational Learning
Repository's public MariaDB `financial` database, as linked from
<https://relational.fel.cvut.cz/dataset/Financial>. The repository publishes no
immutable release, snapshot ID, export checksum, or explicit license for the
underlying banking data. Public access is not a redistribution grant.

The live database was read from `2026-11-02T04:48:08Z` through
`2026-11-02T04:48:28Z`. It contained 8 tables, 55 columns, and 1,079,680 rows.
This differs from the landing page's cached total of 1,090,086 rows, so the
project-computed hashes in the adjacent manifest identify only the observed
live state and are not publisher-issued release hashes. Hashes use canonical
UTF-8 JSON Lines, primary-key order, ISO-8601 dates, exact decimal strings, and
JSON nulls. No row values were retained after streaming.

## Labels, missingness, and leakage

The 682 `loan` rows contain A=203, B=31, C=403, and D=45. The landing-page
statement of 606 successful and 76 unsuccessful loans is the combined A+C and
B+D split; it is not the standard completed-loan A/B distribution. The CTU
task requires prediction at `loan.date` and only A/B records are completed, so
the eligible benchmark has 234 loans (203 A, 31 B), with material class
imbalance and limited sample size.

All 234 completed loans have transactions after the decision date. The live
join contained 17,676 transactions on or before `loan.date` and 73,013 after
it. Any feature query must enforce `trans.date <= loan.date`; post-loan
balances, transaction behavior, loan duration/completion logic, and any other
future-derived values are prohibited. The district table has one missing value
in each of A12 and A15. Transaction missingness is concentrated in `operation`,
`k_symbol`, `bank`, and `account` (183,114; 481,881; 782,812; and 760,931
rows respectively) and must retain field-specific semantics.

## Use and privacy boundary

Permitted use is a narrow, historical, external-only evaluation of relational
credit classification and temporal leakage controls. It is not representative
of modern populations or banking practice and is not approved for production
scoring, underwriting, individual decisions, causal discrimination claims, or
cross-source linkage. Identifiers, account/card/client relationships, dates,
birth-derived age, gender, district, counterparties, balances, and transaction
patterns are linkable or sensitive/proxy fields. They must not appear in
features, reports, logs, fixtures, or retained artifacts except where a
documented aggregate research method and disclosure control explicitly allow
it.

## Citation

Use both the live dataset page and repository paper, plus the original
PKDD'99 source when available:

> CTU Prague Relational Learning Repository. *Financial* (`financial`
> variant), accessed 2026-11-02. <https://relational.fel.cvut.cz/dataset/Financial>

> Motl, J., & Schulte, O. (2015). *The CTU Prague Relational Learning
> Repository*. arXiv:1511.03086. <https://arxiv.org/abs/1511.03086>

The citation is not a license. Until the rightsholder supplies an explicit
rights basis, the project must not redistribute the database or derived rows.
