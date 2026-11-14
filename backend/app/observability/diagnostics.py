"""Bounded diagnostic handoff; storage has no authority over answer delivery."""
from collections import OrderedDict, deque
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from threading import Condition, Event, Thread, current_thread
import time
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class DiagnosticStatus:
    job_id: str
    request_id: str
    thread_id: str
    status: str
    reason: str
    updated_at: float


DiagnosticReceipt = DiagnosticStatus


@dataclass(frozen=True)
class DiagnosticSnapshot:
    data: dict


class DiagnosticStore(Protocol):
    def write(self, snapshot: DiagnosticSnapshot, job_id: str, closed: Event) -> tuple[str, str]: ...


_FIELDS = frozenset(("request_id", "thread_id", "original_question", "model_trace", "execution_trace",
                     "retrieval_batches", "evidence_registry", "status", "stop_reason", "usage"))
_PRIVATE_FIELDS = frozenset(("api_key", "apikey", "authorization", "password", "secret", "jwt_secret",
                            "token", "access_token", "private_reasoning", "reasoning", "thoughts",
                            "chain_of_thought"))
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_STORE_RESULTS = frozenset((("saved", "saved"), ("skipped", "closed"),
    ("failed", "serialize_failed"), ("failed", "write_failed"),
    ("failed", "conflict"), ("failed", "publish_failed")))


class _SnapshotRejected(Exception):
    pass


def _snapshot(source: dict, deadline: float | None) -> DiagnosticSnapshot:
    nodes = chars = 0
    active = set()

    def copy(value, depth):
        nonlocal nodes, chars
        if deadline is not None and time.monotonic() >= deadline:
            raise _SnapshotRejected("request_expired")
        nodes += 1
        if nodes > 100_000 or depth > 64:
            raise _SnapshotRejected("snapshot_limit")
        kind = type(value)
        if kind is str:
            chars += len(value)
            if chars > 2_000_000:
                raise _SnapshotRejected("snapshot_limit")
            return value
        if value is None or kind in (bool, int, float):
            return value
        if kind not in (dict, list):
            raise _SnapshotRejected("invalid_snapshot")
        if id(value) in active:
            raise _SnapshotRejected("invalid_snapshot")
        if len(value) > 100_000 - nodes:
            raise _SnapshotRejected("snapshot_limit")
        active.add(id(value))
        try:
            if kind is list:
                return [copy(item, depth + 1) for item in value]
            result = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise _SnapshotRejected("invalid_snapshot")
                copy(key, depth + 1)
                normalized = key.strip().lower().replace("-", "_")
                if normalized in _PRIVATE_FIELDS or any(part in normalized for part in
                                                       ("api_key", "authorization", "password", "reasoning")):
                    continue
                result[key] = copy(item, depth + 1)
            return result
        finally:
            active.remove(id(value))

    if type(source) is not dict or len(source) > len(_FIELDS):
        raise _SnapshotRejected("invalid_snapshot")
    for key in source:
        if type(key) is not str or key not in _FIELDS:
            raise _SnapshotRejected("invalid_snapshot")
    data = copy(source, 0)
    request_id = data.get("request_id")
    if type(request_id) is not str or not _IDENTIFIER.fullmatch(request_id):
        raise _SnapshotRejected("invalid_snapshot")
    if type(data.get("thread_id", "")) is not str:
        raise _SnapshotRejected("invalid_snapshot")
    return DiagnosticSnapshot(data)


class LocalDiagnosticStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def write(self, snapshot: DiagnosticSnapshot, job_id: str, closed: Event) -> tuple[str, str]:
        # Serialize before creating anything, and never publish a partial JSON file.
        if closed.is_set():
            return "skipped", "closed"
        try:
            content = json.dumps(snapshot.data, ensure_ascii=False, indent=2, allow_nan=False)
        except Exception:
            return ("skipped", "closed") if closed.is_set() else ("failed", "serialize_failed")
        if closed.is_set():
            return "skipped", "closed"
        temporary = self.directory / f".{job_id}.tmp"
        final = self.directory / f"{snapshot.data['request_id']}.json"
        owned = False
        try:
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
                with temporary.open("x", encoding="utf-8") as stream:
                    owned = True
                    stream.write(content)
                    stream.flush()
            except Exception:
                return ("skipped", "closed") if closed.is_set() else ("failed", "write_failed")
            if closed.is_set():
                return "skipped", "closed"
            try:
                if os.name == "nt":
                    os.rename(temporary, final)
                else:
                    os.link(temporary, final)
            except FileExistsError:
                return "failed", "conflict"
            except Exception:
                return "failed", "publish_failed"
            return "saved", "saved"
        finally:
            if owned:
                try:
                    temporary.unlink(missing_ok=True)
                except Exception:
                    # A published final file remains saved even if temp cleanup fails.
                    pass


