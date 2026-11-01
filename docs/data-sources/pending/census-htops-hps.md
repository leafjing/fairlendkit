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

## Enablement plan

- Target: `repository` for a clearly redistributable selected wave; otherwise
  `external_only` with a wave-pinned Census download workflow.
- Contact: Census HTOPS/HPS program office and official data-user support.
- Ask for: recommended current wave, revision/version identity, public-use and
  redistribution terms, archive stability, and questionnaire comparability.
- Next evidence: select one wave with rent or energy-insecurity fields and pin
  its package, codebook, questionnaire, weights, and technical note as one unit.
- Parallel work: synthetic wave fixture plus adapter enforcing survey identity,
  reference periods, weights, missing codes, and prohibition on silent pooling.
- Deliverables after approval: wave-specific manifest/adapter/data card and a
  quality/coverage example; later waves enter as separate manifests.
- Unacceptable condition: no stable wave archive or disclosure terms prevent
  safe reproducible use.
