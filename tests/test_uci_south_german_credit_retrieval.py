from __future__ import annotations

import importlib.util
import io
import json
import os
import stat
import sys
import warnings
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "retrieve_uci_south_german_credit.py"
SPEC = importlib.util.spec_from_file_location("uci_retrieval", SCRIPT)
assert SPEC and SPEC.loader
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, url):
        self.calls.append(url)
        if not self.responses:
            raise AssertionError("unexpected network attempt")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def roots(tmp_path):
    tmp_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    quarantine = tmp_path / "quarantine"
    audit = tmp_path / "audit"
    quarantine.mkdir(mode=0o700)
    audit.mkdir(mode=0o700)
    os.chmod(quarantine, 0o700)
    os.chmod(audit, 0o700)
    return quarantine, audit


def archive_bytes(members=None, *, mutate=None):
    members = members or {"a.txt": b"alpha\n", "b.txt": b"beta\n", "c.txt": b"gamma\n"}
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in members.items() if isinstance(members, dict) else members:
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED
                if mutate:
                    mutate(info)
                archive.writestr(info, content)
    return output.getvalue()


def policy(data, members=None, **overrides):
    members = members or {"a.txt": 6, "b.txt": 5, "c.txt": 6}
    values = {
        "expected_compressed_size": len(data),
        "max_compressed_size": len(data) + 64,
        "expected_members": members,
        "expected_uncompressed_size": sum(members.values()),
        "max_uncompressed_size": sum(members.values()) + 64,
    }
    values.update(overrides)
    return harness.Policy(**values)


def response(data, *, status=200, headers=None, chunks=None):
    base = {"content-length": str(len(data)), "content-type": "application/zip"}
    base.update(headers or {})
    return harness.Response(status, base, chunks if chunks is not None else (data,))


def assert_failed_once(tmp_path, *, data=None, responses=None, test_policy=None, run_id="run-1"):
    quarantine, audit = roots(tmp_path)
    data = data or archive_bytes()
    transport = FakeTransport(responses or [response(data)])
    with pytest.raises(Exception):
        harness.retrieve_once(
            run_id=run_id,
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=test_policy or policy(data),
        )
    assert not (quarantine / run_id).exists()
    assert (audit / f"{run_id}.spent").stat().st_mode & 0o777 == 0o400
    assert json.loads((audit / f"{run_id}.json").read_text())["states"][-1]["state"] == "failed"
    calls = len(transport.calls)
    with pytest.raises(FileExistsError):
        harness.retrieve_once(
            run_id=run_id,
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=test_policy or policy(data),
        )
    assert len(transport.calls) == calls


def test_valid_redirected_retrieval_is_quarantined_read_only(tmp_path):
    data = archive_bytes()
    redirect = harness.Response(302, {"location": "/final.zip"}, ())
    transport = FakeTransport([redirect, response(data)])
    quarantine, audit = roots(tmp_path)
    result = harness.retrieve_once(
        run_id="authorized-1",
        quarantine_root=quarantine,
        audit_root=audit,
        transport=transport,
        policy=policy(data),
    )
    run_dir = quarantine / "authorized-1"
    assert result["compressed_size"] == len(data)
    assert run_dir.stat().st_mode & 0o777 == 0o700
    assert (run_dir / "package.zip").stat().st_mode & 0o777 == 0o400
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in (run_dir / "members").iterdir())
    assert not any(part == "data" for path in run_dir.rglob("*") for part in path.parts)
    audit_payload = (audit / "authorized-1.json").read_text()
    assert "alpha" not in audit_payload
    assert json.loads(audit_payload)["states"][-1]["state"] == "succeeded"


@pytest.mark.parametrize(
    "location",
    [
        "http://archive.ics.uci.edu/final.zip",
        "https://evil.example/final.zip",
        "https://127.0.0.1/final.zip",
        "https://user:pass@archive.ics.uci.edu/final.zip",
        "https://archive.ics.uci.edu:443/final.zip",
        "https://archive.ics.uci.edu/final.zip?token=secret",
    ],
)
def test_redirect_targets_fail_before_source_bytes_persist(tmp_path, location):
    data = archive_bytes()
    assert_failed_once(
        tmp_path,
        data=data,
        responses=[harness.Response(302, {"location": location}, ())],
    )


