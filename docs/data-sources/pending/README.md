# Pending candidate pool

Status: no candidate in this directory is approved for download, analysis,
redistribution, or repository inclusion.

Create one `<candidate-id>.md` record from the AD-D0 template and set
`Review status: evidence_incomplete`. A pending record must link to evidence; it
must not copy consumer rows, embed screenshots of records, or infer missing
fields from a paper's narrative.

Before a candidate can leave this directory, reviewers must independently
verify:

1. original publisher and canonical landing page;
2. exact release/version and integrity manifest;
3. license plus website/API terms and redistribution permission;
4. actual field and data dictionary coverage;
5. event, observation, decision, and performance times;
6. outcome meaning, source, maturity, and censoring;
7. privacy, reidentification, and representation risks; and
8. the final `repository`, `external_only`, or `reject` disposition.

Candidate datasets remain separate. Records from different datasets must never
be linked or presented as observations of one consumer unless the original
publishers provide an authorized, documented common identity and the privacy
review explicitly approves that linkage. Aggregate comparison across independent
datasets must label each population separately.

Transaction-like synthetic fixtures must be labeled `synthetic`; survey,
household, monthly aggregate, or account summary data must retain their real
unit of observation. The project must not reshape them into fictitious
transaction histories. Utility or rent hardship, arrears, missed bills, or
service interruption must not be renamed as loan default. Only the publisher's
documented credit outcome may satisfy the risk-outcome contract.

## Current admission queue

The current evidence-maturity order, per-source next gate, and blocking state
are maintained in the
[serial admission queue](../admission-queue.md). Every record in this directory
remains `evidence_incomplete`. Queue position controls work order only; it is not
trust, admission, download authorization, or a preferred analytical conclusion.

Each record must include an enablement plan: target `repository` or
`external_only` disposition, fixable conditions, official contact route, next
evidence, canonical mapping, synthetic fixture, and post-approval deliverables.
`Reject` is reserved for a verified unacceptable condition, not used merely
because evidence collection requires work.
