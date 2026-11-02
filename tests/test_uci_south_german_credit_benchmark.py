from pathlib import Path

import pytest

from fairlendkit.research.uci_south_german_credit import (
    ARCHIVE_SHA256,
    BenchmarkIntegrityError,
    DOI,
    MEMBERS,
    SENSITIVE_OR_PROXY_COLUMNS,
    load_south_german_credit,
)


def test_reviewed_identity_is_pinned() -> None:
    assert DOI == "10.24432/C5QG88"
    assert ARCHIVE_SHA256 == "0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551"
    assert set(MEMBERS) == {"codetable.txt", "read_SouthGermanCredit.R", "SouthGermanCredit.asc"}
    assert SENSITIVE_OR_PROXY_COLUMNS == {"famges", "alter", "gastarb"}


def test_loader_rejects_unreviewed_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "south+german+credit+update.zip"
    archive.write_bytes(b"not the reviewed archive")
    with pytest.raises(BenchmarkIntegrityError, match="SHA-256"):
        load_south_german_credit(archive)


def test_loader_does_not_fetch_or_vendor_data() -> None:
    # A caller must explicitly supply the separately obtained official archive.
    with pytest.raises(TypeError):
        load_south_german_credit()  # type: ignore[call-arg]
