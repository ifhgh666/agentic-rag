import json
import time
from threading import Event

import pytest

from app.observability.diagnostics import DiagnosticRecorder, LocalDiagnosticStore


def source(request_id="request-1"):
    return {"request_id": request_id, "thread_id": "thread-1", "original_question": "question",
            "model_trace": [{"input_messages": [{"content": "ORIGINAL_INPUT"}],
                             "candidate_content": "FIRST_REPLY", "api_key": "SECRET",
                             "private_reasoning": "PRIVATE_REASONING"}],
            "usage": {"model_calls": 2}, "status": "completed"}


def wait_status(recorder, receipt):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = recorder.status(receipt.job_id)
        if status is not None and status.status not in ("queued", "writing"):
            return status
        Event().wait(0.005)
    pytest.fail("Diagnostic worker did not finish within the test deadline")


class GatedStore:
    def __init__(self, delegate=None):
        self.entered = Event()
        self.release = Event()
        self.finished = Event()
        self.delegate = delegate
        self.snapshots = []

    def write(self, snapshot, job_id, closed):
        self.snapshots.append(snapshot)
        self.entered.set()
        try:
            if not self.release.wait(5):
                raise RuntimeError("Test did not release storage gate")
            if self.delegate:
                return self.delegate.write(snapshot, job_id, closed)
            return ("skipped", "closed") if closed.is_set() else ("saved", "saved")
        finally:
            self.finished.set()


def test_snapshot_is_detached_and_private_first_reply_remains_local(tmp_path):
    store = GatedStore(LocalDiagnosticStore(tmp_path / "traces"))
    recorder = DiagnosticRecorder(tmp_path, store=store)
    recorder.start()
    value = source()
    try:
        receipt = recorder.submit(value)
        assert receipt.status == "queued"
        assert store.entered.wait(3)
        value["model_trace"][0]["input_messages"][0]["content"] = "MUTATED"
        value["usage"]["model_calls"] = 999
        assert not (tmp_path / "traces/request-1.json").exists()
        store.release.set()
        assert wait_status(recorder, receipt).status == "saved"
        data = json.loads((tmp_path / "traces/request-1.json").read_text(encoding="utf-8"))
        assert data["model_trace"][0]["input_messages"][0]["content"] == "ORIGINAL_INPUT"
        assert data["model_trace"][0]["candidate_content"] == "FIRST_REPLY"
        assert data["usage"]["model_calls"] == 2
        assert "SECRET" not in json.dumps(data) and "PRIVATE_REASONING" not in json.dumps(data)
    finally:
        store.release.set()
        recorder.close()


class HostileDict(dict):
    def items(self):
        raise AssertionError("Must never invoke user items")

    def __iter__(self):
        raise AssertionError("Must never invoke user iterator")


class HostileList(list):
    def __iter__(self):
        raise AssertionError("Must never invoke user iterator")


class HostileObject:
    def __deepcopy__(self, memo):
        raise AssertionError("Must never invoke user deepcopy")

    def __str__(self):
        raise AssertionError("Must never invoke user string conversion")


@pytest.mark.parametrize("value", [HostileDict(), HostileList(), HostileObject(), (1,), {1: "bad"}])
def test_invalid_values_skip_without_invoking_custom_code(tmp_path, value):
    recorder = DiagnosticRecorder(tmp_path / "absent")
    recorder.start()
    try:
        receipt = recorder.submit({**source(), "usage": value})
        assert (receipt.status, receipt.reason) == ("skipped", "invalid_snapshot")
        assert not (tmp_path / "absent").exists()
    finally:
        recorder.close()


