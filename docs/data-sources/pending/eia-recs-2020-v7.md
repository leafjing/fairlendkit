# EIA Residential Energy Consumption Survey 2020 public microdata v7

- Candidate ID: `eia-recs-2020-v7`
- Priority: 5
- Review status: `evidence_incomplete`
- Publisher: U.S. Energy Information Administration
- Publisher class: government
- Canonical microdata page:
  <https://www.eia.gov/consumption/residential/data/2020/index.php?view=microdata>
- Official CSV:
  <https://www.eia.gov/consumption/residential/data/2020/csv/recs2020_public_v7.csv>
- Official codebook:
  <https://www.eia.gov/consumption/residential/data/2020/xls/RECS%202020%20Codebook%20for%20Public%20File%20-%20v7.xlsx>
- Method guide:
  <https://www.eia.gov/consumption/residential/data/2020/pdf/microdata-guide.pdf>
- Exact release/version: 2020 RECS public microdata v7
- License/redistribution: EIA terms not yet recorded
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

RECS provides household-level energy characteristics, consumption/expenditure
estimates, housing context, demographics, weights, and replicate weights. It is
suited to utility coverage, expenditure, energy burden, representation, and
proxy-pathway research. It is not a monthly payment ledger and does not establish
timeliness, arrears, reversals, interruption, or credit default unless an exact
official field says so.

Required evidence: terms, attribution, redistribution and automated-access
review, file size/hash, field/imputation/replicate-weight matrix, reference and
release times, and a `quality_only` approved-use record.

## Enablement plan

- Target: `repository` for the public CSV/codebook if EIA terms permit;
  otherwise `external_only` with official URL, byte hash, and cache workflow.
- Contact: EIA RECS program/data support through the official RECS contact route.
- Ask for: redistribution/attribution confirmation, stable v7 status, checksum
  availability, revision policy, and correct replicate-weight use.
- Next evidence: capture EIA website terms and v7 publication metadata, then
  verify the official file manifest after retrieval is authorized.
- Parallel work: synthetic RECS-shaped household fixture; adapter contracts for
  energy expenditures, service types, imputation flags, main and replicate
  weights, and annual reference periods.
- Deliverables after approval: adapter, weighted quality/coverage example,
  utility data card, variance tests, and source verifier.
- Unacceptable condition: official terms bar intended use or public fields have
  disclosure constraints incompatible with repository-safe outputs.