class DiagnosticRecorder:
    def __init__(self, directory: Path, *, enabled: bool = True, store: DiagnosticStore | None = None):
        self._enabled = enabled
        self._store = store if store is not None else LocalDiagnosticStore(directory)
        self._condition = Condition()
        self._closed = Event()
        self._thread: Thread | None = None
        self._pending = deque()
        self._statuses = OrderedDict()

    def start(self) -> None:
        with self._condition:
            if not self._enabled or self._closed.is_set() or self._thread is not None:
                return
            try:
                worker = Thread(target=self._work, name="diagnostic-recorder", daemon=True)
                worker.start()
                self._thread = worker
            except Exception:
                self._closed.set()

    def _remember(self, receipt: DiagnosticStatus) -> DiagnosticStatus:
        self._statuses[receipt.job_id] = receipt
        while len(self._statuses) > 256:
            self._statuses.popitem(last=False)
        return receipt

    def submit(self, snapshot_source: dict, *, deadline: float | None = None) -> DiagnosticReceipt:
        job_id = str(uuid4())
        request_id = thread_id = ""
        if (type(snapshot_source) is dict and len(snapshot_source) <= len(_FIELDS)
                and all(type(key) is str for key in snapshot_source)):
            for key in ("request_id", "thread_id"):
                value = snapshot_source.get(key)
                if type(value) is str and len(value) <= 128 and _IDENTIFIER.fullmatch(value):
                    if key == "request_id":
                        request_id = value
                    else:
                        thread_id = value

        def receipt(status, reason):
            return DiagnosticStatus(job_id, request_id, thread_id, status, reason, time.monotonic())

        def unavailable():
            if not self._enabled:
                return "disabled"
            if self._closed.is_set() or self._thread is None:
                return "closed"
            if len(self._pending) >= 8:
                return "queue_full"
            return None

        with self._condition:
            reason = unavailable()
            if reason:
                return self._remember(receipt("skipped", reason))
        try:
            snapshot = _snapshot(snapshot_source, deadline)
        except _SnapshotRejected as exc:
            with self._condition:
                return self._remember(receipt("skipped", exc.args[0]))
        except Exception:
            with self._condition:
                return self._remember(receipt("skipped", "invalid_snapshot"))
        with self._condition:
            reason = unavailable()
            if reason:
                return self._remember(receipt("skipped", reason))
            result = self._remember(receipt("queued", "accepted"))
            self._pending.append((snapshot, result))
            self._condition.notify()
            return result

    def status(self, job_id: str) -> DiagnosticStatus | None:
        with self._condition:
            return self._statuses.get(job_id)

    def _update(self, receipt: DiagnosticStatus, status: str, reason: str) -> None:
        if receipt.job_id in self._statuses:
            self._statuses[receipt.job_id] = DiagnosticStatus(receipt.job_id, receipt.request_id,
                receipt.thread_id, status, reason, time.monotonic())

    def _work(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._pending or self._closed.is_set())
                if self._closed.is_set():
                    return
                snapshot, receipt = self._pending.popleft()
                self._update(receipt, "writing", "accepted")
            try:
                status, reason = self._store.write(snapshot, receipt.job_id, self._closed)
                if (status, reason) not in _STORE_RESULTS:
                    status, reason = "failed", "write_failed"
            except Exception:
                status, reason = "failed", "write_failed"
            with self._condition:
                self._update(receipt, status, reason)

    def close(self, timeout: float = 1.0) -> None:
        with self._condition:
            self._closed.set()
            while self._pending:
                _, receipt = self._pending.popleft()
                self._update(receipt, "skipped", "closed")
            self._condition.notify_all()
            worker = self._thread
        if worker is not None and worker is not current_thread():
            worker.join(timeout=max(0.0, min(timeout, 1.0)))
