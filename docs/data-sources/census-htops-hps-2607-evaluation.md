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
The English questionnaire, Source and Accuracy statement, quality-measures
workbook, and October 30 user note are each fixed by official URL, filename,
byte size, last-modified time, and SHA-256; document identity drift therefore
fails closed alongside package drift.

The October 30 user note postdates the September 10 ZIP. It reports errors in
the published Health1 and Housing3 tables, while its incorporated October 7
notice reports an error in Transportation3. All three affected products are
summary tables, and the note explicitly states that the underlying PUF is not
affected. The note therefore does not authorize or require substituting new PUF
bytes; this evaluation remains pinned to the September 10 ZIP hash. It also
warns that July race/ethnicity fields changed with the questionnaire and that
some variables were recoded for disclosure avoidance, reinforcing the ban on
silent cross-wave pooling or comparisons without wave-specific dictionaries.

`SCRAMID` is non-null and unique, and its row order agrees between the main and
replicate files. It is used only for local integrity joining and is prohibited
from features, outputs, logs, fixtures, and cross-wave/source linkage.

## Weights, imputation, and special responses

`PWEIGHT` and `HWEIGHT` are the full-sample weights. `PWEIGHT0` and `HWEIGHT0`
match them row by row and are not replicates. Exactly 80 person and 80 household
replicate weights (`1` through `80`) are finite and positive; missing, extra,
duplicated, or reordered columns fail closed. Exact ranges and per-column
statistics digests fail closed. The Source and Accuracy statement specifies
successive-difference replication with variance `4/80 * sum((theta_i -
theta_full)^2)`. This project does not implement that estimator, so this
evaluation must not output standard errors or confidence intervals. Eight
`A_*` allocation flags distinguish
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