def test_excessive_redirects_and_header_stream_limits(tmp_path):
    data = archive_bytes()
    redirects = [harness.Response(302, {"location": f"/r{index}"}, ()) for index in range(6)]
    assert_failed_once(tmp_path / "redirects", data=data, responses=redirects)

    bad_header = response(data, headers={"content-length": str(len(data) + 1)})
    assert_failed_once(tmp_path / "header", data=data, responses=[bad_header])

    huge_header = response(data, headers={"x-padding": "x" * 9000})
    assert_failed_once(tmp_path / "header-bytes", data=data, responses=[huge_header])

    limited = policy(data, max_compressed_size=len(data))
    oversized = response(data, headers={"content-length": str(len(data))}, chunks=(data, b"x"))
    assert_failed_once(tmp_path / "stream", data=data, responses=[oversized], test_policy=limited)


def test_interrupted_truncated_and_length_mismatch_streams_are_cleaned(tmp_path):
    data = archive_bytes()

    def interrupted():
        yield data[:10]
        raise OSError("injected interrupted stream")

    assert_failed_once(tmp_path / "interrupt", data=data, responses=[response(data, chunks=interrupted())])
    assert_failed_once(tmp_path / "truncated", data=data, responses=[response(data, chunks=(data[:-1],))])
    mismatch = response(data, headers={"content-length": str(len(data) - 1)})
    assert_failed_once(tmp_path / "mismatch", data=data, responses=[mismatch])


@pytest.mark.parametrize(
    "names",
    [
        [("/a.txt", b"a"), ("b.txt", b"b"), ("c.txt", b"c")],
        [("../a.txt", b"a"), ("b.txt", b"b"), ("c.txt", b"c")],
        [("a.txt", b"a"), ("a.txt", b"a"), ("c.txt", b"c")],
        [("A.txt", b"a"), ("a.txt", b"a"), ("c.txt", b"c")],
        [("e\u0301.txt", b"a"), ("é.txt", b"a"), ("c.txt", b"c")],
        [("a.zip", b"a"), ("b.txt", b"b"), ("c.txt", b"c")],
    ],
)
def test_malicious_member_names_are_rejected(tmp_path, names):
    data = archive_bytes(names)
    expected = {name: len(content) for name, content in names}
    assert_failed_once(tmp_path, data=data, test_policy=policy(data, expected))


def test_nul_and_collision_path_checks_are_explicit():
    with pytest.raises(ValueError):
        harness._validate_member_names(["a\x00.txt", "b.txt", "c.txt"])
    with pytest.raises(ValueError):
        harness._validate_member_names(["a\\b.txt", "b.txt", "c.txt"])
    with pytest.raises(ValueError):
        harness._validate_member_names(["C:/a.txt", "b.txt", "c.txt"])


@pytest.mark.parametrize("mode", [stat.S_IFLNK | 0o777, stat.S_IFCHR | 0o600, stat.S_IFDIR | 0o700])
def test_symlink_device_and_nonregular_members_are_rejected(tmp_path, mode):
    def mutate(info):
        if info.filename == "a.txt":
            info.create_system = 3
            info.external_attr = mode << 16

    data = archive_bytes(mutate=mutate)
    assert_failed_once(tmp_path, data=data)


