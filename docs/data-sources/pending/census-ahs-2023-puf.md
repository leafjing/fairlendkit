# Census/HUD American Housing Survey 2023 public-use file

- Candidate ID: `census-ahs-2023-puf`
- Priority: 6
- Review status: `evidence_incomplete`
- Publishers: U.S. Census Bureau and U.S. Department of Housing and Urban
  Development
- Publisher class: government
- Canonical data page: <https://www.census.gov/programs-surveys/ahs/data.html>
- 2023 PUF page:
  <https://www.census.gov/programs-surveys/ahs/data/2023/ahs-2023-public-use-file--puf-.html>
- Exact release/version: 2023 national PUF; package revision not yet pinned
- License/redistribution: official terms not yet recorded
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

AHS is housing-unit/household survey microdata with housing costs, rent,
utilities, mortgages, conditions, demographics, weights, and panel elements. It
can support affordability, coverage, data quality, representation, and
proxy-pathway research. It is not a rent or utility payment-event ledger.
Housing-cost burden, missed payment, or hardship retains its official meaning
and cannot be renamed loan default.

Required evidence: exact PUF archive/revision/members/codebook/hashes, Census/HUD
terms, field matrix, panel/reference periods, attrition, imputation, disclosure,
and a default `quality_only` use unless a mature credit outcome is documented.

## Enablement plan

- Target: `repository` if Census/HUD terms permit redistributing the selected
  public file; otherwise `external_only` with a pinned official package.
- Contact: AHS program office/data-user support and HUD AHS data steward through
  official program channels.
- Ask for: 2023 PUF revision identity, terms/redistribution, panel-ID controls,
  codebook stability, and recommended rent/utility/imputation fields.
- Next evidence: pin the national PUF package and documentation set, then verify
  terms and panel/reference-period semantics.
- Parallel work: synthetic housing-panel fixture and mappings for rent,
  utilities, burden, weights, imputations, panel time, and unavailable states.
- Deliverables after approval: adapter, panel-safe tests, housing data card,
  rent/utility quality and representation example, and manifest verifier.
- Unacceptable condition: panel/linkage restrictions or disclosure risk cannot
  be reconciled with aggregate report controls.
