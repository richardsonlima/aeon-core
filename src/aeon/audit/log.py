"""The asynchronous audit log.

``emit`` only stamps the event and puts it on a bounded queue, so the decision path never
waits on storage. A single writer thread seals records into the hash chain and appends
them to the backend. If the backend fails, records stay pending (bounded) and the writer
retries with backoff; when it recovers it first writes an ``audit.backend_error`` record,
so the outage itself is part of the chain. Events that do not fit in the queue are
counted and reported in an ``audit.gap`` record.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from aeon._util import utc_now_iso
from aeon.audit.backends import Backend, open_backend
from aeon.audit.chain import GENESIS, VerifyReport, seal, verify_records
import contextlib


@dataclass
class AuditStats:
    emitted: int = 0
    written: int = 0
    dropped: int = 0
    backend_errors: int = 0
    last_error: str | None = None
    lag_ms_last: float = 0.0
    lag_ms_max: float = 0.0
    lag_samples: deque[float] = field(default_factory=lambda: deque(maxlen=10_000))

    def to_dict(self) -> dict[str, Any]:
        return {
            "emitted": self.emitted,
            "written": self.written,
            "dropped": self.dropped,
            "backend_errors": self.backend_errors,
            "last_error": self.last_error,
            "lag_ms_last": round(self.lag_ms_last, 4),
            "lag_ms_max": round(self.lag_ms_max, 4),
        }


_STOP = object()


class AuditLog:
    """Append-only, hash-chained, written off the decision path by one background thread."""

    def __init__(
        self,
        backend: Backend | str | os.PathLike[str] = ".aeon/audit.jsonl",
        *,
        maxsize: int = 10_000,
        batch: int = 256,
        retry_max_s: float = 5.0,
        fsync: bool = False,
    ) -> None:
        self.backend: Backend = (
            open_backend(backend, fsync=fsync)
            if isinstance(backend, (str, os.PathLike))
            else backend
        )
        self.stats = AuditStats()
        self._q: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._pending: list[tuple[float, str, str, dict[str, Any]]] = []
        self._reported_dropped = 0
        self._pending_max = maxsize
        self._batch = batch
        self._retry_max = retry_max_s
        self._seq: int | None = None
        self._prev = GENESIS
        self._unflushed = 0
        self._cond = threading.Condition()
        self._lock = threading.Lock()
        self._closed = False
        self._outage: dict[str, Any] | None = None
        self._thread = threading.Thread(target=self._run, name="aeon-audit", daemon=True)
        self._thread.start()

    # -- decision-path side --------------------------------------------------------------

    def emit(self, type: str, data: Mapping[str, Any]) -> None:
        """Queue an event. Never blocks; a full queue drops the event and counts it."""
        if self._closed:
            self.stats.dropped += 1
            return
        item = (time.perf_counter(), utc_now_iso(), type, dict(data))
        with self._lock:  # count before queueing so the writer can never settle it first
            self._unflushed += 1
            self.stats.emitted += 1
        try:
            self._q.put_nowait(item)
        except queue.Full:
            with self._lock:
                self._unflushed -= 1
                self.stats.emitted -= 1
                self.stats.dropped += 1

    # -- writer thread -------------------------------------------------------------------

    def _init_head(self) -> None:
        head = self.backend.head()
        if head is None:
            self._seq, self._prev = 0, GENESIS
        else:
            self._seq, self._prev = head[0] + 1, head[1]

    def _seal(self, ts: str, type: str, data: Mapping[str, Any]) -> dict[str, Any]:
        assert self._seq is not None
        rec = seal(self._seq, ts, type, dict(data), self._prev)
        self._seq += 1
        self._prev = rec["hash"]
        return rec

    def _run(self) -> None:
        backoff = 0.05
        stopping = False
        while True:
            if not stopping:
                try:
                    first = self._q.get(timeout=0.05 if self._pending else 0.25)
                except queue.Empty:
                    first = None
                if first is _STOP:
                    stopping = True
                elif first is not None:
                    self._pending.append(first)
            while len(self._pending) < self._batch * 4:
                try:
                    item = self._q.get_nowait()
                except queue.Empty:
                    break
                if item is _STOP:
                    stopping = True
                    break
                self._pending.append(item)
            if not self._pending:
                if stopping:
                    return
                continue
            if self._write():
                backoff = 0.05
                continue
            if stopping and backoff >= self._retry_max:
                return  # give up on shutdown; pending events are lost and were counted
            time.sleep(backoff)
            backoff = min(backoff * 2, self._retry_max)

    def _write(self) -> bool:
        """Seal pending events and append them. On failure nothing is consumed."""
        try:
            if self._seq is None:
                self._init_head()
        except Exception as exc:
            self._fail(exc)
            return False
        assert self._seq is not None
        seq0, prev0 = self._seq, self._prev
        events = self._pending[: self._batch]
        sealed: list[dict[str, Any]] = []
        if self._outage is not None:
            sealed.append(self._seal(utc_now_iso(), "audit.backend_error", self._outage))
        with self._lock:
            dropped = self.stats.dropped
        if dropped > self._reported_dropped:
            sealed.append(
                self._seal(
                    utc_now_iso(),
                    "audit.gap",
                    {"dropped_total": dropped, "reason": "queue full; events were not recorded"},
                )
            )
        sealed.extend(self._seal(ts, type_, data) for (_t0, ts, type_, data) in events)
        try:
            self.backend.append(sealed)
        except Exception as exc:
            self._seq, self._prev = seq0, prev0
            self._fail(exc)
            return False

        del self._pending[: len(events)]
        self._outage = None
        self._reported_dropped = dropped
        now = time.perf_counter()
        with self._lock:
            for t0, *_ in events:
                lag = (now - t0) * 1e3
                self.stats.lag_samples.append(lag)
                self.stats.lag_ms_last = lag
                self.stats.lag_ms_max = max(self.stats.lag_ms_max, lag)
            self.stats.written += len(sealed)
        self._settle(len(events))
        return True

    def _fail(self, exc: Exception) -> None:
        err = f"{type(exc).__name__}: {exc}"
        with self._lock:
            self.stats.backend_errors += 1
            self.stats.last_error = err
        if self._outage is None:
            self._outage = {"first_error": err, "since": utc_now_iso(), "failures": 0}
        self._outage["failures"] += 1
        self._outage["last_error"] = err
        overflow = len(self._pending) - self._pending_max
        if overflow > 0:  # bound memory while the backend is down: drop the oldest
            del self._pending[:overflow]
            with self._lock:
                self.stats.dropped += overflow
            self._settle(overflow)

    def _settle(self, n: int) -> None:
        with self._cond:
            with self._lock:
                self._unflushed = max(0, self._unflushed - n)
            self._cond.notify_all()

    # -- control -------------------------------------------------------------------------

    @property
    def healthy(self) -> bool:
        return self._outage is None

    @property
    def pending(self) -> int:
        return self._unflushed

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait until everything emitted so far is durable. Returns False on timeout."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self._unflushed > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(min(remaining, 0.05))
        return True

    def close(self, timeout: float = 5.0) -> None:
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(queue.Full):
            self._q.put(_STOP, timeout=timeout)
        self._thread.join(timeout)
        with self._lock:
            if self._unflushed:  # could not be written before shutdown
                self.stats.dropped += self._unflushed
                self.stats.last_error = self.stats.last_error or "closed with unwritten events"
                self._unflushed = 0
        self.backend.close()

    def __enter__(self) -> AuditLog:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- reading -------------------------------------------------------------------------

    def verify(self, expect_head: str | None = None) -> VerifyReport:
        return verify_records(self.backend.entries(), expect_head=expect_head)

    def records(self) -> Iterator[dict[str, Any]]:
        for _, rec in self.backend.entries():
            if isinstance(rec, dict):
                yield rec


def verify(spec: str | os.PathLike[str], expect_head: str | None = None) -> VerifyReport:
    """Verify the chain stored at ``spec`` (a JSONL path, ``sqlite:<path>`` or ``.db`` path)."""
    backend = open_backend(spec)
    try:
        return verify_records(backend.entries(), expect_head=expect_head)
    finally:
        backend.close()


def read(spec: str | os.PathLike[str]) -> Iterator[dict[str, Any]]:
    backend = open_backend(spec)
    try:
        for _, rec in backend.entries():
            if isinstance(rec, dict):
                yield rec
    finally:
        backend.close()
