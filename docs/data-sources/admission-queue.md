# Alternative-data serial admission queue

Status: **pending independent review**. Snapshot date: 2026-11-02.

This queue covers every candidate currently listed in
[`pending/`](pending/README.md). It translates custice's instruction to assess
all listed sources into a strictly serial workflow. It is not a bulk-download,
admission, repository, or redistribution authorization.

## Queue invariants

- Work on one candidate at a time. Only metadata and contract preparation for a
  later candidate may proceed while an earlier candidate awaits an external
  answer; live retrievals never run in parallel.
- Every candidate has its own publisher evidence, package identity, manifest,
  retrieval contract/harness, authorization record, single-use run ID,
  repository-external quarantine, audit record, hashes, adapter, data card,
  privacy review, license decision, and final disposition.
- The UCI harness is package-specific. It must not retrieve another candidate,
  even if that candidate also publishes a ZIP or CSV.
- Each stage requires its own independently reviewed artifact and explicit
  authorization. Success at one stage does not authorize the next.
- A failure stops that candidate at its current gate. It does not convert into
  rejection without evidence, does not trigger an automatic retry, and does not
  block evidence work for the next candidate.
- Separate datasets never share consumer identities or get presented as one
  consumer history. Survey hardship is not a transaction event or loan default.
- Until a candidate's manifest is independently changed, it remains
  `evidence_incomplete`, `release_id=null`, redistribution/scope=`unverified`,
  and repository SHA-256 values null.

## Per-candidate gate sequence

Every candidate advances through these gates in order:

1. **Q0 — official evidence:** authoritative landing/package, publisher-issued
   version if one exists, members, dictionary, terms, intended-use boundary,
   privacy risks, and a complete pending manifest.
2. **Q1 — retrieval preparation:** source-specific contract and offline-tested
   harness plus a read-only authorization record binding reviewed code, official
   URL, limits, run ID, expiry, quarantine, and audit paths. No live network call.
3. **Q2 — controlled retrieval:** one authorized invocation into a repository-
   external quarantine. No retry, repository write, or product use.
4. **Q3 — byte-level review:** container/member hashes, schema, null tokens,
   identifiers, privacy, license/NOTICE, provenance, label/time semantics,
   weights, and adapter assumptions are independently checked.
5. **Q4 — admission decision:** record exactly `repository`, `external_only`, or
   `reject`, with approved/prohibited uses and unresolved limitations. Retrieval
   alone never implies admission.
6. **Q5 — promotion:** a separate reviewed change may add permitted source bytes
   or an external-only recipe, completed manifest, NOTICE, data card, adapter,
   schema validation, synthetic fixtures, and tests.
7. **Q6 — redistribution:** allowed only when the recorded license and terms
   affirmatively permit the exact redistributed artifacts and all attribution,
   notice, modification, privacy, and provenance requirements are satisfied.

## Evidence-maturity order

### 1. UCI South German Credit

- Candidate: [`uci-south-german-credit-2019`](pending/uci-south-german-credit-2019.md)
- Current gate: Q0/UCI-M1 response-metadata evidence. The first Q2 authorization
  was consumed and failed closed before body streaming; cleanup and zero
  residual bytes were independently verified. It cannot enter Q3 or Q4.
- Evidence ready: official UCI page and DOI, official package URL, three expected
  members and sizes, CC BY 4.0 presentation, field-level privacy proposal,
  benchmark-only boundary, approved offline controlled-retrieval harness.
- Intended use: generic historical credit-risk metric/adapter benchmark only;
  never cash-flow, rent, utility, modern-population, underwriting, or production
  fairness evidence.
- Blocking before any new Q1/Q2: the official package HEAD response supplies no
  `Content-Type` or `Content-Length`, while the failed GET audit proves only that
  its normalized media type was outside the approved allowlist and did not
  preserve the exact raw header. The delivery behavior must be resolved without
  inferring GET headers from HEAD or widening the allowlist.
- Next evidence: obtain affirmative publisher header/package guidance, or
  independently review a new offline-only Harness revision that records safe
  status/redirect/header-presence evidence before rejecting a response. Only
  then may a new contract, authorization, and Run ID be proposed.
