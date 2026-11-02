# CFPB Making Ends Meet public-use file evaluation

Evaluation date: 2026-11-02. Disposition: `external_only`; permitted project use:
`quality_only`. No raw, sampled, or transformed respondent data is committed.

## Official artifacts and structure

The CFPB July 2025 user guide and official Sample 1, 3, 4, 5, and 6 ZIPs were
downloaded from `files.consumerfinance.gov`. Sample 2 is intentionally omitted
from the public release. Each ZIP contains CSV and DTA data, a codebook,
applicable questionnaires, the user guide, and a README. CSV and DTA shapes and
column order match within every package; packages are unencrypted and their
fixed archive/CSV hashes and shapes are recorded in the adjacent manifest.

All CSVs have zero duplicate rows and a non-null, unique random `ID`. That ID is
an isolation check only and must be removed before features, outputs, logs,
fixtures, or links. Shapes are Sample 1: 2,986×612; Sample 3: 2,125×404;
Sample 4: 2,136×396; Sample 5: 3,113×491; and Sample 6: 2,630×346.

## Weights, missingness, and time semantics

Every sample supplies analysis-specific weights for initial, follow-up, panel,
combined, paper, or online populations. Analysts must choose the codebook-
specified weight for the exact sample/wave/question mode; raw row counts are not
population estimates. Missing values can mean skip logic, a response recoded
for inconsistent skip logic, or nonresponse and must not be collapsed into one
state or imputed without field-specific documentation.

Only Sample 1 includes credit-derived quarterly fields: debt-presence flags,
credit-card debt/utilization, and noisy VantageScore values from December 2018
through December 2021. Survey field dates are wave intervals, not individual
decision timestamps. The files contain no verified underwriting decision,
default label, or common performance window. Payment difficulty, inability to
cover expenses, and financial well-being are not delinquency/default labels.

## Terms, privacy, and use boundary

The CFPB terms prohibit direct or indirect correlation to identify an
individual and reverse engineering of VantageScore. A recipient of repackaged,
modified, or distributed data must receive or incorporate the agreement.
Analyses may not be represented as CFPB views or official government material,
and the data/output must not be used as the basis for decisions or courses of
action. Because the live public-data page now redirects to the general research
page, this evaluation preserves the last official terms observed with the file
URLs and applies the most restrictive boundary: no repository redistribution.

Suitable uses are weighted aggregate research on financial well-being, bill
payment difficulty, liquidity, survey coverage, attrition, missingness,
privacy transformations, and proxy pathways. Prohibited uses include individual
scoring or underwriting, eligibility/adverse-action decisions, reidentification,
cross-source linkage, reconstructing credit models, or treating hardship as a
credit outcome. Demographics, oversampling strata, credit-derived values, and
longitudinal responses are sensitive or proxy-bearing and require disclosure
controls.

Suggested citation, following CFPB's terms:

> Consumer Financial Protection Bureau (CFPB). (2025). *Making Ends Meet
> Public Use File* [Dataset].
> <https://www.consumerfinance.gov/data-research/making-ends-meet-survey-data/public-data/>