@pytest.mark.parametrize("kind", ["characters", "nodes", "depth", "cycle", "expired", "path", "top-level"])
def test_snapshot_limits_and_invalid_identifiers_are_whole_record_rejections(tmp_path, kind):
    value = source()
    expected = "snapshot_limit"
    deadline = None
    if kind == "characters":
        value["original_question"] = "x" * 2_000_001
    elif kind == "nodes":
        value["usage"] = [None] * 100_001
    elif kind == "depth":
        nested = []
        for _ in range(65):
            nested = [nested]
        value["usage"] = nested
    elif kind == "cycle":
        value["usage"] = value
        expected = "invalid_snapshot"
    elif kind == "expired":
        deadline = time.monotonic() - 1
        expected = "request_expired"
    elif kind == "path":
        value["request_id"] = "../escape"
        expected = "invalid_snapshot"
    else:
        value["unexpected"] = "body"
        expected = "invalid_snapshot"
    recorder = DiagnosticRecorder(tmp_path / "absent")
    recorder.start()
    try:
        receipt = recorder.submit(value, deadline=deadline)
        assert (receipt.status, receipt.reason) == ("skipped", expected)
        assert not (tmp_path / "absent").exists()
    finally:
        recorder.close()


def test_duplicate_jobs_have_separate_status_and_do_not_overwrite_evidence(tmp_path):
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        first = recorder.submit(source())
        assert wait_status(recorder, first).status == "saved"
        original = (tmp_path / "request-1.json").read_bytes()
        second = recorder.submit({**source(), "original_question": "different"})
        assert first.job_id != second.job_id
        assert wait_status(recorder, second).reason == "conflict"
        assert recorder.status(first.job_id).status == "saved"
        assert (tmp_path / "request-1.json").read_bytes() == original
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        recorder.close()


@pytest.mark.parametrize("fault", ["serialize", "write", "publish"])
def test_storage_failures_are_safe_and_leave_no_partial_final(tmp_path, monkeypatch, fault):
    from pathlib import Path
    import app.observability.diagnostics as module
    value = source()
    expected = fault + "_failed"
    if fault == "serialize":
        value["usage"] = {"number": float("nan")}
    elif fault == "write":
        monkeypatch.setattr(Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("PRIVATE_PATH")))
    else:
        monkeypatch.setattr(module.os, "rename" if module.os.name == "nt" else "link",
                            lambda *a: (_ for _ in ()).throw(OSError("PRIVATE_PATH")))
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        receipt = recorder.submit(value)
        result = wait_status(recorder, receipt)
        assert (result.status, result.reason) == ("failed", expected)
        assert "PRIVATE_PATH" not in repr(result)
        assert not list(tmp_path.glob("*.json")) and not list(tmp_path.glob("*.tmp"))
    finally:
        recorder.close()


def test_interrupted_write_cleans_only_its_temporary_file(tmp_path, monkeypatch):
    from pathlib import Path
    original = Path.open
    historical = tmp_path / ".historical.tmp"
    historical.write_bytes(b"preserve old failure evidence")

    class Interrupted:
        def __init__(self, path):
            self.stream = original(path, "x", encoding="utf-8")

        def __enter__(self):
            return self

        def write(self, content):
            self.stream.write(content[:10])
            raise OSError("PRIVATE_PARTIAL_WRITE")

        def __exit__(self, *args):
            self.stream.close()

    def open_file(path, mode="r", *args, **kwargs):
        return Interrupted(path) if mode == "x" else original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        receipt = recorder.submit(source())
        assert wait_status(recorder, receipt).reason == "write_failed"
        assert not (tmp_path / "request-1.json").exists()
        assert list(tmp_path.glob("*.tmp")) == [historical]
        assert historical.read_bytes() == b"preserve old failure evidence"
    finally:
        recorder.close()