- Successor endpoint evidence: custice supplied dataset ID 573, DOI
  `10.24432/C5QG88`, and `south+german+credit+update.zip`. Metadata-only HEAD
  confirms the official UCI host and DOI chain without reading a body. Treat it
  as a new endpoint requiring independent supersession and execution review,
  never as reuse or retry of the spent dataset-522 Run.
- Q3 must resolve: actual hashes and member/schema identity, unexpected fields,
  direct/quasi-identifier risk, package notices, release-date discrepancy,
  original provenance, label horizon, sampling, and time semantics.
- Stop condition: any URL/member/hash mismatch, unexpected identifier or term,
  cleanup failure, or provenance/privacy issue stops the run and returns it to
  evidence review; there is no automatic retry or promotion.

UCI ranks first because it is the only candidate with a reviewed package-
specific offline harness and a clear small-package/license path. Its limited
benchmark value is not evidence that it is the most relevant alternative-data
source.

### 2. EIA RECS 2020 public microdata v7

- Candidate: [`eia-recs-2020-v7`](pending/eia-recs-2020-v7.md)
- Current gate: Q1 metadata contract. The 2026-11-02 metadata-only recheck
  reconfirmed the official v7 CSV, codebook, and methodology endpoints, exact
  HEAD sizes/media types/validators, January 2024 version context, and EIA
  public-domain/reuse guidance. No file body was read.
- Evidence ready: authoritative v7 CSV, codebook and method-guide URLs; observed
  byte sizes; affirmative EIA reuse guidance with a third-party-material caveat;
  documented main/replicate weights, imputation indicators, billing-coverage
  fields, and a `quality_only` boundary.
- Intended use: utility coverage, annual consumption/expenditure quality,
  imputation, weighted representation, and proxy-pathway research. It is not a
  payment ledger or credit outcome source.
- Blocking before Q2: stable release/revision identity or documented project
  snapshot rule, publisher checksum policy, automated-access review, exact
  schema/null-token plan, confirmation of third-party content, and an approved
  60-replicate-weight calculation contract with golden fixtures.
- Required bespoke retrieval: streamed 56 MB CSV controls, independent limits
  for codebook/guide, exact content-type and size policy, row/column ceilings,
  CSV formula/text safety, `DOEID` containment, and no reuse of the UCI ZIP
  harness.
- Likely disposition: `repository` only if size policy, terms, privacy, and
  third-party review permit; otherwise `external_only`.

RECS ranks second because its official version, source authority, reuse path,
dictionary, and relevant utility semantics are the strongest after UCI.

### 3. Census HTOPS July 2026 cross-sectional PUF

- Candidate: [`census-htops-hps`](pending/census-htops-hps.md)
- Current gate: Q0.
- Evidence ready: one exact cross-sectional cycle, official ZIP and supporting
  document URLs, observed byte sizes, collection dates, and a strict
  `quality_only` survey boundary.
- Intended use: housing/energy hardship coverage, missingness,
  representativeness, and survey-quality evidence; never transaction history or
  credit default.
- Blocking before Q1: official ZIP member list, data-dictionary and replicate-
  weight locations, publisher revision identity, reuse/redistribution terms,
  and the exact effect of the 2026-10-30 user note on the 2026-09-10 ZIP.
- Required bespoke retrieval: July-cycle-only ZIP contract, member whitelist,
  survey/replicate-weight validation, wave isolation, and an independently
  approved variance contract. It cannot pool 2025 longitudinal or another 2026
  cross-sectional wave.
- Likely disposition: `repository` if Census terms and package identity close;
  otherwise `external_only`.

### 4. Census/HUD AHS 2023 national PUF v1.1

- Candidate: [`census-ahs-2023-puf`](pending/census-ahs-2023-puf.md)
- Current gate: Q0.
- Evidence ready: authoritative 2023 national PUF v1.1 page, official CSV ZIP,
  value-label package, version-control document, and observed byte sizes.
- Intended use: rent/utility cost, affordability, coverage, imputation,
  representation, and housing proxy-pathway research; not a payment-event ledger
  or loan outcome source.
- Blocking before Q1: dataset-level reuse/redistribution terms, archive member
  inventory, publisher checksum/revision behavior, codebook/field matrix,
  panel/reference periods, attrition/imputation rules, and panel-ID privacy.
