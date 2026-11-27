from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aeon.audit import AuditLog
from aeon.axioms import Gate, Level
from aeon.axioms._gate import AxiomSpec
from aeon.cli.main import CLIError
from aeon.config import Config
from aeon.docs_mcp import DocsServer, serve_docs
from aeon.runtime.mcp import PROTOCOL_VERSION, McpServer


def _no_delete(action: Any) -> Any:
    return "destructive" if action.tool == "delete_db" else True


def server(mode: str = "enforce", audit: Any = None) -> McpServer:
    gate = Gate(mode=mode, audit=audit)
    gate.axioms.add(AxiomSpec("no-delete", _no_delete, Level.BLOCK, frozenset({"delete_db"})))
    return McpServer(gate, config=Config())


def call(srv: Any, method: str, params: Any = None, id: Any = 1) -> dict[str, Any]:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        msg["params"] = params
    out = srv.handle(msg)
    assert out is not None
    return dict(out)


def tool(srv: Any, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    r = call(srv, "tools/call", {"name": name, "arguments": args or {}})
    return dict(r["result"])


# -- protocol ---------------------------------------------------------------------------


def test_initialize_and_lifecycle() -> None:
    srv = server()
    r = call(srv, "initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}})
    res = r["result"]
    assert res["protocolVersion"] == "2025-06-18"
    assert res["serverInfo"]["name"] == "aeon" and "tools" in res["capabilities"]
    older = call(srv, "initialize", {"protocolVersion": "2024-11-05"})["result"]
    assert older["protocolVersion"] == "2024-11-05"
    unknown = call(srv, "initialize", {"protocolVersion": "1999-01-01"})["result"]
    assert unknown["protocolVersion"] == PROTOCOL_VERSION
    assert srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert call(srv, "ping")["result"] == {}


def test_errors() -> None:
    srv = server()
    assert call(srv, "nope")["error"]["code"] == -32601
    assert srv.handle({"jsonrpc": "2.0", "method": "nope"}) is None  # notification: silent
    assert srv.handle_line("{not json")["error"]["code"] == -32700  # type: ignore[index]
    assert srv.handle([1, 2])["error"]["code"] == -32600  # type: ignore[index]
    assert srv.handle({"id": 1, "method": "ping"})["error"]["code"] == -32600  # type: ignore[index]
    assert call(srv, "tools/call", {"name": "ghost"})["error"]["code"] == -32602
    assert (
        call(srv, "tools/call", {"name": "aeon_status", "arguments": 3})["error"]["code"] == -32602
    )
    bad = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1]})
    assert bad is not None and bad["error"]["code"] == -32602


def test_tools_list_names_and_schemas() -> None:
    tools = call(server(), "tools/list")["result"]["tools"]
    assert [t["name"] for t in tools] == [
        "aeon_check_action",
        "aeon_status",
        "aeon_audit_verify",
        "aeon_run_campaign",
    ]
    assert all(t["inputSchema"]["type"] == "object" and t["description"] for t in tools)


# -- tools ------------------------------------------------------------------------------


def test_check_action_returns_decision_record() -> None:
    res = tool(server(), "aeon_check_action", {"tool": "delete_db", "agent": "a"})
    rec = res["structuredContent"]
    assert rec["verdict"] == "BLOCK" and rec["allowed"] is False and rec["agent"] == "a"
    assert json.loads(res["content"][0]["text"]) == rec
    assert "isError" not in res
    ok = tool(server(), "aeon_check_action", {"tool": "read_file", "args": {"p": 1}})
    assert ok["structuredContent"]["allowed"] is True


def test_check_action_shadow_and_approval() -> None:
    res = tool(server("shadow"), "aeon_check_action", {"tool": "delete_db"})
    assert res["structuredContent"]["allowed"] is True
    assert res["structuredContent"]["verdict"] == "BLOCK"


def test_tool_errors_are_is_error() -> None:
    srv = server()
    for args in ({}, {"tool": ""}, {"tool": "t", "args": "x"}):
        res = tool(srv, "aeon_check_action", args)
        assert res["isError"] is True and res["content"][0]["type"] == "text"
    assert tool(srv, "aeon_audit_verify")["isError"] is True  # no audit log configured
    assert tool(srv, "aeon_run_campaign", {"target": "nope-fault"})["isError"] is True
    assert tool(srv, "aeon_run_campaign", {"target": "tool-timeout", "runs": "2"})["isError"]


def test_status_tool() -> None:
    srv = server()
    tool(srv, "aeon_check_action", {"tool": "delete_db"})
    st = tool(srv, "aeon_status")["structuredContent"]
    assert st["mode"] == "enforce" and st["axioms"] == ["no-delete"]
    assert st["counters"]["decisions"] == 1 and "default" in st["safe_states"]


def test_audit_verify_tool(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "a.jsonl")
    srv = server(audit=log)
    tool(srv, "aeon_check_action", {"tool": "read_file"})
    rep = tool(srv, "aeon_audit_verify")["structuredContent"]
    assert rep["ok"] is True and rep["records"] >= 1
    assert tool(srv, "aeon_audit_verify", {"expect_head": "00"})["structuredContent"]["ok"] is False
    assert tool(srv, "aeon_audit_verify", {"expect_head": 5})["isError"] is True
    log.close()


