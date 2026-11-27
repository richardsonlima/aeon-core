from __future__ import annotations

import asyncio
import json
import socket
import stat
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from aeon.audit import AuditLog
from aeon.axioms import Action, Gate, Level
from aeon.axioms._gate import AxiomSpec
from aeon.cli.main import CLIError
from aeon.config import Config
from aeon.runtime.app import (
    MAX_BODY_BYTES,
    DecisionHub,
    create_app,
    resolve_token,
    sse_events,
)
from aeon.runtime.server import check_bind_host, serve

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _no_delete(action: Any) -> Any:
    if action.tool == "delete_db":
        return "destructive"
    return True


def make_gate(mode: str = "shadow", audit: Any = None) -> Gate:
    gate = Gate(mode=mode, audit=audit)
    gate.axioms.add(
        AxiomSpec("no-delete", _no_delete, Level.BLOCK, frozenset({"delete_db"}), "no deletes")
    )
    return gate


@pytest.fixture
def gate() -> Gate:
    return make_gate()


@pytest.fixture
def client(gate: Gate) -> Iterator[TestClient]:
    with TestClient(create_app(gate, config=Config(), token=TOKEN)) as c:
        yield c


def evaluate(client: TestClient, tool: str = "delete_db", **kw: Any) -> dict[str, Any]:
    r = client.post("/v1/actions/evaluate", json={"tool": tool, **kw}, headers=AUTH)
    assert r.status_code == 200, r.text
    return dict(r.json())


# -- auth -------------------------------------------------------------------------------


