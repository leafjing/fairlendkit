"""Repository discoverability metadata and navigation checks."""

import subprocess
import sys
from pathlib import Path


def test_discoverability_metadata_and_links_are_consistent():
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/verify_discoverability.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "discoverability metadata and links verified"
