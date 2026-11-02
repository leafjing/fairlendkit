"""Strict, external-only loader for the UCI South German Credit benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pandas as pd

ARCHIVE_SHA256 = "0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551"
DOI = "10.24432/C5QG88"
MEMBERS = {
    "codetable.txt": (3154, "0040e7a173a06d1167447b2bbc4315ee1380fa3c25db321b9fd7d97ada0721bf"),
    "read_SouthGermanCredit.R": (7550, "92340012c6387dcc0fea9dcf47e2cc9659cda93c21bd688f3f694f0f0229ed68"),
    "SouthGermanCredit.asc": (47940, "5f363343f356ca38a0236baab849e472846399b2176ccc5bd686483dd8a7562f"),
}
SENSITIVE_OR_PROXY_COLUMNS = frozenset({"famges", "alter", "gastarb"})


class BenchmarkIntegrityError(ValueError):
    """Raised when an external archive does not match the reviewed artifact."""


@dataclass(frozen=True)
class SouthGermanCreditBenchmark:
    """Reviewed historical benchmark; never a production underwriting input."""

    frame: pd.DataFrame
    source_path: Path
    usage: str = "quality_only"

    @property
    def model_feature_columns(self) -> tuple[str, ...]:
        """Columns allowed in bounded benchmark models (sensitive/proxies excluded)."""
        return tuple(
            column
            for column in self.frame.columns
            if column != "kredit" and column not in SENSITIVE_OR_PROXY_COLUMNS
        )


def load_south_german_credit(archive: str | Path) -> SouthGermanCreditBenchmark:
    """Verify and load the reviewed UCI 573 ZIP without copying it into the repo."""
    path = Path(archive)
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != ARCHIVE_SHA256:
        raise BenchmarkIntegrityError("archive SHA-256 does not match reviewed UCI 573 ZIP")

    try:
        with ZipFile(path) as package:
            infos = package.infolist()
            if {info.filename for info in infos} != set(MEMBERS):
                raise BenchmarkIntegrityError("archive member set does not match reviewed UCI 573 ZIP")
            if any(info.is_dir() or info.flag_bits & 0x1 for info in infos):
                raise BenchmarkIntegrityError("archive contains a directory or encrypted member")
            for info in infos:
                expected_size, expected_hash = MEMBERS[info.filename]
                content = package.read(info)
                if info.file_size != expected_size or len(content) != expected_size:
                    raise BenchmarkIntegrityError(f"unexpected size for {info.filename}")
                if sha256(content).hexdigest() != expected_hash:
                    raise BenchmarkIntegrityError(f"unexpected SHA-256 for {info.filename}")
                content.decode("utf-8", errors="strict")
            data = package.read("SouthGermanCredit.asc")
    except (BadZipFile, OSError, UnicodeDecodeError) as exc:
        raise BenchmarkIntegrityError("invalid reviewed UCI 573 archive") from exc

    frame = pd.read_csv(pd.io.common.BytesIO(data), sep=r"\s+")
    if frame.shape != (1000, 21):
        raise BenchmarkIntegrityError("expected 1,000 rows and 21 columns")
    if frame.isna().any().any() or frame.duplicated().any():
        raise BenchmarkIntegrityError("benchmark contains missing or duplicate rows")
    if frame["kredit"].value_counts().to_dict() != {1: 700, 0: 300}:
        raise BenchmarkIntegrityError("unexpected kredit label distribution")
    return SouthGermanCreditBenchmark(frame=frame, source_path=path.resolve())
