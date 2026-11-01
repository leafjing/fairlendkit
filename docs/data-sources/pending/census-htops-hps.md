# Census HTOPS / Household Pulse Survey

- Candidate ID: `census-htops-hps`
- Priority: 4
- Review status: `evidence_incomplete`
- Publisher: U.S. Census Bureau
- Publisher class: government
- HTOPS overview: <https://www.census.gov/programs-surveys/htops.html>
- Official data page linked there:
  <https://www.census.gov/programs-surveys/household-pulse-survey/data.html>
- Exact release/version: not selected; each cycle/wave requires its own manifest
- License/redistribution: Census and file-specific terms require verification
- Decision: none
- Trust tier: A for publisher authority; admission remains incomplete

HTOPS succeeds/extends the experimental Household Pulse Survey. Topics may
cover housing payments, energy insecurity, expenses, hardship, demographics,
and weights. These are survey responses, not consumer transaction, rent-ledger,
or utility-account histories. HTOPS and HPS waves must not be silently pooled;
housing or energy difficulty is not a credit-default label.

Required evidence: one exact cycle, package, codebook, questionnaire, weights,
revision notes, terms, hashes, collection/reference periods, response-rate and
representation limits. Expected disposition is `quality_only` absent a separate
mature credit outcome.
