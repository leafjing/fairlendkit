import hashlib
from pathlib import Path
import zipfile

import pandas as pd
import pytest

import fairlendkit.research.uci_south_german_credit as benchmark_module
from fairlendkit.research.uci_south_german_credit import (
    ARCHIVE_SHA256,
    BenchmarkIntegrityError,
    DOI,
    MEMBERS,
    SENSITIVE_OR_PROXY_COLUMNS,
    load_south_german_credit,
)


HEADERS = [
    "laufkont",
    "laufzeit",
    "moral",
    "verw",
    "hoehe",
    "sparkont",
    "beszeit",
    "rate",
    "famges",
    "buerge",
    "wohnzeit",
    "verm",
    "alter",
    "weitkred",
    "wohn",
    "bishkred",
    "beruf",
    "pers",
    "telef",
    "gastarb",
    "kredit",
]


def _synthetic_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    data: bytes | None = None,
    member_names: tuple[str, ...] = ("codetable.txt", "read_SouthGermanCredit.R", "SouthGermanCredit.asc"),
) -> Path:
    if data is None:
        rows = []
        for index in range(1000):
            label = 1 if index < 700 else 0
            rows.append([index + column + 1 for column in range(20)] + [label])
        frame = pd.DataFrame(rows, columns=HEADERS)
        data = frame.to_csv(sep=" ", index=False).encode("utf-8")

    contents = {
        "codetable.txt": b"synthetic code table\n",
        "read_SouthGermanCredit.R": b"# synthetic reader\n",
        "SouthGermanCredit.asc": data,
    }
    archive = tmp_path / "synthetic-uci-573.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name in member_names:
            package.writestr(name, contents.get(name, b"unexpected\n"))

    selected = {name: contents.get(name, b"unexpected\n") for name in member_names}
    monkeypatch.setattr(benchmark_module, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(
        benchmark_module,
        "MEMBERS",
        {name: (len(content), hashlib.sha256(content).hexdigest()) for name, content in selected.items()},
    )
    return archive


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


def test_loader_parses_synthetic_reviewed_structure_and_excludes_sensitive_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _synthetic_archive(tmp_path, monkeypatch)

    benchmark = load_south_german_credit(archive)

    assert benchmark.frame.shape == (1000, 21)
    assert benchmark.frame["kredit"].value_counts().to_dict() == {1: 700, 0: 300}
    assert not (SENSITIVE_OR_PROXY_COLUMNS & set(benchmark.model_feature_columns))
    assert "kredit" not in benchmark.model_feature_columns
    assert len(benchmark.model_feature_columns) == 17


@pytest.mark.parametrize(
    ("row_count", "good_count", "error"),
    [(999, 700, "1,000 rows and 21 columns"), (1000, 699, "label distribution")],
)
def test_loader_enforces_shape_and_label_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    row_count: int,
    good_count: int,
    error: str,
) -> None:
    rows = []
    for index in range(row_count):
        rows.append([index + column + 1 for column in range(20)] + [1 if index < good_count else 0])
    data = pd.DataFrame(rows, columns=HEADERS).to_csv(sep=" ", index=False).encode("utf-8")
    archive = _synthetic_archive(tmp_path, monkeypatch, data=data)

    with pytest.raises(BenchmarkIntegrityError, match=error):
        load_south_german_credit(archive)


def test_loader_rejects_wrong_member_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = _synthetic_archive(
        tmp_path,
        monkeypatch,
        member_names=("codetable.txt", "read_SouthGermanCredit.R", "wrong.asc"),
    )
    monkeypatch.setattr(
        benchmark_module,
        "MEMBERS",
        {
            "codetable.txt": benchmark_module.MEMBERS["codetable.txt"],
            "read_SouthGermanCredit.R": benchmark_module.MEMBERS["read_SouthGermanCredit.R"],
            "SouthGermanCredit.asc": (1, "0" * 64),
        },
    )

    with pytest.raises(BenchmarkIntegrityError, match="member set"):
        load_south_german_credit(archive)


def test_loader_rejects_malformed_table_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    malformed = b" ".join(header.encode() for header in HEADERS[:-1]) + b"\n" + b"1 " * 19 + b"1\n"
    archive = _synthetic_archive(tmp_path, monkeypatch, data=malformed)

    with pytest.raises(BenchmarkIntegrityError, match="1,000 rows and 21 columns"):
        load_south_german_credit(archive)


def test_loader_does_not_fetch_or_vendor_data() -> None:
    # A caller must explicitly supply the separately obtained official archive.
    with pytest.raises(TypeError):
        load_south_german_credit()  # type: ignore[call-arg]
