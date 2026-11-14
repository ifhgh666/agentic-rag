from threading import Event, Thread

from fastapi.testclient import TestClient

from app.main import create_app
from app.observability.diagnostics import DiagnosticRecorder, LocalDiagnosticStore
from tests.unit.test_diagnostics import GatedStore, source, wait_status


def test_constructor_disabled_unstarted_and_closed_do_not_access_disk(tmp_path):
    for enabled, start, reason in ((False, True, "disabled"), (True, False, "closed")):
        recorder = DiagnosticRecorder(tmp_path / "absent", enabled=enabled)
        if start:
            recorder.start()
        assert recorder.submit(source()).reason == reason
        recorder.close()
        recorder.start()
        assert recorder.submit(source()).status == "skipped"
    assert not (tmp_path / "absent").exists()


def test_queue_capacity_close_and_late_worker_have_no_publish_authority(tmp_path):
    store = GatedStore(LocalDiagnosticStore(tmp_path))
    recorder = DiagnosticRecorder(tmp_path, store=store)
    recorder.start()
    try:
        active = recorder.submit(source("active"))
        assert store.entered.wait(3)
        assert recorder.status(active.job_id).status == "writing"
        waiting = [recorder.submit(source(f"pending-{i}")) for i in range(8)]
        assert all(receipt.status == "queued" for receipt in waiting)
        assert recorder.submit(source("overflow")).reason == "queue_full"
        closed = Event()
        closer = Thread(target=lambda: (recorder.close(), closed.set()))
        closer.start()
        assert closed.wait(2), "Default close must return without waiting for the blocked store"
        assert not store.release.is_set()
        assert all(recorder.status(item.job_id).reason == "closed" for item in waiting)
        assert recorder.submit(source()).reason == "closed"
        store.release.set()
        assert wait_status(recorder, active).reason == "closed"
        assert not list(tmp_path.glob("*.json"))
        closer.join(1)
        recorder.close()
    finally:
        store.release.set()
        recorder.close()


def test_status_retention_is_bounded_by_job_identity(tmp_path):
    recorder = DiagnosticRecorder(tmp_path, enabled=False)
    receipts = [recorder.submit(source()) for _ in range(257)]
    assert len({receipt.job_id for receipt in receipts}) == 257
    assert recorder.status(receipts[0].job_id) is None
    assert recorder.status(receipts[1].job_id).reason == "disabled"
    assert recorder.status(receipts[-1].job_id).reason == "disabled"
    recorder.close()


def test_lifespan_starts_and_stops_the_injected_recorder(settings):
    app = create_app(settings)
    recorder = app.state.services.diagnostics
    assert app.state.services.pipeline.diagnostics is recorder
    assert recorder.submit(source()).reason == "closed"
    with TestClient(app):
        receipt = recorder.submit(source())
        assert receipt.status == "queued"
        assert wait_status(recorder, receipt).status == "saved"
    assert recorder.submit(source()).reason == "closed"


def test_worker_start_failure_disables_diagnostics_without_failing_the_app(tmp_path, monkeypatch):
    import app.observability.diagnostics as module

    def fail_start(self):
        raise RuntimeError("PRIVATE_THREAD_START_FAILURE")

    recorder = DiagnosticRecorder(tmp_path / "absent")
    monkeypatch.setattr(module.Thread, "start", fail_start)
    recorder.start()
    assert recorder.submit(source()).reason == "closed"
    recorder.close()
    assert not (tmp_path / "absent").exists()


def test_close_after_entering_publish_records_the_actual_completed_publication(tmp_path, monkeypatch):
    import app.observability.diagnostics as module
    publish_entered, release_publish = Event(), Event()
    original = module.os.rename if module.os.name == "nt" else module.os.link

    def publish(temporary, final):
        publish_entered.set()
        assert release_publish.wait(5)
        return original(temporary, final)

    monkeypatch.setattr(module.os, "rename" if module.os.name == "nt" else "link", publish)
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        receipt = recorder.submit(source())
        assert publish_entered.wait(3)
        recorder.close(timeout=0)
        assert recorder.submit(source()).reason == "closed"
        release_publish.set()
        assert wait_status(recorder, receipt).status == "saved"
        assert (tmp_path / "request-1.json").is_file()
    finally:
        release_publish.set()
        recorder.close()


def test_close_during_failed_write_discards_the_unpublished_job(tmp_path, monkeypatch):
    from pathlib import Path
    entered, release = Event(), Event()
    original = Path.open

    class InterruptedWrite:
        def __init__(self, path):
            self.stream = original(path, "x", encoding="utf-8")

        def __enter__(self):
            return self

        def write(self, content):
            entered.set()
            assert release.wait(5)
            raise OSError("PRIVATE_DISK_FAILURE_AFTER_CLOSE")

        def __exit__(self, *args):
            self.stream.close()

    monkeypatch.setattr(Path, "open", lambda path, mode="r", *a, **kw:
                        InterruptedWrite(path) if mode == "x" else original(path, mode, *a, **kw))
    recorder = DiagnosticRecorder(tmp_path)
    recorder.start()
    try:
        receipt = recorder.submit(source())
        assert entered.wait(3)
        recorder.close(timeout=0)
        release.set()
        result = wait_status(recorder, receipt)
        assert (result.status, result.reason) == ("skipped", "closed")
        assert not list(tmp_path.glob("*.json")) and not list(tmp_path.glob("*.tmp"))
    finally:
        release.set()
        recorder.close()
