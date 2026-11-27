"""Hash chain: how records are sealed and how a chain is verified.

A record is ``{"seq", "ts", "type", "data", "prev", "hash"}``. ``hash`` is the sha256 of
the canonical JSON of every other field, and ``prev`` is the previous record's hash
(``GENESIS`` for the first). Changing, removing or reordering any record breaks the
chain at that point. Removing records from the end does not, unless the expected head
hash is checked (see ``verify_records(expect_head=...)``).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from aeon._util import canonical_json, sha256_hex

GENESIS = "0" * 64
FIELDS = ("seq", "ts", "type", "data", "prev")


def record_hash(record: dict[str, Any]) -> str:
    """Return the sha256 hex digest of the canonical JSON of ``record``'s hashed fields."""
    return sha256_hex(canonical_json({k: record.get(k) for k in FIELDS}))


def seal(seq: int, ts: str, kind: str, data: Any, prev: str) -> dict[str, Any]:
    """Build a record of type ``kind`` linked to ``prev`` and stamp its hash."""
    record: dict[str, Any] = {"seq": seq, "ts": ts, "type": kind, "data": data, "prev": prev}
    record["hash"] = record_hash(record)
    return record


@dataclass
class VerifyReport:
    """Result of verifying a chain. ``first_bad_*`` point at the first broken link."""

    ok: bool
    records: int = 0
    head: str = GENESIS
    first_bad_seq: int | None = None
    first_bad_line: int | None = None
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    ts_regressions: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a plain dict."""
        return asdict(self)


class ParseFailure:
    """Placeholder yielded by a backend for a line it cannot decode."""

    def __init__(self, error: str) -> None:
        self.error = error


Entry = tuple[int, "dict[str, Any] | ParseFailure"]


def parse_jsonl(lines: Iterable[str]) -> Iterator[Entry]:
    """Yield ``(line number, record)`` per non-blank line, or a ``ParseFailure`` for bad lines."""
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            yield lineno, ParseFailure(f"invalid JSON: {exc.msg} at column {exc.colno}")
            continue
        if not isinstance(obj, dict):
            yield lineno, ParseFailure("record is not a JSON object")
            continue
        yield lineno, obj


def _link_failure(rec: dict[str, Any], prev: str, expected_seq: int) -> tuple[Any, str] | None:
    """Return ``(seq, reason)`` if ``rec`` does not extend the chain, else ``None``."""
    missing = [k for k in (*FIELDS, "hash") if k not in rec]
    if missing:
        return rec.get("seq"), f"missing fields: {', '.join(missing)}"
    seq = rec["seq"]
    if seq != expected_seq:
        return seq, f"sequence gap: expected {expected_seq}, found {seq}"
    if rec["prev"] != prev:
        return seq, "prev does not match the previous record's hash"
    if record_hash(rec) != rec["hash"]:
        return seq, "hash mismatch: record content was changed"
    return None


def verify_records(entries: Iterable[Entry], *, expect_head: str | None = None) -> VerifyReport:
    """Recompute the chain and stop at the first broken link."""
    report = VerifyReport(ok=True)
    prev = GENESIS
    expected_seq = 0
    last_ts: str | None = None

    def fail(lineno: int, seq: int | None, reason: str) -> VerifyReport:
        report.ok = False
        report.first_bad_line = lineno
        report.first_bad_seq = seq
        report.reason = reason
        return report

    for lineno, rec in entries:
        if isinstance(rec, ParseFailure):
            return fail(lineno, expected_seq, rec.error)
        broken = _link_failure(rec, prev, expected_seq)
        if broken is not None:
            return fail(lineno, *broken)
        ts = rec["ts"]
        if last_ts is not None and isinstance(ts, str) and ts < last_ts:
            report.ts_regressions += 1
        last_ts = ts if isinstance(ts, str) else last_ts
        prev = rec["hash"]
        expected_seq += 1
        report.records += 1

    report.head = prev
    if report.ts_regressions:
        report.warnings.append(
            f"{report.ts_regressions} timestamp(s) go backwards (clock skew?); "
            "order is defined by seq, not ts"
        )
    if expect_head is not None and expect_head != prev:
        report.ok = False
        report.reason = (
            f"head mismatch: expected {expect_head}, chain ends at {prev} "
            "(records were removed from the end, or the chain was rebuilt)"
        )
    return report
