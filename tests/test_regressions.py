"""Regression tests for bugs found in review (one test per finding)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from aeon.audit import AuditLog, JsonlBackend, verify
from aeon.axioms import Action, Gate, Level
from aeon.axioms.builtin import deny_tools
from aeon.chaos import Campaign, run_campaign
from aeon.cli.main import main


class BrokenMonitor:
    def finding(self, agent: str) -> Any:
        raise RuntimeError("monitor bug")

    def record(self, *a: Any, **k: Any) -> None: ...

    def reset_accumulated(self, agent: str) -> None: ...

    def status(self) -> dict[str, Any]:
        return {}


def test_kill_switch_holds_when_the_gate_errors_in_shadow() -> None:
    g = Gate(mode="shadow", monitor=BrokenMonitor())  # type: ignore[arg-type]
    g.engage_kill_switch("stop")
    d = g.decide(Action("ls"))
    assert not d.allowed and d.enforced and d.gate_error


def test_gate_error_in_enforce_enters_safe_state() -> None:
    g = Gate(mode="enforce", monitor=BrokenMonitor())  # type: ignore[arg-type]
    d = g.decide(Action("ls", agent="a"))
    assert not d.allowed and d.safe_state and g.safe_state("a") is not None


@pytest.mark.parametrize("args", [{1: "a", "b": 2}, "circular"])
def test_decide_never_raises_on_odd_arguments(args: Any) -> None:
    from tests.conftest import ListSink

    if args == "circular":
        args = {}
        args["self"] = args
    sink = ListSink()
    g = Gate([deny_tools(["rm"])], mode="enforce", audit=sink)
    d = g.decide(Action("rm", args))
    assert not d.allowed and d.safe_state
    assert sink.of("decision") and sink.of("safe_state")


def test_jsonl_failure_after_write_does_not_duplicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "a.jsonl"
    real = os.fsync
    calls = {"n": 0}

    def flaky(fd: int) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("fsync failed")
        real(fd)

    monkeypatch.setattr(os, "fsync", flaky)
    log = AuditLog(JsonlBackend(p, fsync=True), retry_max_s=0.05)
    log.emit("decision", {"i": 1})
    log.emit("decision", {"i": 2})
    assert log.flush(5)
    log.close()
    r = verify(p)
    assert r.ok, r.reason
    assert [x for x in p.read_text().splitlines() if '"decision"' in x].__len__() == 2


def test_reopen_after_missing_trailing_newline(tmp_path: Path) -> None:
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        log.emit("decision", {"i": 1})
        assert log.flush(5)
    p.write_text(p.read_text().rstrip("\n"))
    with AuditLog(p) as log:
        log.emit("decision", {"i": 2})
        assert log.flush(5)
    r = verify(p)
    assert r.ok and r.records == 2, r.reason


def test_close_timeout_does_not_double_count(tmp_path: Path) -> None:
    from aeon.audit import MemoryBackend

    class Down(MemoryBackend):
        down = True

        def append(self, records: list[dict[str, Any]]) -> None:
            if self.down:
                raise OSError("down")
            super().append(records)

    be = Down()
    log = AuditLog(be, retry_max_s=0.05)
    log.emit("decision", {})
    log.close(timeout=0.2)
    be.down = False
    import time

    time.sleep(0.4)
    assert be.records == [] or log.stats.dropped == 0
    assert log.stats.written + log.stats.dropped <= log.stats.emitted + 2


def test_aeon_run_keeps_configured_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "aeon.toml").write_text('[aeon]\nmode = "enforce"\n[aeon.audit]\npath="off"\n')
    (tmp_path / "s.py").write_text(
        "from aeon import default_gate\nprint('MODE', default_gate().mode.value)\n"
    )
    assert main(["run", "s.py"]) == 0
    assert "MODE enforce" in capsys.readouterr().out


def test_chaos_run_zero_runs_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["chaos", "run", "rate-limit", "--runs", "0"])
    err = capsys.readouterr().err
    assert code != 0 and "unexpected error" not in err


def test_audit_tail_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        log.emit(
            "decision",
            {
                "agent": "a",
                "tool": "t",
                "verdict": "GO",
                "allowed": True,
                "mode": "shadow",
                "findings": [],
            },
        )
        log.flush(5)
    assert main(["audit", "tail", "--file", str(p), "-n", "0", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_fault_params_cannot_shadow_reserved_names() -> None:
    from aeon.chaos import make

    with pytest.raises(ValueError):
        make("rate-limit", name="x")
    c = Campaign(
        id="x",
        hypothesis="h",
        fault="rate-limit",
        fault_params={"probability": 0.5},
        runs=1,
        controls=0,
        steps=40,
        start_step=30,
    )
    run_campaign(c)  # must not raise a duplicate-keyword TypeError


def test_detection_ignores_runs_where_the_fault_never_fired() -> None:
    c = Campaign(
        id="x",
        hypothesis="h",
        fault="gateway-latency",
        probability=0.0,
        runs=4,
        controls=0,
        steps=60,
        start_step=40,
        min_detection_rate=0.5,
    )
    doc = run_campaign(c)
    s = doc["summary"]
    assert s["runs_with_injection"] == 0
    assert s["detection_rate"] is None
    assert doc["checks"]["min_detection_rate"] is False
    assert doc["checks"].get("max_false_positive_rate") is None


def test_no_harm_is_not_vacuous() -> None:
    c = Campaign(
        id="x",
        hypothesis="h",
        fault="poisoned-output",
        gullibility=0.0,
        runs=3,
        controls=1,
        steps=60,
        start_step=40,
    )
    doc = run_campaign(c)
    assert doc["summary"]["runs_with_harm_attempts"] == 0
    assert "no_harm" not in doc["checks"]
    assert any("no destructive action was attempted" in u for u in doc["unfavourable"])


def test_monitor_reset_clears_repeat_memory() -> None:
    from aeon.baseline import Budget, Monitor

    m = Monitor(Budget(baseline_n=2))
    a = Action("x", {"k": 1})
    m.record(a, latency_ms=1, error=False)
    m.reset_accumulated("default")
    m.record(Action("y"), latency_ms=1, error=False)  # calibration completes
    m.record(a, latency_ms=1, error=False)
    assert m.status()["agents"]["default"]["terms"].get("repeat", 0) == 0


def test_mcp_survives_deeply_nested_json() -> None:
    from aeon.runtime.mcp import McpServer

    s = McpServer.__new__(McpServer)
    out = McpServer.handle_line(s, "[" * 200_000)
    assert out is not None and "error" in out


def test_level_enum_unchanged() -> None:
    assert Level.BLOCK > Level.LIMIT > Level.ALERT > Level.GO


def test_mcp_rejects_oversized_line() -> None:
    import io

    from aeon.runtime import mcp

    s = mcp.McpServer(Gate(mode="shadow"))
    big = "x" * (mcp.MAX_LINE + 10) + "\n" + '{"jsonrpc":"2.0","id":1,"method":"ping"}\n'
    out = io.StringIO()
    s.serve_streams(io.StringIO(big), out)
    lines = [json.loads(x) for x in out.getvalue().splitlines()]
    assert lines[0]["error"]["code"] == mcp.PARSE_ERROR and len(lines) == 2


def test_runtime_limits_and_headers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from aeon.config import Config
    from aeon.runtime.app import create_app

    app = create_app(Gate(mode="shadow"), config=Config(audit="off", root=tmp_path), token="t")
    c = TestClient(app)
    auth = {"Authorization": "Bearer t"}
    r = c.get("/health")
    assert (
        r.headers["x-frame-options"] == "DENY"
        and "frame-ancestors" in r.headers["content-security-policy"]
    )
    bad = {"target": "gateway-latency", "runs": 1000, "controls": 1000}
    assert c.post("/v1/campaigns", json=bad, headers=auth).status_code in {400, 422}
    slow = {
        "campaign": {
            "id": "slow",
            "hypothesis": "h",
            "fault": {"name": "gateway-latency", "params": {"delay_ms": 600000}},
        }
    }
    assert c.post("/v1/campaigns", json=slow, headers=auth).status_code in {400, 422}


def test_token_file_mode_is_tightened(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    from aeon.runtime.app import resolve_token

    monkeypatch.delenv("AEON_RUNTIME_TOKEN", raising=False)
    tok, _ = resolve_token(None, tmp_path)
    p = tmp_path / ".aeon" / "runtime.token"
    os.chmod(p, 0o644)
    assert resolve_token(None, tmp_path)[0] == tok
    if os.name == "posix":
        assert p.stat().st_mode & 0o777 == 0o600
    link = tmp_path / "other"
    (link / ".aeon").mkdir(parents=True)
    (link / ".aeon" / "runtime.token").symlink_to(p)
    with pytest.raises(PermissionError):
        resolve_token(None, link)


def test_allowed_hosts() -> None:
    pytest.importorskip("fastapi")
    from aeon.runtime.server import allowed_hosts

    assert "localhost" in allowed_hosts("127.0.0.1")
    assert allowed_hosts("0.0.0.0") == []
    os.environ["AEON_RUNTIME_ALLOWED_HOSTS"] = "a.local, b.local"
    try:
        assert allowed_hosts("0.0.0.0") == ["a.local", "b.local"]
    finally:
        del os.environ["AEON_RUNTIME_ALLOWED_HOSTS"]
