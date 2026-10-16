"""Self-contained human review view of an existing audit result."""

from __future__ import annotations

from html import escape
import json

from fairlendkit.report.models import AuditGroup, AuditResultV2


def render_html(result: AuditResultV2) -> bytes:
    """Render review-oriented HTML without scripts, network assets, or analysis."""

    intervals = {item.metric_key: item for item in result.uncertainty}
    metadata = result.metadata
    config = metadata.configuration
    validation_rows = "".join(
        "<tr>"
        f"<th scope=\"row\">{_text(layer.layer.value)}</th>"
        f"<td>{_text(_status_label(layer.status.value))}</td>"
        f"<td>{len(layer.issues)}</td>"
        "</tr>"
        for layer in result.validation.layers
    )
    flag_rows = "".join(
        "<tr>"
        f"<td>{_text(flag.code)}</td>"
        f"<td>{_text(flag.related_metric_key or '')}</td>"
        f"<td>{_number(flag.observed_value)}</td>"
        f"<td>{_text(flag.condition)} {_number(flag.threshold)}</td>"
        "</tr>"
        for flag in result.screening_flags
    ) or '<tr><td colspan="4">No screening flags were emitted.</td></tr>'
    metric_rows = "".join(
        _metric_row(metric, intervals.get(metric.key))
        for metric in result.observed_metrics
    )
    limitation_items = "".join(
        f"<li><code>{_text(item.code.value if hasattr(item.code, 'value') else item.code)}</code>: "
        f"{_text(item.detail)}"
        f"{_references(item.affected_metric_keys)}</li>"
        for item in result.limitations
    ) or "<li>None recorded.</li>"
    note_items = "".join(
        f"<li>{_text(item.recorded_at.isoformat())} — {_text(item.author)}: {_text(item.text)}</li>"
        for item in result.practitioner_review_notes
    ) or "<li>No practitioner review notes are attached.</li>"
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FairLendKit audit report</title>
<style>
body{{font-family:system-ui,sans-serif;line-height:1.45;max-width:1200px;margin:auto;padding:2rem;color:#17202a}}
h1,h2{{line-height:1.2}} table{{border-collapse:collapse;width:100%;margin:1rem 0}}
caption{{font-weight:700;text-align:left;padding:.5rem 0}} th,td{{border:1px solid #777;padding:.45rem;text-align:left;vertical-align:top}}
.notice{{border:3px solid #333;padding:1rem;background:#f4f4f4}} code{{overflow-wrap:anywhere}}
</style>
</head>
<body>
<header><h1>FairLendKit audit report</h1></header>
<main>
<section aria-labelledby="scope"><h2 id="scope">Scope and run metadata</h2>
<dl><dt>Population</dt><dd>{_text(config.population_definition)}</dd>
<dt>Sampling</dt><dd>{_text(config.sampling_definition)}</dd>
<dt>Generated</dt><dd>{_text(metadata.generated_at.isoformat())}</dd>
<dt>Dataset version</dt><dd>{_text(config.dataset_version or 'Not recorded')}</dd>
<dt>Model version</dt><dd>{_text(config.model_version or 'Not recorded')}</dd></dl></section>
<aside class="notice" aria-label="Important interpretation notice"><strong>Human review required.</strong>
This report contains statistical screening evidence. It does not determine legal compliance,
provide legal advice, identify causation, or replace domain, governance, validation, and legal review.</aside>
<section aria-labelledby="validation"><h2 id="validation">Layered validation evidence</h2>
<p>Input rows: {result.validation.input_rows}; analyzed rows: {result.validation.analyzed_rows}.</p>
<table><caption>Validation layers</caption><thead><tr><th scope="col">Layer</th><th scope="col">Status</th><th scope="col">Issue count</th></tr></thead>
<tbody>{validation_rows}</tbody></table></section>
<section aria-labelledby="flags"><h2 id="flags">Screening flags</h2>
<table><caption>Prompts requiring practitioner review</caption><thead><tr><th scope="col">Code</th><th scope="col">Metric key</th><th scope="col">Observed</th><th scope="col">Rule</th></tr></thead>
<tbody>{flag_rows}</tbody></table></section>
<section aria-labelledby="metrics"><h2 id="metrics">Observed metrics and uncertainty</h2>
<table><caption>Schema 2.0 observed metrics</caption><thead><tr><th scope="col">Metric key</th><th scope="col">Metric</th><th scope="col">Scope</th><th scope="col">Value or reason</th><th scope="col">Reliability</th><th scope="col">Count</th><th scope="col">Interval</th></tr></thead>
<tbody>{metric_rows}</tbody></table></section>
<section aria-labelledby="limits"><h2 id="limits">Limitations</h2><ul>{limitation_items}</ul></section>
<section aria-labelledby="notes"><h2 id="notes">Practitioner review notes</h2><ul>{note_items}</ul></section>
<section aria-labelledby="repro"><h2 id="repro">Reproducibility record</h2>
<dl><dt>Schema version</dt><dd>{_text(result.schema_version)}</dd>
<dt>Package version</dt><dd>{_text(metadata.package_version)}</dd>
<dt>Data fingerprint</dt><dd><code>{_text(metadata.data_fingerprint)}</code></dd></dl></section>
</main></body></html>
"""
    return document.encode("utf-8")


def _metric_row(metric: object, interval: object | None) -> str:
    value = metric.value
    rendered_value = (
        _number(value.value)
        if value.value is not None
        else f"Undefined: {_text(value.undefined_reason.code.value)}"
    )
    rendered_interval = (
        ""
        if interval is None
        else f"[{_number(interval.lower)}, {_number(interval.upper)}] at {_number(interval.confidence_level)}"
    )
    return (
        "<tr>"
        f"<td><code>{_text(metric.key)}</code></td>"
        f"<td>{_text(metric.metric.value)}</td>"
        f"<td>{_scope(metric.group, metric.comparison_group, metric.reference_group)}</td>"
        f"<td>{rendered_value}</td>"
        f"<td>{_text(metric.reliability.value)}</td>"
        f"<td>{metric.sample_count}</td>"
        f"<td>{rendered_interval}</td>"
        "</tr>"
    )


def _scope(group: AuditGroup | None, comparison: AuditGroup | None, reference: AuditGroup | None) -> str:
    if group is not None:
        return _text(_group_json(group))
    return f"{_text(_group_json(comparison))} compared with {_text(_group_json(reference))}"


def _group_json(group: AuditGroup | None) -> str:
    if group is None:
        return ""
    return json.dumps(group.attributes, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _status_label(status: str) -> str:
    return "blocking issues detected" if status == "failed" else status


def _references(keys: tuple[str, ...]) -> str:
    return "" if not keys else " (metrics: " + ", ".join(f"<code>{_text(key)}</code>" for key in keys) + ")"


def _number(value: float) -> str:
    return _text(str(value))


def _text(value: object) -> str:
    return escape(str(value), quote=True)
