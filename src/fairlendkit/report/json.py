"""Canonical JSON view of an already assembled audit result."""

from __future__ import annotations

from fairlendkit.report.models import AuditResultV2


def render_json(result: AuditResultV2) -> bytes:
    """Return the canonical compact Schema 2.0 serialization plus one newline."""

    return result.model_dump_json().encode("utf-8") + b"\n"
