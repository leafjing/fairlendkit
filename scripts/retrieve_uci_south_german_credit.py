#!/usr/bin/env python3
"""Prepared one-shot UCI retrieval harness. Importing this module is offline."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Protocol
from urllib.parse import urljoin, urlsplit

PACKAGE_URL = "https://archive.ics.uci.edu/static/public/522/south+german+credit.zip"
ALLOWED_HOST = "archive.ics.uci.edu"
EXPECTED_COMPRESSED_SIZE = 13_130
MAX_COMPRESSED_SIZE = 16_384
MAX_REDIRECTS = 5
MAX_RATIO = 100
MAX_HEADER_BYTES = 8_192
MAX_HEADER_COUNT = 64
ALLOWED_MEDIA_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream"}
EXPECTED_MEMBERS = {
    "SouthGermanCredit.asc": 47_940,
    "read_SouthGermanCredit.R": 7_550,
    "codetable.txt": 3_154,
}
MAX_UNCOMPRESSED_SIZE = 65_536
EXPECTED_UNCOMPRESSED_SIZE = 58_644
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EOCD = b"PK\x05\x06"


@dataclass(frozen=True)
class Policy:
    package_url: str = PACKAGE_URL
    allowed_host: str = ALLOWED_HOST
    expected_compressed_size: int = EXPECTED_COMPRESSED_SIZE
    max_compressed_size: int = MAX_COMPRESSED_SIZE
    max_redirects: int = MAX_REDIRECTS
    expected_members: Mapping[str, int] = None  # type: ignore[assignment]
    expected_uncompressed_size: int = EXPECTED_UNCOMPRESSED_SIZE
    max_uncompressed_size: int = MAX_UNCOMPRESSED_SIZE
    max_ratio: int = MAX_RATIO

    def __post_init__(self) -> None:
        if self.expected_members is None:
            object.__setattr__(self, "expected_members", EXPECTED_MEMBERS)


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    chunks: Iterable[bytes]


class Transport(Protocol):
    def request(self, url: str) -> Response: ...


class GitInspector(Protocol):
    def commit(self) -> str: ...
    def dirty(self, paths: tuple[Path, ...]) -> bool: ...


class SubprocessGitInspector:
    def commit(self) -> str:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True
        ).strip()

    def dirty(self, paths: tuple[Path, ...]) -> bool:
        repository = Path(__file__).resolve().parents[1]
        relative = [str(path.resolve().relative_to(repository)) for path in paths]
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--", *relative], cwd=repository, text=True
        )
        return bool(output.strip())


class UrllibTransport:
    """HTTPS transport with automatic redirects disabled."""

    def request(self, url: str) -> Response:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
                return None

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/zip", "User-Agent": "FairLendKit-retrieval/1"},
            method="GET",
        )
        try:
            handle = opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            handle = error
        headers = {key.lower(): value for key, value in handle.headers.items()}

        def chunks() -> Iterable[bytes]:
            with handle:
                while True:
                    block = handle.read(8192)
                    if not block:
                        break
                    yield block

        return Response(int(handle.status), headers, chunks())


def retrieve_authorized(
    *,
    authorization_file: Path,
    transport: Transport,
    now: datetime | None = None,
    inspector: GitInspector | None = None,
) -> dict[str, object]:
    authorization = _load_authorization(
        authorization_file,
        now=now,
        inspector=inspector or SubprocessGitInspector(),
        require_unexpired=True,
        enforce_review_state=True,
    )
    return _retrieve_once(
        run_id=str(authorization["run_id"]),
        quarantine_root=Path(str(authorization["quarantine_root"])),
        audit_root=Path(str(authorization["audit_root"])),
        transport=transport,
        policy=Policy(),
        now=now,
        authorization_id=str(authorization["authorization_id"]),
        authorization_sha256=_sha256_file(authorization_file),
    )


def _retrieve_once(
    *,
    run_id: str,
    quarantine_root: Path,
    audit_root: Path,
    transport: Transport,
    policy: Policy = Policy(),
    now: datetime | None = None,
    authorization_id: str = "test-authorization",
    authorization_sha256: str = "0" * 64,
) -> dict[str, object]:
    """Perform one authorized attempt. Tests inject transport; CLI uses HTTPS."""

    _validate_run_id(run_id)
    quarantine_root = _validate_root(quarantine_root)
    audit_root = _validate_root(audit_root)
    if quarantine_root == audit_root or quarantine_root in audit_root.parents or audit_root in quarantine_root.parents:
        raise ValueError("approved roots must be outside each other")
    run_dir = quarantine_root / run_id
    audit_path = audit_root / f"{run_id}.json"
    spent_path = audit_root / f"{run_id}.spent"
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    _exclusive_file(spent_path, 0o400, b"spent\n")
    audit = {
        "schema_version": "1.0",
        "run_id": run_id,
        "authorization_binding": {
            "authorization_id": authorization_id,
            "authorization_sha256": authorization_sha256,
            "package_url": policy.package_url,
            "allowed_host": policy.allowed_host,
            "expected_compressed_size": policy.expected_compressed_size,
            "expected_members": dict(policy.expected_members),
            "max_compressed_size": policy.max_compressed_size,
            "max_uncompressed_size": policy.max_uncompressed_size,
            "harness_version": "1",
        },
        "states": [{"state": "prepared", "at": timestamp.isoformat()}],
    }
    _exclusive_json(audit_path, audit)
    partial = run_dir / "package.zip.partial"
    try:
        run_dir.mkdir(mode=0o700)
        _transition(audit_path, audit, "started", timestamp)
        metadata = _download(partial, transport, policy)
        members = _validate_and_extract(partial, run_dir, policy)
        final_archive = run_dir / "package.zip"
        partial.rename(final_archive)
        os.chmod(final_archive, 0o400)
        _sync_dir(run_dir)
        result = {
            **metadata,
            "members": members,
            "retention_deadline": (timestamp + timedelta(days=7)).isoformat(),
        }
        audit.update(result)
        _transition(audit_path, audit, "succeeded", timestamp)
        return result
    except BaseException as error:
        audit["failure_reason"] = _safe_failure(error)
        audit["retention_deadline"] = (timestamp + timedelta(days=30)).isoformat()
        try:
            _remove_run_bytes(run_dir)
            audit["cleanup_completed"] = not run_dir.exists()
            audit["remaining_bytes_state"] = (
                "absent" if audit["cleanup_completed"] else "present"
            )
        except BaseException as cleanup_error:
            audit["cleanup_completed"] = False
            audit["cleanup_failure_reason"] = _safe_failure(cleanup_error)
            try:
                audit["remaining_bytes_state"] = (
                    "present" if run_dir.exists() else "absent"
                )
            except BaseException:
                audit["remaining_bytes_state"] = "unknown"
        _transition(audit_path, audit, "failed", timestamp)
        if audit["cleanup_completed"]:
            _transition(audit_path, audit, "cleaned", timestamp)
        raise


def cleanup_run(
    *, run_id: str, quarantine_root: Path, audit_root: Path, now: datetime | None = None
) -> None:
    _validate_run_id(run_id)
    quarantine_root = _validate_root(quarantine_root)
    audit_root = _validate_root(audit_root)
    audit_path = audit_root / f"{run_id}.json"
    spent_path = audit_root / f"{run_id}.spent"
    if not spent_path.is_file() or not audit_path.is_file():
        raise ValueError("run audit or spent marker is unavailable")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("run_id") != run_id:
        raise ValueError("audit run identity mismatch")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    deadline = audit.get("retention_deadline")
    if deadline is not None and current < datetime.fromisoformat(deadline):
        raise ValueError("retention deadline has not elapsed")
    _remove_run_bytes(quarantine_root / run_id)
    states = audit.get("states", [])
    terminal = states[-1].get("state") if isinstance(states, list) and states else None
    if terminal == "failed":
        audit_path.unlink()
        _sync_dir(audit_root)
    else:
        _transition(audit_path, audit, "cleaned", current)


def cleanup_authorized(
    *,
    authorization_file: Path,
    now: datetime | None = None,
    inspector: GitInspector | None = None,
) -> None:
    authorization = _load_authorization(
        authorization_file,
        now=now,
        inspector=inspector or SubprocessGitInspector(),
        require_unexpired=False,
        enforce_review_state=False,
    )
    cleanup_run(
        run_id=str(authorization["run_id"]),
        quarantine_root=Path(str(authorization["quarantine_root"])),
        audit_root=Path(str(authorization["audit_root"])),
        now=now,
    )


def _load_authorization(
    path: Path,
    *,
    now: datetime | None,
    inspector: GitInspector,
    require_unexpired: bool,
    enforce_review_state: bool,
) -> dict[str, object]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("authorization file must be an absolute regular non-symlink file")
    if path.stat().st_mode & 0o777 != 0o400:
        raise ValueError("authorization file mode must be 0400")
    repository = Path(__file__).resolve().parents[1]
    resolved = path.resolve(strict=True)
    if resolved == repository or repository in resolved.parents:
        raise ValueError("authorization file must be outside the repository")
    try:
        authorization = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("authorization file must contain valid UTF-8 JSON") from error
    required = {
        "authorization_id", "run_id", "issued_at", "expires_at", "candidate_id",
        "max_attempts", "package_url", "allowed_redirect_host", "https_only",
        "max_redirects", "expected_content_length", "max_streamed_bytes",
        "allowed_media_types", "members", "expected_uncompressed_bytes",
        "max_uncompressed_bytes", "member_count", "max_compression_ratio",
        "harness_git_commit", "harness_sha256", "test_sha256", "quarantine_root",
        "audit_root",
    }
    if not isinstance(authorization, dict) or set(authorization) != required:
        raise ValueError("authorization schema fields must match exactly")
    for key in ("authorization_id", "run_id", "candidate_id", "harness_git_commit"):
        if not isinstance(authorization[key], str) or not authorization[key]:
            raise ValueError("authorization identity fields must be non-empty strings")
    if re.fullmatch(r"[0-9a-f]{40}", str(authorization["harness_git_commit"])) is None:
        raise ValueError("reviewed Git commit must be a lowercase full SHA")
    for key in ("harness_sha256", "test_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", str(authorization[key])) is None:
            raise ValueError("reviewed file hashes must be lowercase SHA-256")
    _validate_run_id(str(authorization["run_id"]))
    try:
        issued = datetime.fromisoformat(str(authorization["issued_at"]))
        expires = datetime.fromisoformat(str(authorization["expires_at"]))
    except ValueError as error:
        raise ValueError("authorization timestamps must be ISO 8601") from error
    if issued.tzinfo is None or expires.tzinfo is None:
        raise ValueError("authorization timestamps must be timezone-aware")
    issued, expires = issued.astimezone(UTC), expires.astimezone(UTC)
    if expires <= issued or expires - issued > timedelta(hours=24):
        raise ValueError("authorization validity cannot exceed 24 hours")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    if require_unexpired and not (issued <= current < expires):
        raise ValueError("authorization is not currently valid")
    expected = {
        "candidate_id": "uci-south-german-credit-2019",
        "max_attempts": 1,
        "package_url": PACKAGE_URL,
        "allowed_redirect_host": ALLOWED_HOST,
        "https_only": True,
        "max_redirects": MAX_REDIRECTS,
        "expected_content_length": EXPECTED_COMPRESSED_SIZE,
        "max_streamed_bytes": MAX_COMPRESSED_SIZE,
        "allowed_media_types": sorted(ALLOWED_MEDIA_TYPES),
        "members": EXPECTED_MEMBERS,
        "expected_uncompressed_bytes": EXPECTED_UNCOMPRESSED_SIZE,
        "max_uncompressed_bytes": MAX_UNCOMPRESSED_SIZE,
        "member_count": len(EXPECTED_MEMBERS),
        "max_compression_ratio": MAX_RATIO,
    }
    if any(authorization[key] != value for key, value in expected.items()):
        raise ValueError("authorization policy does not match compiled constants")
    quarantine = _validate_root(Path(str(authorization["quarantine_root"])))
    audit = _validate_root(Path(str(authorization["audit_root"])))
    if resolved == quarantine or quarantine in resolved.parents or resolved == audit or audit in resolved.parents:
        raise ValueError("authorization file must be outside approved roots")
    harness_path = Path(__file__).resolve()
    test_path = repository / "tests/test_uci_south_german_credit_retrieval.py"
    if authorization["harness_sha256"] != _sha256_file(harness_path):
        raise ValueError("authorization harness hash mismatch")
    if authorization["test_sha256"] != _sha256_file(test_path):
        raise ValueError("authorization test hash mismatch")
    if enforce_review_state:
        if authorization["harness_git_commit"] != inspector.commit():
            raise ValueError("authorization reviewed Git commit mismatch")
        if inspector.dirty((harness_path, test_path)):
            raise ValueError("reviewed harness or test file is dirty")
    return authorization


def _download(path: Path, transport: Transport, policy: Policy) -> dict[str, object]:
    url = policy.package_url
    redirects = []
    response = None
    for hop in range(policy.max_redirects + 1):
        _validate_url(url, policy)
        response = transport.request(url)
        _validate_headers(response.headers)
        if response.status in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location or hop == policy.max_redirects:
                raise ValueError("redirect chain is invalid or excessive")
            next_url = urljoin(url, location)
            _validate_url(next_url, policy)
            redirects.append({"from": url, "to": next_url, "status": response.status})
            url = next_url
            continue
        if response.status != 200:
            raise ValueError("final response status is not 200")
        break
    assert response is not None
    length = response.headers.get("content-length")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise ValueError("response media type is not an authorized ZIP type")
    if length is not None:
        try:
            declared = int(length)
        except ValueError as error:
            raise ValueError("Content-Length is invalid") from error
        if declared != policy.expected_compressed_size or declared > policy.max_compressed_size:
            raise ValueError("Content-Length violates the authorized package identity")
    digest = hashlib.sha256()
    count = 0
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            for chunk in response.chunks:
                if not isinstance(chunk, bytes):
                    raise ValueError("transport yielded a non-byte chunk")
                count += len(chunk)
                if count > policy.max_compressed_size:
                    raise ValueError("stream exceeds the compressed byte ceiling")
                stream.write(chunk)
                digest.update(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    if count != policy.expected_compressed_size or (length is not None and count != declared):
        path.unlink(missing_ok=True)
        raise ValueError("downloaded byte count does not match the authorized identity")
    return {
        "redirect_chain": redirects,
        "final_url": url,
        "http": {
            key: response.headers.get(key)
            for key in ("etag", "last-modified", "content-type", "content-length")
        },
        "compressed_size": count,
        "archive_sha256": digest.hexdigest(),
    }


def _validate_and_extract(path: Path, run_dir: Path, policy: Policy) -> list[dict[str, object]]:
    data = path.read_bytes()
    _validate_eocd(data)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != len(policy.expected_members):
            raise ValueError("ZIP member count is not authorized")
        names = [info.filename for info in infos]
        _validate_member_names(names)
        if set(names) != set(policy.expected_members):
            raise ValueError("ZIP member allowlist mismatch")
        total = 0
        for info in infos:
            _validate_member_type(info)
            expected = policy.expected_members[info.filename]
            if info.file_size != expected:
                raise ValueError("ZIP member exact size mismatch")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted ZIP members are prohibited")
            if info.compress_size == 0 and info.file_size:
                raise ValueError("ZIP member compression ratio is invalid")
            if info.compress_size and info.file_size / info.compress_size > policy.max_ratio:
                raise ValueError("ZIP member compression ratio exceeds policy")
            total += info.file_size
        if total != policy.expected_uncompressed_size or total > policy.max_uncompressed_size:
            raise ValueError("ZIP total uncompressed size mismatch")
        output = []
        member_root = run_dir / "members"
        member_root.mkdir(mode=0o700)
        for info in infos:
            target = member_root / info.filename
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            digest = hashlib.sha256()
            size = 0
            with archive.open(info) as source, os.fdopen(descriptor, "wb") as destination:
                while True:
                    block = source.read(8192)
                    if not block:
                        break
                    size += len(block)
                    if size > policy.expected_members[info.filename]:
                        raise ValueError("ZIP member stream exceeds exact size")
                    destination.write(block)
                    digest.update(block)
                destination.flush()
                os.fsync(destination.fileno())
            if size != policy.expected_members[info.filename]:
                raise ValueError("ZIP member stream is truncated")
            _validate_text(target)
            os.chmod(target, 0o400)
            output.append({"path": info.filename, "size": size, "sha256": digest.hexdigest()})
        _sync_dir(member_root)
        return sorted(output, key=lambda item: str(item["path"]))


def _validate_url(url: str, policy: Policy) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != policy.allowed_host:
        raise ValueError("URL must use the authorized HTTPS host")
    if parsed.username or parsed.password or parsed.port is not None or parsed.query or parsed.fragment:
        raise ValueError("URL credentials, ports, query, and fragment are prohibited")
    try:
        ipaddress.ip_address(parsed.hostname or "")
    except ValueError:
        pass
    else:
        raise ValueError("IP-literal targets are prohibited")


def _validate_headers(headers: Mapping[str, str]) -> None:
    if len(headers) > MAX_HEADER_COUNT:
        raise ValueError("response header count exceeds policy")
    size = sum(len(str(key).encode()) + len(str(value).encode()) + 4 for key, value in headers.items())
    if size > MAX_HEADER_BYTES:
        raise ValueError("response headers exceed the byte ceiling")


def _validate_eocd(data: bytes) -> None:
    offset = data.rfind(EOCD)
    if offset < 0 or offset + 22 > len(data):
        raise ValueError("ZIP end record is missing or truncated")
    disk, central_disk, disk_entries, entries, _, _, comment_length = struct.unpack_from(
        "<HHHHIIH", data, offset + 4
    )
    if disk or central_disk or disk_entries != entries:
        raise ValueError("multi-disk ZIP archives are prohibited")
    if offset + 22 + comment_length != len(data):
        raise ValueError("ZIP contains trailing or concatenated payload")


def _validate_member_names(names: list[str]) -> None:
    exact = set()
    folded = set()
    normalized = set()
    for name in names:
        if "\x00" in name or "\\" in name or "//" in name or re.match(r"^[A-Za-z]:", name):
            raise ValueError("ZIP member path is malformed")
        path = PurePosixPath(name)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("ZIP member path traversal is prohibited")
        if name.endswith("/") or Path(name).suffix.lower() in {".zip", ".tar", ".gz", ".7z"}:
            raise ValueError("directories and nested archives are prohibited")
        if name in exact or name.casefold() in folded or unicodedata.normalize("NFC", name) in normalized:
            raise ValueError("ZIP member paths collide")
        exact.add(name)
        folded.add(name.casefold())
        normalized.add(unicodedata.normalize("NFC", name))


def _validate_member_type(info: zipfile.ZipInfo) -> None:
    mode = (info.external_attr >> 16) & 0xFFFF
    kind = stat.S_IFMT(mode)
    if kind not in {0, stat.S_IFREG}:
        raise ValueError("ZIP symlink or special member is prohibited")


def _validate_text(path: Path) -> None:
    content = path.read_bytes()
    if b"\x00" in content:
        raise ValueError("binary member content is prohibited")
    text = content.decode("utf-8", errors="strict")
    lowered = text[:8192].casefold()
    prohibited = ("email_address", "postal_address", "account_number", "meter_id", "row_id")
    if any(term in lowered for term in prohibited):
        raise ValueError("unexpected identifier-like schema field requires privacy review")


def _validate_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError("approved root must be an existing absolute non-symlink directory")
    resolved = path.resolve(strict=True)
    repository = Path(__file__).resolve().parents[1]
    if resolved == repository or repository in resolved.parents or resolved in repository.parents:
        raise ValueError("approved root must be outside the repository")
    mode = resolved.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError("approved root cannot be group/world writable")
    parent_mode = resolved.parent.stat().st_mode
    if parent_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError("approved root parent cannot be group/world writable")
    if any(part.casefold() in {"downloads", "download"} for part in resolved.parts):
        raise ValueError("approved root cannot use a shared download directory")
    return resolved


def _validate_run_id(run_id: str) -> None:
    if RUN_ID.fullmatch(run_id) is None or run_id in {".", ".."}:
        raise ValueError("run ID is malformed")


def _exclusive_file(path: Path, mode: int, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)
    _sync_dir(path.parent)


def _exclusive_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    _exclusive_file(path, 0o600, encoded)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.unlink(missing_ok=True)
    _exclusive_file(temporary, 0o600, (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())
    temporary.replace(path)
    os.chmod(path, 0o600)
    _sync_dir(path.parent)


def _transition(path: Path, audit: dict[str, object], state: str, at: datetime) -> None:
    states = audit.setdefault("states", [])
    assert isinstance(states, list)
    states.append({"state": state, "at": at.isoformat()})
    _write_json(path, audit)


def _remove_run_bytes(run_dir: Path) -> None:
    if run_dir.exists():
        shutil.rmtree(run_dir)
        _sync_dir(run_dir.parent)


def _sync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _safe_failure(error: BaseException) -> str:
    return type(error).__name__ + ": " + str(error).split("?")[0][:256]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8192):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("retrieve", "cleanup"):
        command = commands.add_parser(name)
        command.add_argument("--authorization-file", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "retrieve":
        retrieve_authorized(
            authorization_file=args.authorization_file,
            transport=UrllibTransport(),
        )
    else:
        cleanup_authorized(authorization_file=args.authorization_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
