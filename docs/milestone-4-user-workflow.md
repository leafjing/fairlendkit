# Milestone 4 — User Workflow and Reports

## Status and purpose

This contract defines the first user-facing workflow built on the completed
Milestone 3 audit engine. It turns the package API into a reproducible command
that accepts a tabular dataset and an explicit configuration, runs exactly one
audit, and writes consistent JSON, CSV, and HTML artifacts.

Milestone 4 does not add metrics or reinterpret evidence. Renderers consume the
existing `AuditResult` Schema 2.0 and must not recompute, round-trip, filter, or
silently repair audit results.

## Scope

Milestone 4 includes:

- a `fairlendkit audit` command;
- CSV input with documented parsing behavior;
- JSON configuration using the public `AuditConfig` contract;
- canonical JSON, tabular CSV, and self-contained HTML output;
- deterministic output names, atomic publication, and overwrite protection;
- stable exit codes and concise user-facing errors;
- one checked-in end-to-end example; and
- integration and golden-file release checks on Python 3.11 and 3.12.

Milestone 4 excludes threshold scanning, fairness-accuracy frontiers, proxy-risk
screening, governance dispositions, mitigation, model retraining, and legal or
compliance conclusions.

## Command contract

```bash
fairlendkit audit \
  --data examples/workflow/credit.csv \
  --config examples/workflow/audit-config.json \
  --output reports/example
```

The command accepts exactly one CSV data file, one UTF-8 JSON configuration
file, and one output directory. Paths may be relative or absolute. The command
must not read configuration from environment variables or infer semantic fields
from the dataset.

The initial command surface is deliberately small:

- `--data PATH` is required and must identify a regular file.
- `--config PATH` is required and must identify a regular file.
- `--output DIRECTORY` is required.
- `--format {json,csv,html}` may be repeated; omitting it selects all formats.
- `--overwrite` permits replacing the complete known artifact set only.
- `--version` prints the installed package version and exits.
- `--help` is generated from the declared command contract.

Unknown options, repeated singleton options, missing values, and unsupported
formats fail before reading input data. Standard output is reserved for concise
status information. Diagnostics go to standard error. Machine-readable report
content is written only to files.

## Input boundary

### Configuration

The configuration file is parsed as JSON and then validated directly by
`AuditConfig`. Unknown keys remain forbidden. CLI code must not apply hidden
defaults beyond defaults already owned by `AuditConfig`, coerce labels, or
rewrite column names.

### CSV

CSV ingestion is an outer adapter. The adapter uses UTF-8, a header row, comma
separation, and pandas' documented default scalar parsing for this milestone.
The checked-in example must pin values whose type affects label equality so the
same files behave identically on supported environments.

The CLI must report file, decode, parse, and configuration errors without a
traceback by default. It must not include row data, configuration contents, or
other potentially sensitive values in error messages.

## Output contract

Successful execution creates the requested output directory and publishes this
fixed artifact set:

```text
audit-result.json
metrics.csv
report.html
```

Only selected formats are written. Publication is all-or-nothing: render every
selected artifact in a private temporary location, then publish the complete
set after all renderers succeed. A failed run must not leave a partially updated
report set.

If any selected target already exists, the command fails unless `--overwrite`
is present. Overwrite may replace only the fixed selected target names; it must
not delete unrelated files from the output directory.

### JSON

`audit-result.json` is the canonical compact Schema 2.0 serialization of the
returned `AuditResult`. It ends with one newline. The CLI and renderer must not
modify the result or introduce a second JSON schema.

### CSV

`metrics.csv` has one row per `observed_metrics` entry in canonical result order.
Its columns are fixed for this milestone:

```text
metric_key,metric,value,undefined_reason,reliability,sample_count,
group,comparison_group,reference_group,interval_lower,interval_upper,
confidence_level
```

Group fields contain compact JSON objects with sorted keys. Undefined numeric
cells are empty and `undefined_reason` contains the stable reason code.
Uncertainty columns are populated only when the result contains an interval for
that metric key. CSV is UTF-8, uses RFC 4180 quoting, and ends with one newline.

### HTML

`report.html` is a self-contained UTF-8 document with no network requests,
scripts, remote fonts, or external stylesheets. It contains, in order:

1. scope and run metadata;
2. a conspicuous non-legal-advice and human-review notice;
3. layered validation evidence;
4. screening flags and their supporting metric references;
5. observed metrics, reliability states, and uncertainty;
6. limitations and practitioner review notes; and
7. reproducibility metadata, including schema version and fingerprints.

Undefined and unreliable results must be visibly distinct from zero and from
reliable results. HTML language must use "screening" and "review" terminology;
it must not describe a group, model, or run as fair, unfair, compliant, illegal,
approved, failed, safe, or biased.

## Exit codes

- `0`: requested artifacts were published successfully.
- `2`: command usage is invalid.
- `3`: an input file cannot be read or parsed.
- `4`: configuration or audit-data validation failed.
- `5`: output targets conflict or cannot be published safely.
- `1`: an unexpected internal error occurred.

Expected failures show one concise diagnostic without a traceback. Unexpected
failures show a stable generic diagnostic; tracebacks are limited to developer
and test entry points and are not part of the public CLI contract.

## Architecture boundaries

- The CLI owns argument parsing, filesystem coordination, and process exit.
- The CSV adapter owns dataframe ingestion, not semantic interpretation.
- Renderers accept an already validated `AuditResultV2`.
- Renderers must not import pandas or metric implementations.
- The audit application and domain modules must not import CLI or renderers.
- Serialization helpers may be shared by renderers only when they preserve the
  canonical Schema 2.0 meaning.

## Delivery slices

### 4.1 CLI and canonical JSON

Add the package entry point, JSON configuration loading, CSV ingestion, atomic
single-format publication, stable exit mapping, and an end-to-end JSON test.

### 4.2 Metrics CSV

Add the fixed metrics projection, uncertainty join by metric key, deterministic
group encoding, and golden/edge-case tests.

### 4.3 Self-contained HTML

Add the ordered report sections, safe escaping, responsible-use language,
accessibility checks, and golden structural tests.

### 4.4 Multi-format release gate

Add atomic multi-artifact publication, overwrite/conflict tests, the checked-in
workflow example, user documentation, and clean-environment verification on
Python 3.11 and 3.12.

## Acceptance criteria

Milestone 4 is complete only when:

1. one documented command produces all three artifacts from checked-in inputs;
2. JSON exactly matches the public Schema 2.0 result produced by `run_audit`;
3. every CSV metric row and HTML metric reference traces to that same result;
4. renderers perform no analysis or metric recomputation;
5. invalid input, unsafe overwrite, renderer failure, and permission failure are
   covered and never leave a partial selected artifact set;
6. HTML escapes all dataset- and configuration-derived text and performs no
   network access;
7. expected user errors contain no traceback or record-level data;
8. package, architecture, integration, and golden tests pass on Python 3.11 and
   3.12; and
9. README, documentation index, roadmap, and limitations agree with the shipped
   behavior.

