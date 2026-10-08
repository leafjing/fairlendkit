#!/usr/bin/env python3
"""Exercise the real, unmocked Paper 2 runtime manifest path."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fairlendkit.research.paper2.execution import build_manifest, manifest_sha256


repo_root = Path(__file__).resolve().parents[1]
manifest = build_manifest(repo_root)
print(
    json.dumps(
        {"manifest": asdict(manifest), "manifest_sha256": manifest_sha256(manifest)},
        sort_keys=True,
        separators=(",", ":"),
    )
)
