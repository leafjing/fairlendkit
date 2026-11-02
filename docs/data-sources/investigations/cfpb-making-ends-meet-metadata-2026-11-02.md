# CFPB-M1 — Making Ends Meet public-use metadata evidence

Status: official-document and metadata investigation. The CFPB user guide was
read; no MEM CSV/DTA package, row data, mirror, or reconstructed file was used.

- Candidate: `cfpb-making-ends-meet`
- Observation date: `2026-11-02`
- Public-data path:
  <https://www.consumerfinance.gov/data-research/making-ends-meet-survey-data/public-data/>
- Official user guide:
  <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>
- Publisher: U.S. Consumer Financial Protection Bureau (CFPB)

## Current source and version identity

The public-data path and parent Making Ends Meet path currently redirect to the
generic CFPB Data & Research page. The user guide remains directly available
from CFPB's official file host as a 261,183-byte PDF. It describes public-use
files for Sample 1 and Samples 3–6; Sample 2 was a small specialized sample and
is omitted.

The latest sample described by the guide is Sample 6 Wave 1, fielded from
`2025-01-13` through `2025-03-28`, with 2,630 responses. Sample 5 Wave 2 was
fielded over the same dates with 1,952 follow-up responses. The current guide
does not provide an immutable package release ID, DOI, file hashes, or direct
CSV/DTA URLs.

The former public-data page was indexed as providing per-sample CSV and DTA
downloads after acceptance of terms, but its current redirect prevents an
independent live check of links, terms version, file manifest, or prescribed
citation. Search-index or archive copies are discovery evidence only and must
not substitute for the active CFPB terms or official bytes.

## Samples, fields, and outcomes

Each sample combines all of its waves into one file and includes a unique
respondent identifier for within-sample longitudinal linkage. The public-use
files contain selected household-finance and demographic survey responses.
Sample 1 additionally contains selected credit-panel-derived variables; Samples
3–6 contain survey responses without those credit variables.

Sample 1 credit-derived fields include indicators for mortgage, student-loan,
auto-loan, and credit-card presence, plus noisy approximations of credit-card
debt, utilization, and VantageScore. CFPB added statistical noise to the three
continuous fields to reduce reidentification risk. They are not transaction
records and must not be reverse engineered or linked back to individuals.

Survey topics include financial well-being, difficulty paying bills and
expenses, ability to cover expenses after income loss, product use,
expectations, household finances, and demographics. These are descriptive
survey measures, not verified loan-performance labels. Financial hardship,
bill-payment difficulty, credit score bands, collections, inquiries, disputes,
or product holdings must not be relabeled as default or used for individual
credit decisions.

Missing values may result from skip logic, correction of inconsistent skip
logic, or item nonresponse. Select-all questions can conflate a true
not-selected response with a skipped question unless embedded skip logic
distinguishes them. Missing states must therefore remain question- and
wave-specific rather than being converted to a common zero.

## Sampling and weights

Samples deliberately oversample credit- and geography-related groups. Sample 6
oversampled people in majority African American or Hispanic areas, below-
median-income areas, and people with recent inquiries, recent disputes, 60-day
delinquencies, or very poor, poor, or fair credit scores. These are sample-
design strata and sensitive/proxy pathways, not labels or causal explanations.

Final weights combine sampling weights and nonresponse adjustment. Weighting
uses credit-score/delinquency/collection variables, credit-panel predictors,
age, missing/imputation indicators, and for some surveys ACS raking and weight
smoothing. Longitudinal analysis must use the weight corresponding to the last
included wave so attrition is reflected.

Starting with Sample 3 Wave 2, combined weights permit analyses joining the
follow-up sample with the new sample fielded concurrently. For Sample 5 Wave 2
and Sample 6 Wave 1, online-only questions require `_online` weights; other
questions use `_paper` weights, including respondents who answered online.
Unweighted results, wrong-wave weights, or mixing online/paper universes are
invalid.

## Privacy, terms, and disposition

CFPB states that contractors removed direct PII and that CFPB removed, grouped,
masked, topcoded, rounded, or dropped sensitive fields and open text before
publication. The retained respondent identifier is still linkable within a
sample and must not enter features, logs, reports, fixtures, exports, or
cross-source joins.

The guide's Acceptable Use section says the separate MEM Terms and Conditions
contain all prohibited uses and proper-citation instructions, and all users
must comply. Those live terms are not currently retrievable because the page
redirects. Therefore no license, automated-access permission, repository
redistribution right, or exact publisher-prescribed citation can be asserted.

Technical evaluation of an official CFPB file may proceed under the team's
instruction, but source rows must not be committed or redistributed. Until the
active terms are captured, the maximum provisional disposition is
`external_only`; analytical use is `quality_only` for survey coverage,
financial-well-being, hardship, weighting, missingness, representation, and
proxy-pathway research. `risk_eligible` remains false.

## Citation

No DOI is published in the guide. Pending recovery of CFPB's prescribed
citation, use this clearly provisional source identification:

> Consumer Financial Protection Bureau. *Making Ends Meet Survey Public Use
> File User Guide*. CFPB, accessed 2026-11-02.
> <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>

A data analysis must additionally name the exact sample and waves, file format,
access date, and project-computed file hash. This provisional citation does not
replace the citation required by the unavailable MEM Terms and Conditions.

## Content-evaluation handoff

Prefer Sample 6 Wave 1 as the latest guide-defined sample for a bounded
`quality_only` evaluation, unless CFPB's restored official page identifies a
newer release. Fix the official file URL, format, hash, dimensions, respondent
ID handling, question/codebook map, missing-value codes, `_online`/`_paper`
weights, sample dates, and sensitive/proxy fields. If official bytes or active
terms cannot be recovered, record the concrete failure and move to Federal
Reserve SHED 2024; do not use a mirror.
