"""Storage backends for the audit chain: JSONL (default), SQLite and in-memory."""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

from aeon.audit.chain import Entry, ParseFailure, parse_jsonl


class Backend(Protocol):
    """Append-only storage. Only the audit writer thread calls ``append``."""

    def head(self) -> tuple[int, str] | None:
        """Return ``(seq, hash)`` of the last stored record, or ``None`` if empty."""
        ...

    def append(self, records: list[dict[str, Any]]) -> None:
        """Store ``records`` in order. Must be all-or-nothing from the caller's view."""
        ...

    def entries(self) -> Iterator[Entry]:
        """Yield ``(line number, record)`` for each stored record, oldest first."""
        ...

    def close(self) -> None:
        """Release any open handle. Safe to call more than once."""
        ...

    @property
    def location(self) -> str:
        """Human-readable place the records live (a path, ``sqlite:<path>`` or ``memory``)."""
        ...


class MemoryBackend:
    """Keeps records in a list. For tests and ephemeral gates; nothing is persisted."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def location(self) -> str:
        """Always ``"memory"``."""
        return "memory"

    def head(self) -> tuple[int, str] | None:
        """Return ``(seq, hash)`` of the last record, or ``None`` if empty."""
        with self._lock:
            return (self.records[-1]["seq"], self.records[-1]["hash"]) if self.records else None

    def append(self, records: list[dict[str, Any]]) -> None:
        """Store a JSON-normalised copy of each record."""
        with self._lock:
            self.records.extend(json.loads(json.dumps(r, default=str)) for r in records)

    def entries(self) -> Iterator[Entry]:
        """Yield a snapshot of the records, numbered from 1."""
        with self._lock:
            snapshot = list(self.records)
        yield from enumerate(snapshot, start=1)

    def close(self) -> None:
        """Do nothing; there is no handle to release."""
        pass


class JsonlBackend:
    """One JSON record per line. ``fsync=True`` makes each batch durable before returning."""

    def __init__(self, path: str | os.PathLike[str], *, fsync: bool = False) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self._fh: Any = None

    @property
    def location(self) -> str:
        """The file path as a string."""
        return str(self.path)

    def head(self) -> tuple[int, str] | None:
        """Return ``(seq, hash)`` from the last line of the file, or ``None``.

        Raises:
            RuntimeError: The last line is not a valid record (the file was edited or truncated).
        """
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        last = _last_line(self.path)
        if last is None:
            return None
        try:
            rec = json.loads(last)
            return int(rec["seq"]), str(rec["hash"])
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(
                f"cannot append to {self.path}: last line is not a valid record ({exc}); "
                "run `aeon audit verify` to find the damage"
            ) from exc

    def append(self, records: list[dict[str, Any]]) -> None:
        """Append one line per record, flushing (and fsyncing if enabled) before returning."""
        if self._fh is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "a", encoding="utf-8")  # noqa: SIM115
        data = "".join(
            json.dumps(r, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"
            for r in records
        )
        self._fh.write(data)
        self._fh.flush()
        if self.fsync:
            os.fsync(self._fh.fileno())

    def entries(self) -> Iterator[Entry]:
        """Yield each line of the file as a record or a ``ParseFailure``."""
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8", errors="replace") as fh:
            yield from parse_jsonl(fh)

    def close(self) -> None:
        """Close the file handle if one is open."""
        if self._fh is not None:
            with contextlib.suppress(OSError):
                self._fh.close()
            self._fh = None


def _last_line(path: Path) -> str | None:
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        end = fh.tell()
        block = 4096
        buf = b""
        pos = end
        while pos > 0:
            step = min(block, pos)
            pos -= step
            fh.seek(pos)
            buf = fh.read(step) + buf
            lines = buf.rstrip(b"\n").split(b"\n")
            if len(lines) > 1 or pos == 0:
                last = lines[-1].strip()
                return last.decode("utf-8", errors="replace") if last else None
    return None


class SqliteBackend:
    """Records in a single table. The chain is still verified from the stored JSON."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    @property
    def location(self) -> str:
        """``sqlite:`` followed by the database path."""
        return f"sqlite:{self.path}"

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, hash TEXT NOT NULL, "
                "body TEXT NOT NULL)"
            )
            conn.commit()
            self._conn = conn
        return self._conn

    def head(self) -> tuple[int, str] | None:
        """Return ``(seq, hash)`` of the highest ``seq`` row, or ``None`` if empty."""
        with self._lock:
            row = (
                self._db()
                .execute("SELECT seq, hash FROM audit ORDER BY seq DESC LIMIT 1")
                .fetchone()
            )
        return (int(row[0]), str(row[1])) if row else None

    def append(self, records: list[dict[str, Any]]) -> None:
        """Insert the records in one transaction."""
        rows = [
            (r["seq"], r["hash"], json.dumps(r, ensure_ascii=False, default=str)) for r in records
        ]
        with self._lock:
            db = self._db()
            with db:
                db.executemany("INSERT INTO audit (seq, hash, body) VALUES (?, ?, ?)", rows)

    def entries(self) -> Iterator[Entry]:
        """Yield stored records in ``seq`` order, or a ``ParseFailure`` for an undecodable row."""
        if not self.path.exists():
            return
        with self._lock:
            rows = self._db().execute("SELECT seq, body FROM audit ORDER BY seq").fetchall()
        for i, (_seq, body) in enumerate(rows, start=1):
            try:
                obj = json.loads(body)
            except json.JSONDecodeError as exc:
                yield i, ParseFailure(f"invalid JSON in row {i}: {exc.msg}")
                continue
            yield i, obj

    def close(self) -> None:
        """Close the connection if one is open."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


def open_backend(spec: str | os.PathLike[str], *, fsync: bool = False) -> Backend:
    """``memory``, ``sqlite:<path>``, a path ending in ``.db``/``.sqlite``, or a JSONL path."""
    s = str(spec)
    if s == "memory":
        return MemoryBackend()
    if s.startswith("sqlite:"):
        return SqliteBackend(s[len("sqlite:") :])
    if s.endswith((".db", ".sqlite", ".sqlite3")):
        return SqliteBackend(s)
    return JsonlBackend(s, fsync=fsync)