def test_open_routes_need_no_token(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert "version" in client.get("/version").json()


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic test-token"}],
)
def test_v1_requires_token(client: TestClient, headers: dict[str, str]) -> None:
    r = client.get("/v1/status", headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_query_token_only_accepted_on_stream(client: TestClient) -> None:
    assert client.get(f"/v1/status?token={TOKEN}").status_code == 401


def test_token_resolution_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert resolve_token("given", tmp_path) == ("given", "argument")
    monkeypatch.setenv("AEON_RUNTIME_TOKEN", "from-env")
    assert resolve_token(None, tmp_path)[0] == "from-env"
    monkeypatch.delenv("AEON_RUNTIME_TOKEN")
    tok, where = resolve_token(None, tmp_path)
    f = tmp_path / ".aeon" / "runtime.token"
    assert where == str(f) and len(tok) >= 32
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert resolve_token(None, tmp_path)[0] == tok  # reused, not regenerated


# -- decisions --------------------------------------------------------------------------


def test_evaluate_shadow_allows_but_reports_block(client: TestClient) -> None:
    rec = evaluate(client)
    assert rec["verdict"] == "BLOCK"
    assert rec["mode"] == "shadow" and rec["allowed"] is True and rec["enforced"] is False


def test_evaluate_enforce_denies() -> None:
    gate = make_gate("enforce")
    with TestClient(create_app(gate, config=Config(), token=TOKEN)) as c:
        rec = evaluate(c)
        assert rec["allowed"] is False and rec["enforced"] is True and rec["safe_state"] is True
        ok = evaluate(c, tool="read_file", agent="other")
        assert ok["verdict"] == "GO" and ok["allowed"] is True


def test_evaluate_validates_body(client: TestClient) -> None:
    r = client.post("/v1/actions/evaluate", json={"args": {}}, headers=AUTH)
    assert r.status_code == 422


def test_result_feeds_observe(client: TestClient, gate: Gate) -> None:
    seen: list[tuple[str, bool]] = []
    original = gate.observe

    def spy(action: Any, **kw: Any) -> None:
        seen.append((action.tool, kw["error"] is None))
        original(action, **kw)

    gate.observe = spy  # type: ignore[method-assign]
    r = client.post(
        "/v1/actions/result",
        json={"tool": "t", "agent": "a", "latency_ms": 12.5, "ok": False, "tokens": 3},
        headers=AUTH,
    )
    assert r.status_code == 200 and r.json()["recorded"] is True
    assert seen == [("t", False)]


def test_status_and_policies(client: TestClient) -> None:
    st = client.get("/v1/status", headers=AUTH).json()
    assert st["mode"] == "shadow" and st["axioms"] == ["no-delete"] and st["audit"] is None
    pol = client.get("/v1/policies", headers=AUTH).json()["policies"]
    assert pol == [
        {
            "name": "no-delete",
            "level": "BLOCK",
            "tools": ["delete_db"],
            "description": "no deletes",
            "enabled": True,
        }
    ]


def test_policy_disable_enable_and_level(client: TestClient) -> None:
    r = client.put("/v1/policies/no-delete", json={"enabled": False}, headers=AUTH)
    assert r.json()["enabled"] is False
    assert evaluate(client)["verdict"] == "GO"
    rows = client.get("/v1/policies", headers=AUTH).json()["policies"]
    assert [(p["name"], p["enabled"]) for p in rows] == [("no-delete", False)]

    r = client.put("/v1/policies/no-delete", json={"enabled": True, "level": "alert"}, headers=AUTH)
    assert r.json()["level"] == "ALERT" and r.json()["enabled"] is True
    assert evaluate(client)["verdict"] == "ALERT"

    # a level change on a disabled policy is kept for when it comes back
    client.put("/v1/policies/no-delete", json={"enabled": False}, headers=AUTH)
    client.put("/v1/policies/no-delete", json={"level": "LIMIT"}, headers=AUTH)
    client.put("/v1/policies/no-delete", json={"enabled": True}, headers=AUTH)
    assert evaluate(client)["verdict"] == "LIMIT"


def test_policy_errors(client: TestClient) -> None:
    assert client.put("/v1/policies/nope", json={}, headers=AUTH).status_code == 404
    for level in ("GO", "bogus"):
        r = client.put("/v1/policies/no-delete", json={"level": level}, headers=AUTH)
        assert r.status_code == 422


def test_mode_switch(client: TestClient) -> None:
    r = client.post("/v1/mode", json={"mode": "enforce"}, headers=AUTH)
    assert r.json() == {"mode": "enforce"}
    assert evaluate(client)["allowed"] is False
    assert client.post("/v1/mode", json={"mode": "nope"}, headers=AUTH).status_code == 422


def test_kill_switch_blocks_everything_even_in_shadow(client: TestClient) -> None:
    r = client.post("/v1/kill-switch", json={"engaged": True, "reason": "drill"}, headers=AUTH)
    assert r.json()["engaged"] is True and r.json()["reason"] == "drill"
    rec = evaluate(client, tool="read_file")
    assert rec["allowed"] is False and rec["findings"][0]["axiom"] == "kill-switch"
    r = client.post("/v1/kill-switch", json={"engaged": False}, headers=AUTH)
    assert r.json()["engaged"] is False
    assert evaluate(client, tool="read_file")["allowed"] is True


def test_safe_state_reset() -> None:
    gate = make_gate("enforce")
    with TestClient(create_app(gate, config=Config(), token=TOKEN)) as c:
        evaluate(c)
        assert "default" in c.get("/v1/status", headers=AUTH).json()["safe_states"]
        r = c.post("/v1/safe-state/default/reset", headers=AUTH)
        assert r.json() == {"agent": "default", "released": True}
        assert c.get("/v1/status", headers=AUTH).json()["safe_states"] == {}
        assert c.post("/v1/safe-state/default/reset", headers=AUTH).json()["released"] is False


def test_decisions_filters(client: TestClient) -> None:
    evaluate(client, agent="a")
    evaluate(client, tool="read_file", agent="b")
    evaluate(client, agent="b")
    body = client.get("/v1/decisions", headers=AUTH).json()
    assert body["count"] == 3 and body["buffered"] == 3
    assert body["decisions"][0]["agent"] == "b"  # newest first

    def ids(**params: Any) -> list[str]:
        r = client.get("/v1/decisions", params=params, headers=AUTH)
        return [d["agent"] + ":" + d["tool"] for d in r.json()["decisions"]]

    assert ids(agent="a") == ["a:delete_db"]
    assert ids(axiom="no-delete") == ["b:delete_db", "a:delete_db"]
    assert ids(level="go") == ["b:read_file"]
    assert ids(limit=1) == ["b:delete_db"]
    assert client.get("/v1/decisions?level=zzz", headers=AUTH).status_code == 422
    assert client.get("/v1/decisions?limit=0", headers=AUTH).status_code == 422


# -- stream -----------------------------------------------------------------------------


def test_decision_hub_is_bounded() -> None:
    hub = DecisionHub(maxlen=3)
    for i in range(5):
        hub.publish({"agent": "a", "verdict": "GO", "findings": [], "n": i})
    assert len(hub) == 3
    assert [r["n"] for r in hub.recent(agent=None, axiom=None, level=None, limit=10)] == [4, 3, 2]


def test_sse_stream_yields_decisions(gate: Gate) -> None:
    hub: DecisionHub = create_app(gate, config=Config(), token=TOKEN).state.hub

    async def never() -> bool:
        return False

    async def scenario() -> tuple[str, str]:
        stream = sse_events(hub, never, heartbeat_s=0.05)
        first = await anext(stream)
        threading.Thread(target=lambda: gate.decide(Action(tool="delete_db"))).start()
        data = ""
        while not data.startswith("data: "):
            data = await asyncio.wait_for(anext(stream), 2)
        await stream.aclose()
        return first, data

    first, data = asyncio.run(scenario())
    assert first.startswith(": connected")
    rec = json.loads(data.removeprefix("data: "))
    assert rec["tool"] == "delete_db" and rec["verdict"] == "BLOCK"


def test_client_queue_drops_oldest() -> None:
    async def scenario() -> list[int]:
        hub = DecisionHub(queue_size=2)
        q = hub.attach()
        for i in range(5):
            hub.publish({"n": i, "findings": []})
        await asyncio.sleep(0.05)
        return [q.get_nowait()["n"] for _ in range(q.qsize())]

    assert asyncio.run(scenario()) == [3, 4]


def test_sse_heartbeat_and_disconnect() -> None:
    hub = DecisionHub()

    async def scenario() -> list[str]:
        calls = 0

        async def gone() -> bool:
            nonlocal calls
            calls += 1
            return calls > 1

        return [chunk async for chunk in sse_events(hub, gone, heartbeat_s=0.01)]

    out = asyncio.run(scenario())
    assert out == [": connected\n\n", ": heartbeat\n\n"]
    assert hub.clients == 0


def test_stream_route_auth(client: TestClient) -> None:
    assert client.get("/v1/decisions/stream").status_code == 401
    assert client.get("/v1/decisions/stream?token=bad").status_code == 401


# -- audit ------------------------------------------------------------------------------


def test_audit_endpoints(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    gate = make_gate("enforce", audit=log)
    with TestClient(create_app(gate, config=Config(), token=TOKEN)) as c:
        evaluate(c)
        evaluate(c, tool="read_file")
        v = c.post("/v1/audit/verify", headers=AUTH).json()
        assert v["ok"] is True and v["records"] >= 2
        bad = c.post("/v1/audit/verify", json={"expect_head": "00"}, headers=AUTH).json()
        assert bad["ok"] is False
        tail = c.get("/v1/audit?type=decision&limit=1", headers=AUTH).json()
        assert tail["count"] == 1 and tail["records"][0]["type"] == "decision"
        jl = c.get("/v1/audit/export?format=jsonl", headers=AUTH)
        assert jl.headers["content-type"].startswith("application/x-ndjson")
        assert all(json.loads(line)["hash"] for line in jl.text.splitlines())
        csv_body = c.get("/v1/audit/export?format=csv", headers=AUTH).text
        assert csv_body.splitlines()[0].startswith("seq,ts,type")
        assert c.get("/v1/audit/export?format=xml", headers=AUTH).status_code == 422
        st = c.get("/v1/status", headers=AUTH).json()
        assert st["audit"]["healthy"] is True and st["audit"]["stats"]["emitted"] >= 2
    log.close()


def test_audit_endpoints_without_audit_log(client: TestClient) -> None:
    assert client.get("/v1/audit", headers=AUTH).status_code == 409
    assert client.post("/v1/audit/verify", headers=AUTH).status_code == 409
    assert client.get("/v1/audit/export", headers=AUTH).status_code == 409


# -- campaigns --------------------------------------------------------------------------


def _wait_campaign(client: TestClient, cid: str) -> Any:
    for _ in range(400):
        r = client.get(f"/v1/campaigns/{cid}", headers=AUTH)
        if r.status_code != 202:
            return r
        time.sleep(0.05)
    raise AssertionError("campaign did not finish")


def test_campaign_run_poll_and_list(client: TestClient) -> None:
    r = client.post(
        "/v1/campaigns",
        json={"target": "tool-timeout", "runs": 2, "controls": 2, "seed": 3},
        headers=AUTH,
    )
    assert r.status_code == 202
    cid = r.json()["id"]
    assert cid == "adhoc-tool-timeout"
    done = _wait_campaign(client, cid)
    assert done.status_code == 200, done.text
    doc = done.json()
    assert doc["campaign"]["runs"] == 2 and "summary" in doc and "unfavourable" in doc
    listed = client.get("/v1/campaigns", headers=AUTH).json()
    assert [c["id"] for c in listed["campaigns"]] == [cid]


def test_campaign_validation(client: TestClient) -> None:
    def post(body: dict[str, Any]) -> int:
        return client.post("/v1/campaigns", json=body, headers=AUTH).status_code

    assert post({}) == 422
    assert post({"target": "nope-fault"}) == 422
    assert post({"target": "../../etc/passwd"}) == 422
    assert post({"target": "tool-timeout", "runs": 100000}) == 422
    assert post({"target": "tool-timeout", "blast_radius": "production"}) == 422
    assert post({"campaign": {"id": "../x", "hypothesis": "h", "fault": "tool-timeout"}}) == 422
    assert client.get("/v1/campaigns/never-ran", headers=AUTH).status_code == 404
    assert client.get("/v1/campaigns/bad.json", headers=AUTH).status_code == 422


def test_campaign_from_mapping_and_single_flight(client: TestClient) -> None:
    body = {
        "campaign": {
            "id": "mine",
            "hypothesis": "h",
            "fault": "tool-timeout",
            "runs": 2,
            "controls": 2,
        }
    }
    assert client.post("/v1/campaigns", json=body, headers=AUTH).status_code == 202
    second = client.post("/v1/campaigns", json={"target": "tool-timeout"}, headers=AUTH)
    # either still running (409) or already finished (202): never two at once
    assert second.status_code in {202, 409}
    assert _wait_campaign(client, "mine").status_code == 200
    if second.status_code == 202:
        assert _wait_campaign(client, "adhoc-tool-timeout").status_code == 200


# -- claims, ui -------------------------------------------------------------------------


def test_claims_404_then_served(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import aeon.runtime.app as app_mod

    # only look in the test's cwd, not in the repository checkout
    monkeypatch.setattr(
        app_mod, "claims_candidates", lambda cfg: [Path.cwd() / "docs" / "claims.json"]
    )
    r = client.get("/v1/claims", headers=AUTH)
    assert r.status_code == 404 and "claims.json" in r.json()["detail"]
    Path("docs").mkdir()
    Path("docs/claims.json").write_text(json.dumps({"claims": [{"id": "c1"}]}))
    assert client.get("/v1/claims", headers=AUTH).json() == {"claims": [{"id": "c1"}]}


def test_root_redirects_to_ui_when_built(client: TestClient) -> None:
    r = client.get("/", follow_redirects=False)
    if r.status_code == 307:
        assert r.headers["location"] == "/ui/"
        assert client.get("/ui/").status_code == 200
    else:
        assert r.json()["ui"] is False


# -- limits and binding -----------------------------------------------------------------


def test_body_size_cap(client: TestClient) -> None:
    big = {"tool": "t", "args": {"x": "a" * (MAX_BODY_BYTES + 10)}}
    r = client.post("/v1/actions/evaluate", json=big, headers=AUTH)
    assert r.status_code == 413

    def chunks() -> Iterator[bytes]:  # no Content-Length: capped while streaming
        for _ in range(MAX_BODY_BYTES // 1024 + 2):
            yield b"x" * 1024

    r = client.post("/v1/actions/evaluate", content=chunks(), headers=AUTH)
    assert r.status_code == 413
    small = client.post("/v1/actions/evaluate", json={"tool": "t"}, headers=AUTH)
    assert small.status_code == 200


def test_remote_bind_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AEON_RUNTIME_ALLOW_REMOTE", raising=False)
    for host in ("0.0.0.0", "192.168.1.5", "example.com", ""):
        with pytest.raises(CLIError) as exc:
            serve(host, 0, None, False)
        assert "AEON_RUNTIME_ALLOW_REMOTE" in (exc.value.hint or "")
    for host in ("127.0.0.1", "localhost", "::1"):
        check_bind_host(host)
    monkeypatch.setenv("AEON_RUNTIME_ALLOW_REMOTE", "1")
    check_bind_host("0.0.0.0")


def test_port_in_use_is_a_clear_error() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        with pytest.raises(CLIError) as exc:
            serve("127.0.0.1", port, None, False)
    assert "--port" in (exc.value.hint or "")
