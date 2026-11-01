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
        harness._retrieve_once(
            run_id=run_id,
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=test_policy or policy(data),
        )
    assert not (quarantine / run_id).exists()
    assert (audit / f"{run_id}.spent").stat().st_mode & 0o777 == 0o400
    payload = json.loads((audit / f"{run_id}.json").read_text())
    assert [item["state"] for item in payload["states"]][-2:] == ["failed", "cleaned"]
    assert payload["cleanup_completed"] is True
    assert payload["remaining_bytes_state"] == "absent"
    calls = len(transport.calls)
    with pytest.raises(FileExistsError):
        harness._retrieve_once(
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
    result = harness._retrieve_once(
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
    harness._retrieve_once(
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
        harness._retrieve_once(
            run_id="../bad",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert transport.calls == []
    os.chmod(quarantine, 0o777)
    with pytest.raises(ValueError):
        harness._retrieve_once(
            run_id="bad-root",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert transport.calls == []


def test_cleanup_failure_preserves_original_failure_and_audits_remaining_bytes(
    tmp_path, monkeypatch
):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    transport = FakeTransport([RuntimeError("original download failure")])

    def fail_cleanup(run_dir):
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(harness, "_remove_run_bytes", fail_cleanup)
    with pytest.raises(RuntimeError, match="original download failure"):
        harness._retrieve_once(
            run_id="cleanup-failure",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )

    payload = json.loads((audit / "cleanup-failure.json").read_text())
    assert payload["states"][-1]["state"] == "failed"
    assert payload["failure_reason"] == "RuntimeError: original download failure"
    assert payload["cleanup_completed"] is False
    assert payload["cleanup_failure_reason"] == "OSError: injected cleanup failure"
    assert payload["remaining_bytes_state"] == "present"
    assert (quarantine / "cleanup-failure").is_dir()
    assert (audit / "cleanup-failure.spent").is_file()


def test_run_directory_creation_failure_reaches_cleaned_terminal_state(
    tmp_path, monkeypatch
):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    transport = FakeTransport([response(data)])
    run_dir = quarantine / "mkdir-failure"
    original_mkdir = Path.mkdir

    def fail_target_mkdir(path, *args, **kwargs):
        if path == run_dir:
            raise OSError("injected mkdir failure")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_target_mkdir)
    with pytest.raises(OSError, match="injected mkdir failure"):
        harness._retrieve_once(
            run_id="mkdir-failure",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )

    payload = json.loads((audit / "mkdir-failure.json").read_text())
    assert [item["state"] for item in payload["states"]] == [
        "prepared",
        "failed",
        "cleaned",
    ]
    assert payload["cleanup_completed"] is True
    assert payload["remaining_bytes_state"] == "absent"
    assert transport.calls == []
    assert (audit / "mkdir-failure.spent").is_file()


@pytest.mark.parametrize(
    ("failed_state", "disk_terminal", "note"),
    [
        (
            "failed",
            "started",
            "retrieval_lifecycle_error:audit_failed_transition_not_persisted",
        ),
        (
            "cleaned",
            "failed",
            "retrieval_lifecycle_error:audit_cleaned_transition_not_persisted",
        ),
    ],
)
def test_audit_transition_write_failure_preserves_original_error_and_spent_marker(
    tmp_path, monkeypatch, failed_state, disk_terminal, note
):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    transport = FakeTransport([RuntimeError("original retrieval failure")])
    original_write = harness._write_json

    def fail_selected_transition(path, payload):
        if payload["states"][-1]["state"] == failed_state:
            raise OSError(f"injected {failed_state} audit write failure")
        return original_write(path, payload)

    monkeypatch.setattr(harness, "_write_json", fail_selected_transition)
    with pytest.raises(RuntimeError, match="original retrieval failure") as captured:
        harness._retrieve_once(
            run_id=f"audit-{failed_state}-failure",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )

    run_id = f"audit-{failed_state}-failure"
    assert note in (captured.value.__notes__ or [])
    assert json.loads((audit / f"{run_id}.json").read_text())["states"][-1][
        "state"
    ] == disk_terminal
    marker = json.loads(
        (audit / f"{run_id}.persistence-failure.json").read_text()
    )
    assert marker["attempted_state"] == failed_state
    assert marker["original_failure_reason"] == "RuntimeError: original retrieval failure"
    assert marker["cleanup_completed"] is True
    assert marker["remaining_bytes_state"] == "absent"
    assert marker["retry_forbidden"] is True
    assert not (quarantine / run_id).exists()
    assert (audit / f"{run_id}.spent").is_file()
    calls = len(transport.calls)
    with pytest.raises(FileExistsError):
        harness._retrieve_once(
            run_id=run_id,
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert len(transport.calls) == calls


def test_primary_and_emergency_audit_write_failure_still_fails_closed(
    tmp_path, monkeypatch
):
    data = archive_bytes()
    quarantine, audit = roots(tmp_path)
    transport = FakeTransport([RuntimeError("original retrieval failure")])
    original_write = harness._write_json
    original_exclusive = harness._exclusive_json

    def fail_failed_transition(path, payload):
        if payload["states"][-1]["state"] == "failed":
            raise OSError("primary audit unavailable")
        return original_write(path, payload)

    def fail_emergency_marker(path, payload):
        if path.name.endswith(".persistence-failure.json"):
            raise OSError("emergency audit unavailable")
        return original_exclusive(path, payload)

    monkeypatch.setattr(harness, "_write_json", fail_failed_transition)
    monkeypatch.setattr(harness, "_exclusive_json", fail_emergency_marker)
    with pytest.raises(RuntimeError, match="original retrieval failure") as captured:
        harness._retrieve_once(
            run_id="all-audit-failure",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )

    assert "retrieval_lifecycle_error:audit_failed_transition_not_persisted" in (
        captured.value.__notes__ or []
    )
    assert not (audit / "all-audit-failure.persistence-failure.json").exists()
    assert (audit / "all-audit-failure.spent").is_file()
    assert not (quarantine / "all-audit-failure").exists()
    calls = len(transport.calls)
    with pytest.raises(FileExistsError):
        harness._retrieve_once(
            run_id="all-audit-failure",
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
            policy=policy(data),
        )
    assert len(transport.calls) == calls


class FakeInspector:
    def __init__(self, *, commit="a" * 40, dirty=False):
        self._commit = commit
        self._dirty = dirty

    def commit(self):
        return self._commit

    def dirty(self, paths):
        assert {path.name for path in paths} == {
            "retrieve_uci_south_german_credit.py",
            "test_uci_south_german_credit_retrieval.py",
        }
        return self._dirty


def authorization_payload(quarantine, audit, now):
    repository = Path(__file__).parents[1]
    return {
        "authorization_id": "review-authorization-1",
        "run_id": "authorized-run-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + harness.timedelta(hours=1)).isoformat(),
        "candidate_id": "uci-south-german-credit-2019",
        "max_attempts": 1,
        "package_url": harness.PACKAGE_URL,
        "allowed_redirect_host": harness.ALLOWED_HOST,
        "https_only": True,
        "max_redirects": harness.MAX_REDIRECTS,
        "expected_content_length": harness.EXPECTED_COMPRESSED_SIZE,
        "max_streamed_bytes": harness.MAX_COMPRESSED_SIZE,
        "allowed_media_types": sorted(harness.ALLOWED_MEDIA_TYPES),
        "members": harness.EXPECTED_MEMBERS,
        "expected_uncompressed_bytes": harness.EXPECTED_UNCOMPRESSED_SIZE,
        "max_uncompressed_bytes": harness.MAX_UNCOMPRESSED_SIZE,
        "member_count": len(harness.EXPECTED_MEMBERS),
        "max_compression_ratio": harness.MAX_RATIO,
        "harness_git_commit": "a" * 40,
        "harness_sha256": harness._sha256_file(repository / "scripts/retrieve_uci_south_german_credit.py"),
        "test_sha256": harness._sha256_file(Path(__file__)),
        "quarantine_root": str(quarantine),
        "audit_root": str(audit),
    }


def write_authorization(tmp_path, payload):
    target = tmp_path / "authorization.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(target, 0o400)
    return target


def test_strict_authorization_binding_validates_before_transport(tmp_path):
    quarantine, audit = roots(tmp_path)
    now = harness.datetime.now(harness.UTC)
    authorization = write_authorization(
        tmp_path, authorization_payload(quarantine, audit, now)
    )
    loaded = harness._load_authorization(
        authorization,
        now=now,
        inspector=FakeInspector(),
        require_unexpired=True,
        enforce_review_state=True,
    )
    assert loaded["run_id"] == "authorized-run-1"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"unknown": True}),
        lambda payload: payload.update({"package_url": "https://evil.example/data.zip"}),
        lambda payload: payload.update({"max_attempts": 2}),
        lambda payload: payload.update({"harness_git_commit": "b" * 40}),
        lambda payload: payload.update({"harness_sha256": "0" * 64}),
        lambda payload: payload.update({"quarantine_root": payload["audit_root"]}),
    ],
)
def test_authorization_mutations_fail_before_network(tmp_path, mutation):
    quarantine, audit = roots(tmp_path)
    now = harness.datetime.now(harness.UTC)
    payload = authorization_payload(quarantine, audit, now)
    mutation(payload)
    authorization = write_authorization(tmp_path, payload)
    transport = FakeTransport([])
    with pytest.raises(ValueError):
        harness.retrieve_authorized(
            authorization_file=authorization,
            transport=transport,
            now=now,
            inspector=FakeInspector(),
        )
    assert transport.calls == []


def test_expired_dirty_and_writable_authorizations_fail_before_network(tmp_path):
    quarantine, audit = roots(tmp_path)
    now = harness.datetime.now(harness.UTC)
    payload = authorization_payload(quarantine, audit, now - harness.timedelta(hours=2))
    authorization = write_authorization(tmp_path, payload)
    transport = FakeTransport([])
    with pytest.raises(ValueError, match="currently valid"):
        harness.retrieve_authorized(
            authorization_file=authorization,
            transport=transport,
            now=now,
            inspector=FakeInspector(),
        )
    payload = authorization_payload(quarantine, audit, now)
    authorization.unlink()
    authorization = write_authorization(tmp_path, payload)
    with pytest.raises(ValueError, match="dirty"):
        harness.retrieve_authorized(
            authorization_file=authorization,
            transport=transport,
            now=now,
            inspector=FakeInspector(dirty=True),
        )
    os.chmod(authorization, 0o600)
    with pytest.raises(ValueError, match="0400"):
        harness.retrieve_authorized(
            authorization_file=authorization,
            transport=transport,
            now=now,
            inspector=FakeInspector(),
        )
    assert transport.calls == []


def test_authorization_expired_over_24_hours_allows_cleanup_but_never_network_or_retry(
    tmp_path,
):
    quarantine, audit = roots(tmp_path)
    now = harness.datetime.now(harness.UTC)
    issued = now - harness.timedelta(hours=27)
    payload = authorization_payload(quarantine, audit, issued)
    payload["expires_at"] = (issued + harness.timedelta(hours=1)).isoformat()
    authorization = write_authorization(tmp_path, payload)

    run_id = payload["run_id"]
    run_dir = quarantine / run_id
    run_dir.mkdir(mode=0o700)
    retained = run_dir / "package.zip"
    retained.write_bytes(b"quarantined fixture")
    os.chmod(retained, 0o400)
    (audit / f"{run_id}.spent").write_text("spent\n", encoding="utf-8")
    os.chmod(audit / f"{run_id}.spent", 0o400)
    (audit / f"{run_id}.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "retention_deadline": (now - harness.timedelta(seconds=1)).isoformat(),
                "states": [{"state": "succeeded", "at": issued.isoformat()}],
            }
        ),
        encoding="utf-8",
    )
    os.chmod(audit / f"{run_id}.json", 0o600)

    harness.cleanup_authorized(
        authorization_file=authorization,
        now=now,
        inspector=FakeInspector(dirty=True),
    )
    assert not run_dir.exists()
    assert (audit / f"{run_id}.spent").is_file()
    assert json.loads((audit / f"{run_id}.json").read_text())["states"][-1][
        "state"
    ] == "cleaned"

    transport = FakeTransport([])
    with pytest.raises(ValueError, match="currently valid"):
        harness.retrieve_authorized(
            authorization_file=authorization,
            transport=transport,
            now=now,
            inspector=FakeInspector(),
        )
    with pytest.raises(FileExistsError):
        harness._retrieve_once(
            run_id=run_id,
            quarantine_root=quarantine,
            audit_root=audit,
            transport=transport,
        )
    assert transport.calls == []
