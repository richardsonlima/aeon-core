"""Sessions, run history and user memory in SQLite (standard library ``sqlite3``).

``SqliteDb`` keeps three things: the runs of each session (so a conversation can carry
on across processes), and the facts an agent saved about a user. It stores prompts and
answers in plain text: keep the file where only the operator can read it.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

__all__ = ["SqliteDb"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT,
    agent TEXT,
    user_id TEXT,
    input TEXT,
    output TEXT,
    status TEXT,
    tokens INTEGER,
    created REAL
);
CREATE INDEX IF NOT EXISTS runs_session ON runs (session_id, created);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    created REAL
);
CREATE INDEX IF NOT EXISTS memories_user ON memories (user_id);
"""


class SqliteDb:
    """A SQLite file for agent sessions and user memory. Safe to share across threads.

    Args:
        db_file: Path of the database file; parent directories are created.
    """

    def __init__(self, db_file: str | Path) -> None:
        self.path = Path(db_file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def __repr__(self) -> str:
        return f"SqliteDb({str(self.path)!r})"

    def close(self) -> None:
        """Close the connection."""
        with self._lock:
            self._conn.close()

    # -- runs --------------------------------------------------------------------------

    def add_run(
        self,
        *,
        run_id: str,
        session_id: str,
        agent: str,
        user_id: str | None,
        input: str,  # noqa: A002 - mirrors the run field
        output: str | None,
        status: str,
        tokens: int,
    ) -> None:
        """Record one finished run of a session."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, session_id, agent, user_id, input, output, status, tokens, time.time()),
            )
            self._conn.commit()

    def get_runs(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        """The runs of a session, oldest first; ``limit`` keeps only the latest ones."""
        sql = "SELECT run_id, agent, user_id, input, output, status, tokens, created FROM runs"
        sql += " WHERE session_id = ? ORDER BY created DESC, rowid DESC"
        params: tuple[Any, ...] = (session_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params += (limit,)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        keys = ("run_id", "agent", "user_id", "input", "output", "status", "tokens", "created")
        return [dict(zip(keys, r, strict=True)) for r in reversed(rows)]

    def sessions(self, agent: str | None = None) -> list[str]:
        """Session ids, most recent first, optionally for one agent."""
        sql = "SELECT session_id, MAX(created) AS last FROM runs"
        params: tuple[Any, ...] = ()
        if agent is not None:
            sql += " WHERE agent = ?"
            params = (agent,)
        sql += " GROUP BY session_id ORDER BY last DESC"
        with self._lock:
            return [r[0] for r in self._conn.execute(sql, params).fetchall()]

    # -- user memory -------------------------------------------------------------------

    def add_memory(self, user_id: str, memory: str) -> None:
        """Save one fact about a user."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO memories (user_id, memory, created) VALUES (?, ?, ?)",
                (user_id, memory, time.time()),
            )
            self._conn.commit()

    def get_memories(self, user_id: str) -> list[str]:
        """Every fact saved about a user, oldest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT memory FROM memories WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        return [r[0] for r in rows]

    def clear_memories(self, user_id: str) -> int:
        """Delete every fact about a user. Returns how many were deleted."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            self._conn.commit()
            return cur.rowcount

    def export(self) -> str:
        """Every run and memory as JSON, for backup or inspection."""
        with self._lock:
            runs = self._conn.execute("SELECT * FROM runs ORDER BY created").fetchall()
            mems = self._conn.execute("SELECT * FROM memories ORDER BY id").fetchall()
        return json.dumps({"runs": runs, "memories": mems}, default=str)
