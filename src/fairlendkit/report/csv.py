"""Deterministic tabular projection of observed audit metrics."""

from __future__ import annotations

import csv
import io
import json

from fairlendkit.report.models import AuditGroup, AuditResultV2

CSV_COLUMNS = (
    "metric_key",
    "metric",
    "value",
    "undefined_reason",
    "reliability",
    "sample_count",
    "group",
    "comparison_group",
    "reference_group",
    "interval_lower",
    "interval_upper",
    "confidence_level",
)


def render_metrics_csv(result: AuditResultV2) -> bytes:
    """Project metrics and attached uncertainty without recomputing evidence."""

    intervals = {item.metric_key: item for item in result.uncertainty}
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for metric in result.observed_metrics:
        interval = intervals.get(metric.key)
        writer.writerow(
            {
                "metric_key": metric.key,
                "metric": metric.metric.value,
                "value": "" if metric.value.value is None else metric.value.value,
                "undefined_reason": (
                    ""
                    if metric.value.undefined_reason is None
                    else metric.value.undefined_reason.code.value
                ),
                "reliability": metric.reliability.value,
                "sample_count": metric.sample_count,
                "group": _group_json(metric.group),
                "comparison_group": _group_json(metric.comparison_group),
                "reference_group": _group_json(metric.reference_group),
                "interval_lower": "" if interval is None else interval.lower,
                "interval_upper": "" if interval is None else interval.upper,
                "confidence_level": "" if interval is None else interval.confidence_level,
            }
        )
    return stream.getvalue().encode("utf-8")


def _group_json(group: AuditGroup | None) -> str:
    if group is None:
        return ""
    return json.dumps(
        group.attributes,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