def test_two_recorders_competing_for_one_final_name_preserve_the_winner(tmp_path):
    recorders = [DiagnosticRecorder(tmp_path), DiagnosticRecorder(tmp_path)]
    for recorder in recorders:
        recorder.start()
    try:
        receipts = [recorder.submit({**source(), "original_question": str(index)})
                    for index, recorder in enumerate(recorders)]
        results = [wait_status(recorder, receipt) for recorder, receipt in zip(recorders, receipts)]
        assert sorted(result.status for result in results) == ["failed", "saved"]
        winner = next(index for index, result in enumerate(results) if result.status == "saved")
        content = json.loads((tmp_path / "request-1.json").read_text(encoding="utf-8"))
        assert content["original_question"] == str(winner)
        assert next(result for result in results if result.status == "failed").reason == "conflict"
    finally:
        for recorder in recorders:
            recorder.close()


def test_published_record_stays_saved_if_own_temp_cleanup_fails(tmp_path, monkeypatch):
    from pathlib import Path
    original = Path.unlink

    def unlink(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise OSError("PRIVATE_CLEANUP")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        receipt = recorder.submit(source())
        assert wait_status(recorder, receipt).status == "saved"
        assert json.loads((tmp_path / "request-1.json").read_text(encoding="utf-8"))["status"] == "completed"
    finally:
        recorder.close()


@pytest.mark.parametrize("dimension", ["characters", "nodes", "depth"])
def test_exact_snapshot_boundary_is_accepted_and_one_more_is_rejected(tmp_path, dimension):
    if dimension == "characters":
        value = {"request_id": "r", "original_question": ""}
        overhead = sum(len(key) + len(item) for key, item in value.items())
        value["original_question"] = "x" * (2_000_000 - overhead)
        excessive = {**value, "original_question": value["original_question"] + "x"}
    elif dimension == "nodes":
        value = {"request_id": "r", "usage": [None] * 99_995}
        excessive = {**value, "usage": value["usage"] + [None]}
    else:
        nested = None
        for _ in range(63):
            nested = [nested]
        value = {"request_id": "r", "usage": nested}
        excessive = {**value, "usage": [nested]}
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        first = recorder.submit(value)
        assert first.status == "queued"
        assert wait_status(recorder, first).status == "saved"
        assert recorder.submit(excessive).reason == "snapshot_limit"
    finally:
        recorder.close()


def test_posix_link_publication_and_cleanup_failure_keep_complete_final(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    from types import SimpleNamespace
    import app.observability.diagnostics as module
    # Exercise the production POSIX branch with actual local hard links on NTFS.
    # Replace only this module's os reference, not the interpreter's platform.
    monkeypatch.setattr(module, "os", SimpleNamespace(name="posix", link=os.link))
    original_unlink = Path.unlink

    def unlink(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise OSError("PRIVATE_CLEANUP")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        first = recorder.submit(source())
        assert wait_status(recorder, first).status == "saved"
        original = (tmp_path / "request-1.json").read_bytes()
        assert json.loads(original)["request_id"] == "request-1"
        assert (tmp_path / f".{first.job_id}.tmp").read_bytes() == original
        second = recorder.submit(source())
        assert wait_status(recorder, second).reason == "conflict"
        assert (tmp_path / "request-1.json").read_bytes() == original
    finally:
        recorder.close()


def test_exclusive_temp_creation_does_not_remove_an_existing_file(tmp_path):
    from app.observability.diagnostics import DiagnosticSnapshot
    temporary = tmp_path / ".job-id.tmp"
    temporary.write_bytes(b"existing evidence")
    result = LocalDiagnosticStore(tmp_path).write(DiagnosticSnapshot(source()), "job-id", Event())
    assert result == ("failed", "write_failed")
    assert temporary.read_bytes() == b"existing evidence"
    assert not (tmp_path / "request-1.json").exists()


def test_custom_dictionary_key_is_rejected_before_any_equality_callback(tmp_path):
    class Key:
        def __hash__(self):
            return hash("request_id")

        def __eq__(self, other):
            pytest.fail("Snapshot must reject custom keys before dictionary lookup")

    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        assert recorder.submit({Key(): "bad"}).reason == "invalid_snapshot"
    finally:
        recorder.close()