- Required bespoke retrieval: large-archive streaming limits, national-PUF-only
  member whitelist, panel/linkage identifier quarantine, value-label/version-
  control verification, and survey-weight contract.
- Likely disposition: `external_only` unless redistribution, repository size,
  and panel privacy all affirmatively support `repository`.

### 5. Federal Reserve SHED 2024 public-use data

- Candidate: [`federal-reserve-shed-2024`](pending/federal-reserve-shed-2024.md)
- Current gate: Q0.
- Evidence ready: authoritative survey page, current CSV ZIP and codebook URLs,
  observed sizes and 2026 update metadata, plus a `quality_only` boundary.
- Intended use: household financial coverage, bill/housing/credit-access
  survey quality and representation. Self-reported hardship is not default.
- Blocking before Q1: publisher-issued package/revision identity, ZIP members,
  package-specific public-use and redistribution terms, checksum/revision
  policy, field/reference-period matrix, weight semantics, and longitudinal-ID
  privacy restrictions.
- Required bespoke retrieval: SHED-specific ZIP/member limits, update identity,
  survey-weight validation, longitudinal identifier containment, and no
  assumption that a general website linking policy grants redistribution.
- Likely disposition: `repository` only with affirmative terms and privacy
  approval; otherwise `external_only`.

### 6. CFPB Making Ends Meet

- Candidate: [`cfpb-making-ends-meet`](pending/cfpb-making-ends-meet.md)
- Current gate: latest guide-defined target selected as Sample 6 Wave 1
  (2025-01-13 through 2025-03-28), but the official download/terms page now
  redirects and no stable package URL or active terms are pinned.
- Evidence ready: official Public Data Inventory entry and public-use-file user
  guide; an official inquiry draft exists but has not been sent.
- Intended use: financial-well-being, bill-payment, liquidity, coverage, and
  representation research. It is not a transaction ledger, and survey hardship
  is not default.
- Blocking before Q1: current official package URL, one exact sample/wave,
  package identity/members, questionnaire/codebook/weights, public-use terms,
  redistribution/automation permission, privacy limits, and survey-to-credit-
  record time alignment.
- Next action: separately authorize and send the reviewed CFPB inquiry; a reply
  must then be cited and independently assessed. The guide cannot be used to
  reconstruct or source a package from a mirror.
- Required bespoke retrieval: cannot be specified until CFPB identifies the
  current official package and terms.

### 7. CTU/Berka PKDD'99 financial dataset

- Candidate: [`ctu-berka-pkdd-1999`](pending/ctu-berka-pkdd-1999.md)
- Current gate: live CTU source and schema metadata verified. The institutional
  endpoint exposes a live MariaDB database with no immutable export identity,
  checksum, or explicit underlying-data license; content evaluation may proceed
  but repository redistribution remains prohibited.
- Evidence ready: live CTU institutional source, three named repository
  variants, database/table/row/column metadata, task and label definition,
  temporal-leakage warning, repository citation, and official contact route.
- Potential use: historical relational cash-flow/credit research if and only if
  authoritative provenance, dictionary, rights, privacy, and outcome semantics
  are recovered.
- Blocking before repository admission: immutable export identity, exact live
  schema and hashes, explicit license/redistribution permission, label horizon,
  currency/time semantics, and privacy review. Historical dead hosts and
  third-party mirrors are not source evidence.
- Next action: evaluate the official CTU `Financial` database directly; retain
  no unnecessary source rows and do not redistribute. If technically suitable,
  record `external_only` unless explicit rights evidence is obtained.

CTU/Berka ranks last by evidence maturity, not research value. If provenance or
rights cannot be made authoritative, it remains `evidence_incomplete` or is
rejected after review; mirror availability does not advance it.

## Queue advancement record

For every move, append a reviewed queue event containing candidate ID, previous
and next gate, artifact/commit identity, reviewer decision, authorization scope,
expiry when applicable, and unresolved blockers. Never record credentials,
signed URLs, quarantine paths, row values, consumer identifiers, or unpublished
publisher correspondence in the repository.

The queue is reordered only by a reviewed evidence change. A later source may
move forward when it gains clearer official identity, permission, privacy, and
reproducibility evidence; size, novelty, or a successful HTTP request alone are
not evidence maturity.
