# Census HTOPS/HPS July 2026 public-use evaluation

Evaluated `2026-11-02T05:52:43Z`. This record is `evidence_incomplete` and is
not formal adoption. The provisional maximum is `external_only + quality_only`;
project redistribution is prohibited pending an explicit file-specific rights
basis.

## Official identity and structure

The Census HPS PUF page identifies July 2026 (`2607`) as the latest published
2026 cross-sectional HTOPS/HPS release. The official ZIP contains the 255-column
PUF, a 163-column replicate-weight file, and a 255-variable XLSX dictionary.
Both CSVs contain 12,755 rows with no duplicates. Exact sizes, SHA-256 values,
ordered schemas, and the dictionary-derived special-code mapping are pinned in
the adjacent manifest and evidence JSON. No respondent rows are committed.

`SCRAMID` is non-null and unique, and its row order agrees between the main and
replicate files. It is used only for local integrity joining and is prohibited
from features, outputs, logs, fixtures, and cross-wave/source linkage.

## Weights, imputation, and special responses

`PWEIGHT` and `HWEIGHT`, plus 81 person and 81 household replicate weights
(`0` through `80`), are finite and positive. Exact ranges and per-column
statistics digests fail closed. Eight `A_*` allocation flags distinguish
allocated (`1`) from non-allocated (`2`) values and are pinned separately.

The PUF has no blank cells. Dictionary-defined `-88/-88.0` “Not in universe”
and `-99/-99.0` “Did not answer” rules are column-specific, separate from each
other and from ordinary values. Their complete mappings and deterministic
digest are retained; notably `METRO=-88` means outside the top-ten MSA set and
is not silently counted as “Not in universe.”

## Fitness and limits

The release supports weighted aggregate quality, representation, hardship,
housing, energy, transport, health, and imputation research. It is survey
microdata, not a transaction, rent, utility-account, underwriting, or observed
loan-performance dataset. Rent/mortgage arrears, food/energy insecurity,
expense difficulty, and other hardship responses must retain their survey
meaning and must never be relabeled as credit default.

Prohibited uses include individual scoring, underwriting, eligibility or
adverse-action decisions, reidentification, `SCRAMID` linkage, silent pooling
with other waves, and production claims. Sensitive or proxy-bearing geography,
age, sex/orientation, race/ethnicity, education, income, disability, health,
housing, household, employment, and hardship fields require disclosure controls.

Citation: U.S. Census Bureau, *Household Trends and Outlook Pulse Survey /
Household Pulse Survey Public Use File, July 2026 (HTOPS_HPS_2607)*, accessed
2026-11-02.