def test_run_campaign_tool() -> None:
    res = tool(
        server(),
        "aeon_run_campaign",
        {"target": "tool-timeout", "runs": 2, "controls": 2, "seed": 1},
    )
    out = res["structuredContent"]
    assert "isError" not in res
    assert out["campaign"] == "adhoc-tool-timeout"
    assert set(out) >= {"summary", "checks", "unfavourable", "hypothesis_supported"}
    assert Path(out["saved_to"]).is_file()


def test_run_campaign_rejects_paths_and_big_radius() -> None:
    srv = server()
    assert tool(srv, "aeon_run_campaign", {"target": "../x.toml"})["isError"] is True
    big = {"target": "tool-timeout", "blast_radius": "production"}
    assert tool(srv, "aeon_run_campaign", big)["isError"] is True


def test_serve_streams_roundtrip() -> None:
    srv = server()
    lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
        "",
        "garbage",
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": "x", "method": "tools/list"}),
    ]
    out = io.StringIO()
    assert srv.serve_streams(io.StringIO("\n".join(lines) + "\n"), out) == 0
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r["id"] for r in replies] == [1, None, "x"]
    assert replies[1]["error"]["code"] == -32700


def test_subprocess_stdio() -> None:
    msgs = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "aeon", "runtime", "mcp"],
        input="".join(json.dumps(m) + "\n" for m in msgs),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2]  # stdout carries only protocol messages
    assert replies[0]["result"]["protocolVersion"] == PROTOCOL_VERSION
    names = {t["name"] for t in replies[1]["result"]["tools"]}
    assert "aeon_check_action" in names
    assert "ready" in proc.stderr  # logs on stderr only


# -- docs server ------------------------------------------------------------------------


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    (d / "guides").mkdir(parents=True)
    (d / "index.md").write_text("# Welcome\n\nÆon gates agent actions.\n")
    (d / "guides" / "audit.md").write_text(
        "# Audit log\n\nThe audit log is a hash chain.\nVerify the chain with aeon audit verify.\n"
    )
    (d / "guides" / "notes.txt").write_text("not markdown, audit")
    (tmp_path / "secret.md").write_text("# Secret\n")
    return d


def test_docs_resources(docs: Path) -> None:
    srv = DocsServer(docs)
    init = call(srv, "initialize", {})["result"]
    assert "resources" in init["capabilities"]
    items = call(srv, "resources/list")["result"]["resources"]
    assert [i["uri"] for i in items] == ["aeon-docs://guides/audit.md", "aeon-docs://index.md"]
    assert items[0]["title"] == "Audit log" and items[0]["mimeType"] == "text/markdown"
    read = call(srv, "resources/read", {"uri": "aeon-docs://index.md"})["result"]["contents"][0]
    assert "gates agent actions" in read["text"] and read["uri"] == "aeon-docs://index.md"
    missing = call(srv, "resources/read", {"uri": "aeon-docs://nope.md"})
    assert missing["error"]["code"] == -32002


def test_docs_search_and_read(docs: Path) -> None:
    srv = DocsServer(docs)
    res = tool(srv, "search_docs", {"query": "Audit CHAIN"})["structuredContent"]["results"]
    assert res[0]["path"] == "guides/audit.md" and res[0]["title"] == "Audit log"
    assert "hash chain" in res[0]["snippet"] and len(res) == 1
    assert tool(srv, "search_docs", {"query": "zzzz"})["structuredContent"]["results"] == []
    limited = tool(srv, "search_docs", {"query": "a", "limit": 1})["structuredContent"]["results"]
    assert len(limited) <= 1
    assert tool(srv, "search_docs", {"query": "!!!"})["isError"] is True
    doc = tool(srv, "read_doc", {"path": "guides/audit.md"})["structuredContent"]
    assert doc["title"] == "Audit log" and "hash chain" in doc["text"]
    assert tool(srv, "read_doc", {"path": "aeon-docs://index.md"})["structuredContent"]["path"] == (
        "index.md"
    )


@pytest.mark.parametrize(
    "path",
    [
        "../secret.md",
        "guides/../../secret.md",
        "/etc/passwd",
        "..\\secret.md",
        "guides/notes.txt",
        "C:/x.md",
        "",
        "missing.md",
        "guides",
    ],
)
def test_docs_path_traversal_and_bad_paths_rejected(docs: Path, path: str) -> None:
    srv = DocsServer(docs)
    res = tool(srv, "read_doc", {"path": path})
    assert res["isError"] is True and "Secret" not in json.dumps(res)


def test_docs_symlink_escape_rejected(docs: Path, tmp_path: Path) -> None:
    link = docs / "escape.md"
    try:
        link.symlink_to(tmp_path / "secret.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    srv = DocsServer(docs)
    assert tool(srv, "read_doc", {"path": "escape.md"})["isError"] is True
    uris = [i["uri"] for i in call(srv, "resources/list")["result"]["resources"]]
    assert "aeon-docs://escape.md" not in uris
    bad = call(srv, "resources/read", {"uri": "aeon-docs://../secret.md"})
    assert bad["error"]["code"] == -32602


def test_serve_docs_missing_dir_is_clear(tmp_path: Path) -> None:
    with pytest.raises(CLIError) as exc:
        serve_docs(str(tmp_path / "nope"))
    assert "docs directory not found" in str(exc.value)


def test_serve_docs_streams(docs: Path) -> None:
    out = io.StringIO()
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/list"}) + "\n"
    assert serve_docs(str(docs), io.StringIO(req), out) == 0
    assert json.loads(out.getvalue())["result"]["resources"]
