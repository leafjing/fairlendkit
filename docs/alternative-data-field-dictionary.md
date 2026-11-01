# Alternative-data field dictionary

This dictionary is normative for AD-0 through AD-2. Adapters may rename source
columns only through explicit mappings; domain objects and serialized evidence
use the names below. Models are strict and reject unknown fields.

## Shared scalar rules

- Identifiers are non-empty UTF-8 strings after surrounding whitespace is
  rejected. They are opaque and must not be parsed for consumer meaning.
- Times are timezone-aware RFC 3339 instants normalized to UTC. A calendar date
  is used only where an obligation or bill has date rather than instant
  semantics.
- Amounts are finite decimal values serialized as strings; binary floating
  point is not accepted at the input boundary. Currency is an uppercase ISO
  4217 code.
- Enumerations use the exact lowercase values listed here. Unknown values fail
  validation; adapters cannot silently map them to `other`.
- `entity_id`, `record_id`, and linkage IDs are sensitive pseudonymous input
  fields. They may be used for joining and deduplication but never serialized
  into an audit report.

## `AlternativeDataSource`

| Field | Type | Required | Contract |
|---|---|---:|---|
| `source_id` | string | yes | Stable non-consumer source identity exposed in provenance. |
| `signal_family` | enum | yes | `cash_flow`, `rent`, or `utility`. |
| `provider_id` | string | yes | Stable pseudonymous provider identity; not a consumer account ID. |
| `acquisition_method` | enum | yes | `consumer_permissioned`, `consumer_submitted`, `provider_direct`, or `public_record`. |
| `permission_reference` | string | yes | Opaque governance reference; never raw consent text or a token. |
| `coverage_start` | instant | yes | Earliest time the supplied source claims coverage. |
| `coverage_end` | instant or null | yes | Latest claimed coverage, or null only for an explicitly ongoing feed. |
| `refresh_cadence` | duration string | yes | Positive ISO 8601 duration. |
| `source_timezone` | IANA name | yes | Timezone used before UTC normalization. |
| `currency_policy` | enum | yes | `single_currency` or `record_currency`. |
| `default_currency` | ISO 4217 or null | conditional | Required only for `single_currency`. |
| `source_version` | string | yes | Version used to interpret categories and revisions. |

## `ObservationWindow`

| Field | Type | Required | Contract |
|---|---|---:|---|
| `as_of_time` | instant | yes | Decision-time boundary for all feature evidence. |
| `feature_start` | instant | yes | Inclusive lookback start. |
| `feature_end` | instant | yes | Inclusive lookback end; must be at or before `as_of_time`. |
| `performance_start` | instant | yes | Outcome window start; must be strictly after `as_of_time`. |
| `performance_end` | instant | yes | Inclusive outcome window end, after `performance_start`. |
| `label_maturity_time` | instant | yes | Earliest execution time at which the label is mature; execution must be at or after it. |
| `outcome_definition` | string | yes | Non-blank, user-supplied definition; not inferred from event types. |

The intervals `[feature_start, feature_end]` and
`[performance_start, performance_end]` cannot overlap. Source observation time,
not merely event time, controls leakage: a record first observed after
`as_of_time` is unavailable for feature construction even if its event date is
earlier.

## `CreditCoverage`

| Field | Type | Required | Contract |
|---|---|---:|---|
| `entity_id` | string | yes | Join-only pseudonymous entity identity. |
| `coverage_stratum` | configured label or null | conditional | Required and declared when evidence is available; null otherwise. |
| `definition_id` | string | yes | Versioned definition supplied by the caller. |
| `assessed_at` | instant | yes | Must be at or before `as_of_time`. |
| `evidence_available` | boolean | yes | False requires a null stratum and preserves unavailable status. |

Labels such as `limited_file` are allowed only when explicitly supplied under a
documented definition. FairLendKit never derives them from missing alternative
data, score, protected attribute, or model result.

## Shared `SignalRecord` envelope

| Field | Type | Required | Contract |
|---|---|---:|---|
| `entity_id` | string | yes | Join-only pseudonymous consumer identity. |
| `record_id` | string | yes | Unique within `source_id` and `source_version`. |
| `source_id` | string | yes | Resolves to exactly one declared source. |
| `signal_family` | enum | yes | Must equal the resolved source family. |
| `event_type` | family enum | yes | One exact value from the family vocabulary below. |
| `event_time` | instant/date | conditional | Required for point events. |
| `period_start` | instant/date | conditional | Required with `period_end` for period records. |
| `period_end` | instant/date | conditional | Must not precede `period_start`. |
| `observed_at` | instant | yes | When this version became available to the analyst. |
| `amount` | decimal string or null | conditional | Meaning fixed by event type; absence never becomes zero. |
| `currency` | ISO 4217 or null | conditional | Required whenever `amount` is present. |
| `status` | enum | yes | `posted`, `pending`, `reversed`, `adjusted`, or `unavailable`. |
| `revision_of` | record ID or null | conditional | Required for a revised version; no forward or cyclic link. |
| `reversal_of` | record ID or null | conditional | Required for a reversal; target must precede it in source history. |
| `source_version` | string | yes | Must match the interpretation version used by the source. |

Exactly one temporal form is present: `event_time`, or both period fields.
Pending and unavailable records are retained as availability evidence but do
not contribute monetary behavior. Revisions replace a prior version only if the
revision was observable by `as_of_time`; reversals offset only their explicit
target and are never independently classified.

## Family payloads

### Cash flow

Allowed event types are `inflow`, `outflow`, `balance`, `fee`, `transfer`, and
`reversal`. Monetary events require `amount`; amounts are non-negative and
direction comes from `event_type`. `balance` may be negative. A `transfer`
requires `transfer_scope` equal to `internal`, `external`, or `uncertain`;
internal and uncertain transfers are excluded from income and spending totals.
Optional `category_id` must resolve to the declared source taxonomy.

### Rent

Allowed event types are `obligation`, `payment`, `partial_payment`,
`adjustment`, `reversal`, `waiver`, and `reporting_unavailable`. Obligations
require `due_date`, `amount`, and `obligation_id`. Payment-like events require
`obligation_id`; they cannot be matched by amount or proximity alone.
`grace_days` is a non-negative configured policy value, never inferred from the
payment history. `reporting_unavailable` requires a period and no amount.

### Utility

Allowed event types are `bill`, `payment`, `partial_payment`, `adjustment`,
`reversal`, `estimated_bill`, `service_interruption`, and
`reporting_unavailable`. Bills require `service_type`, `provider_id`,
`obligation_id`, billing period, due date, amount, and currency. Allowed
`service_type` values are caller-declared (for example electricity, gas, water,
or telecommunications); the library does not rank them. Payment-like events
require an explicit `obligation_id`. `service_interruption` and
`reporting_unavailable` never count as nonpayment.

## Report-safe projection

Subject to disclosure suppression, reports may retain source ID/version,
provider ID, family, configured category, time-window boundaries, aggregate
count buckets, and aggregate metrics. They must drop
entity, record, account, obligation-linkage, address, meter, raw description,
permission token, and free-text fields. Privacy tests must search every JSON,
CSV, HTML, log, warning, and exception artifact for fixture identifiers.
