from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from aeon.audit import (
    GENESIS,
    AuditLog,
    JsonlBackend,
    MemoryBackend,
    SqliteBackend,
    open_backend,
    read,
    seal,
    verify,
    verify_records,
)
from aeon.axioms import Action, Gate
from aeon.axioms.builtin import deny_tools


def write(log: AuditLog, n: int, type: str = "decision") -> None:
    for i in range(n):
        log.emit(type, {"i": i})
    assert log.flush(5)


@pytest.mark.parametrize("spec", ["a.jsonl", "sqlite:a.db", "a.db"])
def test_chain_roundtrip(tmp_path: Path, spec: str) -> None:
    full = spec.replace("a.", str(tmp_path / "a."))
    with AuditLog(full) as log:
        write(log, 25)
    report = verify(full)
    assert report.ok and report.records == 25 and report.head != GENESIS
    recs = list(read(full))
    assert [r["seq"] for r in recs] == list(range(25))
    assert recs[0]["prev"] == GENESIS
    assert all(recs[i]["prev"] == recs[i - 1]["hash"] for i in range(1, 25))


def test_chain_continues_across_reopen(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        write(log, 3)
    with AuditLog(p) as log:
        write(log, 2)
    r = verify(p)
    assert r.ok and r.records == 5


def lines(p: Path) -> list[str]:
    return p.read_text().splitlines()


def tamper(p: Path, idx: int, fn: Any) -> None:
    ls = lines(p)
    ls[idx] = fn(ls[idx])
    p.write_text("\n".join(ls) + "\n")


@pytest.fixture
def chain(tmp_path: Path) -> Path:
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        write(log, 10)
    return p


def test_detects_modified_record(chain: Path) -> None:
    def edit(line: str) -> str:
        r = json.loads(line)
        r["data"]["i"] = 999
        return json.dumps(r)

    tamper(chain, 4, edit)
    r = verify(chain)
    assert not r.ok and r.first_bad_seq == 4 and r.first_bad_line == 5
    assert "hash mismatch" in (r.reason or "")


def test_detects_rehashed_record(chain: Path) -> None:
    """Recomputing the edited record's hash breaks the next link instead."""

    def edit(line: str) -> str:
        r = json.loads(line)
        return json.dumps(seal(r["seq"], r["ts"], r["type"], {"i": -1}, r["prev"]))

    tamper(chain, 4, edit)
    r = verify(chain)
    assert not r.ok and r.first_bad_seq == 5 and "prev" in (r.reason or "")


def test_detects_deleted_record(chain: Path) -> None:
    ls = lines(chain)
    del ls[3]
    chain.write_text("\n".join(ls) + "\n")
    r = verify(chain)
    assert not r.ok and r.first_bad_seq == 4 and "sequence gap" in (r.reason or "")


def test_detects_reordered_records(chain: Path) -> None:
    ls = lines(chain)
    ls[2], ls[3] = ls[3], ls[2]
    chain.write_text("\n".join(ls) + "\n")
    r = verify(chain)
    assert not r.ok and r.first_bad_line == 3


def test_detects_corrupted_line(chain: Path) -> None:
    tamper(chain, 6, lambda s: s[: len(s) // 2])
    r = verify(chain)
    assert not r.ok and r.first_bad_line == 7 and "invalid JSON" in (r.reason or "")


def test_detects_missing_fields(chain: Path) -> None:
    tamper(chain, 0, lambda s: json.dumps({k: v for k, v in json.loads(s).items() if k != "prev"}))
    r = verify(chain)
    assert not r.ok and r.first_bad_line == 1 and "missing fields: prev" in (r.reason or "")


def test_truncation_needs_expected_head(chain: Path) -> None:
    head = verify(chain).head
    ls = lines(chain)
    chain.write_text("\n".join(ls[:-2]) + "\n")
    assert verify(chain).ok  # a truncated chain is still a valid chain...
    r = verify(chain, expect_head=head)
    assert not r.ok and "head mismatch" in (r.reason or "")  # ...unless the head is anchored


def test_sqlite_tamper_detected(tmp_path: Path) -> None:
    import sqlite3

    p = tmp_path / "a.db"
    with AuditLog(SqliteBackend(p)) as log:
        write(log, 5)
    con = sqlite3.connect(p)
    body = json.loads(con.execute("SELECT body FROM audit WHERE seq=2").fetchone()[0])
    body["data"]["i"] = 42
    con.execute("UPDATE audit SET body=? WHERE seq=2", (json.dumps(body),))
    con.commit()
    con.close()
    r = verify(f"sqlite:{p}")
    assert not r.ok and r.first_bad_seq == 2


def test_clock_skew_is_a_warning_not_a_failure() -> None:
    recs, prev = [], GENESIS
    for i, ts in enumerate(
        ["2026-01-01T00:00:02Z", "2026-01-01T00:00:01Z", "2026-01-01T00:00:03Z"]
    ):
        r = seal(i, ts, "decision", {}, prev)
        prev = r["hash"]
        recs.append((i + 1, r))
    report = verify_records(recs)
    assert report.ok and report.ts_regressions == 1 and report.warnings


def test_append_refuses_on_damaged_tail(chain: Path) -> None:
    with chain.open("a") as fh:
        fh.write("{not json\n")
    log = AuditLog(chain, retry_max_s=0.05)
    log.emit("decision", {})
    assert not log.flush(0.5)
    assert log.stats.backend_errors >= 1 and "cannot append" in (log.stats.last_error or "")
    log.close(timeout=0.5)


class FlakyBackend(MemoryBackend):
    def __init__(self) -> None:
        super().__init__()
        self.down = threading.Event()

    def append(self, records: list[dict[str, Any]]) -> None:
        if self.down.is_set():
            raise OSError("backend unavailable")
        super().append(records)


def test_backend_outage_is_recorded_and_recovered() -> None:
    be = FlakyBackend()
    log = AuditLog(be, retry_max_s=0.05)
    g = Gate([deny_tools(["rm"])], mode="enforce", audit=log)
    write(log, 2)
    be.down.set()
    # the decision path behaves exactly the same while storage is down
    assert g.decide(Action("ls")).allowed
    assert not g.decide(Action("rm")).allowed
    assert not log.flush(0.3) and not log.healthy
    be.down.clear()
    assert log.flush(5) and log.healthy
    log.close()
    types = [r["type"] for r in be.records]
    assert "audit.backend_error" in types
    outage = next(r for r in be.records if r["type"] == "audit.backend_error")["data"]
    assert outage["failures"] >= 1 and "backend unavailable" in outage["first_error"]
    assert types.count("decision") == 4 and types.count("safe_state") == 1
    assert verify_records(be.entries()).ok


def test_queue_overflow_is_counted_and_reported() -> None:
    be = FlakyBackend()
    be.down.set()
    log = AuditLog(be, maxsize=5, retry_max_s=0.02)
    for i in range(50):
        log.emit("decision", {"i": i})  # never blocks
    assert log.stats.dropped > 0
    be.down.clear()
    assert log.flush(5)
    log.close()
    gap = [r for r in be.records if r["type"] == "audit.gap"]
    assert gap and gap[0]["data"]["dropped_total"] == log.stats.dropped
    assert verify_records(be.entries()).ok


def test_emit_after_close_is_dropped(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "a.jsonl")
    log.close()
    log.emit("decision", {})
    assert log.stats.dropped == 1


def test_concurrent_emitters_produce_one_valid_chain(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    log = AuditLog(p)

    def worker(k: int) -> None:
        for i in range(250):
            log.emit("decision", {"k": k, "i": i})

    ts = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert log.flush(10)
    log.close()
    r = verify(p)
    assert r.ok and r.records == 2000
    assert log.stats.lag_ms_max >= 0


def test_open_backend_specs(tmp_path: Path) -> None:
    assert isinstance(open_backend("memory"), MemoryBackend)
    assert isinstance(open_backend(f"sqlite:{tmp_path}/x"), SqliteBackend)
    assert isinstance(open_backend(tmp_path / "x.sqlite"), SqliteBackend)
    assert isinstance(open_backend(tmp_path / "x.jsonl"), JsonlBackend)


def test_verify_missing_file_is_empty_ok(tmp_path: Path) -> None:
    r = verify(tmp_path / "nope.jsonl")
    assert r.ok and r.records == 0


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=10),
    lambda c: st.lists(c, max_size=3) | st.dictionaries(st.text(max_size=5), c, max_size=3),
    max_leaves=10,
)


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(json_values, min_size=1, max_size=20), st.data())
def test_property_any_single_change_is_detected(payloads: list[Any], data: st.DataObject) -> None:
    recs, prev = [], GENESIS
    for i, p in enumerate(payloads):
        r = seal(i, f"t{i}", "decision", {"p": p}, prev)
        prev = r["hash"]
        recs.append(r)
    assert verify_records(enumerate(recs, 1)).ok
    idx = data.draw(st.integers(0, len(recs) - 1))
    field = data.draw(st.sampled_from(["data", "ts", "type", "seq"]))
    bad = json.loads(json.dumps(recs))
    new = {
        "data": {"p": "tampered", "x": idx},
        "ts": "tX",
        "type": "other",
        "seq": bad[idx]["seq"] + 100,
    }[field]
    if bad[idx][field] == new:
        return
    bad[idx][field] = new
    r = verify_records(enumerate(bad, 1))
    assert not r.ok and r.first_bad_line == idx + 1