def test_encrypted_nested_trailing_missing_unexpected_and_size_limits(tmp_path):
    base = archive_bytes()
    assert_failed_once(tmp_path / "trailing", data=base + b"trailing", test_policy=policy(base + b"trailing"))

    missing = archive_bytes({"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    assert_failed_once(tmp_path / "missing", data=missing, test_policy=policy(missing))

    unexpected_members = {"a.txt": 6, "b.txt": 5, "wrong.txt": 6}
    assert_failed_once(tmp_path / "unexpected", data=base, test_policy=policy(base, unexpected_members))

    wrong_size = dict(a=1)
    assert_failed_once(
        tmp_path / "member-size",
        data=base,
        test_policy=policy(base, {"a.txt": 7, "b.txt": 5, "c.txt": 6}),
    )
    assert_failed_once(
        tmp_path / "total-size",
        data=base,
        test_policy=policy(base, expected_uncompressed_size=18),
    )

    too_many_data = archive_bytes(
        {"a.txt": b"a", "b.txt": b"b", "c.txt": b"c", "d.txt": b"d"}
    )
    assert_failed_once(
        tmp_path / "member-count",
        data=too_many_data,
        test_policy=policy(too_many_data),
    )

    encrypted = bytearray(base)
    cursor = 0
    while True:
        cursor = encrypted.find(b"PK\x03\x04", cursor)
        if cursor < 0:
            break
        encrypted[cursor + 6 : cursor + 8] = (
            int.from_bytes(encrypted[cursor + 6 : cursor + 8], "little") | 1
        ).to_bytes(2, "little")
        cursor += 4
    cursor = 0
    while True:
        cursor = encrypted.find(b"PK\x01\x02", cursor)
        if cursor < 0:
            break
        encrypted[cursor + 8 : cursor + 10] = (
            int.from_bytes(encrypted[cursor + 8 : cursor + 10], "little") | 1
        ).to_bytes(2, "little")
        cursor += 4
    encrypted_bytes = bytes(encrypted)
    assert_failed_once(
        tmp_path / "encrypted",
        data=encrypted_bytes,
        test_policy=policy(encrypted_bytes),
    )


def test_ratio_encryption_and_content_privacy_controls(tmp_path):
    data = archive_bytes({"a.txt": b"a" * 1000, "b.txt": b"b", "c.txt": b"c"})
    sizes = {"a.txt": 1000, "b.txt": 1, "c.txt": 1}
    assert_failed_once(tmp_path / "ratio", data=data, test_policy=policy(data, sizes, max_ratio=2))

    binary = archive_bytes({"a.txt": b"a\x00b", "b.txt": b"b", "c.txt": b"c"})
    binary_sizes = {"a.txt": 3, "b.txt": 1, "c.txt": 1}
    assert_failed_once(tmp_path / "binary", data=binary, test_policy=policy(binary, binary_sizes))

    privacy = archive_bytes({"a.txt": b"account_number\n", "b.txt": b"b", "c.txt": b"c"})
    privacy_sizes = {"a.txt": 15, "b.txt": 1, "c.txt": 1}
    assert_failed_once(tmp_path / "privacy", data=privacy, test_policy=policy(privacy, privacy_sizes))


def test_cleanup_preserves_spent_marker_and_refuses_early_cleanup(tmp_path):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    harness.retrieve_once(
        run_id="cleanup-1",
        quarantine_root=quarantine,
        audit_root=audit,
        transport=FakeTransport([response(data)]),
        policy=policy(data),
    )
    with pytest.raises(ValueError, match="deadline"):
        harness.cleanup_run(run_id="cleanup-1", quarantine_root=quarantine, audit_root=audit)
    payload = json.loads((audit / "cleanup-1.json").read_text())
    deadline = harness.datetime.fromisoformat(payload["retention_deadline"])
    harness.cleanup_run(
        run_id="cleanup-1",
        quarantine_root=quarantine,
        audit_root=audit,
        now=deadline,
    )
    assert not (quarantine / "cleanup-1").exists()
    assert (audit / "cleanup-1.spent").exists()
    assert json.loads((audit / "cleanup-1.json").read_text())["states"][-1]["state"] == "cleaned"


def test_roots_and_run_ids_fail_before_network(tmp_path):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    transport = FakeTransport([response(data)])
    with pytest.raises(ValueError):
        harness.retrieve_once(
            run_id="../bad",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert transport.calls == []
    os.chmod(quarantine, 0o777)
    with pytest.raises(ValueError):
        harness.retrieve_once(
            run_id="bad-root",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert transport.calls == []
