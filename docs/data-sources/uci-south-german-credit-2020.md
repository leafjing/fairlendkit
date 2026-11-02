# UCI South German Credit (dataset 573) data card

Status: adopted as an external-only `quality_only` benchmark. No source rows or
archive bytes are committed to this repository.

## Identity, integrity, and citation

- Official page: <https://archive.ics.uci.edu/dataset/573/south+german+credit+update>
- Official ZIP: <https://archive.ics.uci.edu/static/public/573/south+german+credit+update.zip>
- ZIP SHA-256: `0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551`
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Citation: *South German Credit* [Dataset]. (2020). UCI Machine Learning
  Repository. <https://doi.org/10.24432/C5QG88>

The loader also pins all three member names, sizes, and SHA-256 values. Users
obtain the official archive separately and pass its local path to
`load_south_german_credit`; the loader performs no network access and makes no
repository copy.

## Reviewed contents

The whitespace-delimited table contains 1,000 unique rows, 20 predictors and
the binary `kredit` label, with no missing values. Labels are 700 good (`1`) and
300 bad (`0`). The sample describes German credits from 1973–1975, and bad
credits were deliberately oversampled.

## Allowed and prohibited use

Allowed use is limited to historical binary-classification mechanics, metric
tests, data-quality checks, and fairness/sensitivity research. It is not
representative of modern U.S. applicants and must not support production
underwriting, eligibility decisions, causal discrimination claims, or claims
about cash-flow, rent, or utility signals.

`famges` (combined personal-status/sex), `alter` (age), and `gastarb` (foreign
worker) are sensitive attributes or proxies. The benchmark object excludes
them from `model_feature_columns`; they may be used only for documented,
aggregate fairness evaluation with appropriate small-cell controls. They must
never be production scoring inputs.

The label horizon, observation window, decision time, and censoring process are
not documented well enough for `risk_eligible` status. The artifact therefore
remains permanently `quality_only` even though its bytes and citation have been
verified.
