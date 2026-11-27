"""Tests for the agent SDK: models, storage, schema, approval, events, team, workflow."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aeon.agents import (
    Agent,
    Model,
    RunEvent,
    SqliteDb,
    resolve_model,
)
from aeon.agents.schema import OutputSchema
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools, require_approval


class Script:
    """A fake Chat Completions client that replays replies and records requests."""

    def __init__(self, *replies: Any) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kw: Any) -> Any:
        self.requests.append(json.loads(json.dumps(kw, default=str)))
        return self.replies.pop(0)


def say(text: str) -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def call(name: str, args: dict[str, Any], cid: str = "c1") -> dict[str, Any]:
    tc = {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
    msg = {"role": "assistant", "content": None, "tool_calls": [tc]}
    return {"choices": [{"message": msg}], "usage": {"total_tokens": 5}}


def read_file(path: str) -> str:
    """Read a file."""
    return f"contents of {path}"


def delete_file(path: str) -> str:
    """Delete a file."""
    return f"deleted {path}"


# -- models ------------------------------------------------------------------------------


def test_resolve_model_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    m = resolve_model("openrouter:openai/gpt-4o-mini")
    assert (m.id, m.wire, m.provider) == ("openai/gpt-4o-mini", "openai", "openrouter")
    assert resolve_model("ollama:qwen2.5:3b").id == "qwen2.5:3b"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert resolve_model("anthropic:claude-x").wire == "anthropic"
    assert resolve_model("compatible:m", base_url="http://127.0.0.1:1/v1").provider == "compatible"
    assert resolve_model(m) is m


@pytest.mark.parametrize(
    ("spec", "message"),
    [("gpt-4o", "provider:model"), ("nope:x", "unknown provider"), ("groq:x", "GROQ_API_KEY"),
     ("compatible:x", "needs base_url")],
)  # fmt: skip
def test_resolve_model_errors(monkeypatch: pytest.MonkeyPatch, spec: str, message: str) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match=message):
        resolve_model(spec)


# -- storage -----------------------------------------------------------------------------


def test_sqlite_db(tmp_path: Path) -> None:
    db = SqliteDb(tmp_path / "sub" / "a.db")
    for i in range(3):
        db.add_run(run_id=f"r{i}", session_id="s", agent="a", user_id="u", input=f"q{i}",
                   output=f"a{i}", status="completed", tokens=i)  # fmt: skip
    db.add_run(run_id="x", session_id="t", agent="b", user_id=None, input="q", output=None,
               status="paused", tokens=0)  # fmt: skip
    assert [r["input"] for r in db.get_runs("s", 2)] == ["q1", "q2"]
    assert len(db.get_runs("s")) == 3
    assert set(db.sessions()) == {"s", "t"} and db.sessions("b") == ["t"]
    db.add_memory("u", "likes tea")
    assert db.get_memories("u") == ["likes tea"]
    assert json.loads(db.export())["memories"]
    assert db.clear_memories("u") == 1 and db.get_memories("u") == []
    assert "a.db" in repr(db)
    db.close()


# -- schema ------------------------------------------------------------------------------


@dataclass
class Report:
    revenue: int
    note: str = ""


class FakePydantic:
    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        return {"type": "object", "required": ["x"]}

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> Any:
        if "x" not in value:
            raise ValueError("x missing")
        return SimpleNamespace(x=value["x"], model_dump=lambda: value)


def test_output_schema_kinds() -> None:
    s = OutputSchema.of(Report)
    assert s.json_schema["required"] == ["revenue"] and "JSON schema" in s.instruction()
    assert s.parse('```json\n{"revenue": 3, "extra": 1}\n```') == Report(3)
    with pytest.raises(ValueError, match="missing required"):
        s.parse("{}")
    with pytest.raises(ValueError, match="not valid JSON"):
        s.parse("no")
    with pytest.raises(ValueError, match="not an object"):
        s.parse("[1]")
    assert OutputSchema.of({"type": "object"}).parse('{"a": 1}') == {"a": 1}
    p = OutputSchema.of(FakePydantic)
    assert p.parse('{"x": 2}').x == 2
    with pytest.raises(ValueError, match="did not match"):
        p.parse('{"y": 2}')
    with pytest.raises(TypeError):
        OutputSchema.of(int)


def test_agent_structured_output_with_one_retry() -> None:
    client = Script(say("not json"), say('{"revenue": 10}'))
    agent = Agent("m", [read_file], client=client, output_schema=Report)
    run = agent.run("fill it")
    assert run.status == "completed" and run.content == Report(10)
    assert "JSON schema" in client.requests[0]["messages"][0]["content"]
    assert "Reply with only the JSON object" in client.requests[1]["messages"][-1]["content"]


def test_agent_structured_output_gives_up() -> None:
    run = Agent("m", client=Script(say("x"), say("y")), output_schema=Report).run("go")
    assert run.status == "stopped" and run.stop_reason == "bad_output" and run.text == "y"


# -- approval ----------------------------------------------------------------------------


def _approval_gate() -> Gate:
    return Gate([require_approval(["delete_file"])], mode="enforce")


def test_pause_and_continue_approved() -> None:
    client = Script(call("delete_file", {"path": "p"}), say("done"))
    agent = Agent("m", [delete_file], gate=_approval_gate(), client=client)
    run = agent.run("delete p")
    assert run.status == "paused" and [c.name for c in run.pending] == ["delete_file"]
    assert len(client.requests) == 1
    out = agent.continue_run(run, approve={"delete_file": True})
    assert out.status == "completed" and out.content == "done"
    assert out.tool_calls[0].result == "deleted p" and out.tool_calls[0].approved
    assert client.requests[1]["messages"][-1]["content"] == "deleted p"
    assert agent.gate.approver is None  # one-shot approval removed
    with pytest.raises(ValueError, match="not paused"):
        agent.continue_run(out)


def test_continue_denied_and_callable_approval() -> None:
    client = Script(call("delete_file", {"path": "p"}), say("ok, not deleted"))
    agent = Agent("m", [delete_file], gate=_approval_gate(), client=client)
    out = agent.continue_run(agent.run("delete p"), approve=False)
    assert out.tool_calls[0].blocked and "did not approve" in out.tool_calls[0].result

    seen: list[str] = []
    yes = Agent("m", [delete_file], gate=_approval_gate(),
                client=Script(call("delete_file", {"path": "q"}), say("deleted")),
                approval=lambda c: seen.append(c.name) or True)  # fmt: skip
    assert yes.run("go").tool_calls[0].result == "deleted q" and seen == ["delete_file"]

    client = Script(call("delete_file", {"path": "q"}), say("fine"))
    no = Agent("m", [delete_file], gate=_approval_gate(), client=client, approval="deny")
    r = no.run("go")
    assert r.tool_calls[0].blocked and r.status == "completed"


# -- events, printing, debug -------------------------------------------------------------


def test_stream_events_and_print_response(capsys: pytest.CaptureFixture[str]) -> None:
    gate = Gate([deny_tools(["delete_file"])], mode="enforce")
    client = Script(call("read_file", {"path": "a"}), say("summary"))
    agent = Agent("m", [read_file, delete_file], gate=gate, client=client, debug=True)
    kinds = [e.event for e in agent.run("go", stream=True)]
    assert kinds == [
        RunEvent.run_started, RunEvent.model_request_started, RunEvent.model_request_completed,
        RunEvent.tool_call_started, RunEvent.tool_call_completed,
        RunEvent.model_request_started, RunEvent.model_request_completed, RunEvent.run_completed,
    ]  # fmt: skip
    assert "[aeon:agent] RunStarted" in capsys.readouterr().err

    agent.model.client.replies = [call("delete_file", {"path": "p"})]
    agent.debug = False
    out = agent.print_response("go")
    printed = capsys.readouterr().out
    assert "delete_file" in printed and "BLOCKED" in printed and "[stopped: safe_state]" in printed
    assert out.status == "stopped"


def test_print_paused_and_structured(capsys: pytest.CaptureFixture[str]) -> None:
    agent = Agent("m", [delete_file], gate=_approval_gate(),
                  client=Script(call("delete_file", {"path": "p"})))  # fmt: skip
    assert agent.print_response("x").status == "paused"
    assert "needs approval" in capsys.readouterr().out
    s = Agent("m", client=Script(say('{"revenue": 1}')), output_schema=Report)
    s.print_response("x")
    assert '"revenue": 1' in capsys.readouterr().out


def test_cli_app(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    client = Script(say("hello"), call("delete_file", {"path": "p"}), say("deleted it"))
    agent = Agent("m", [delete_file], gate=_approval_gate(), client=client)
    monkeypatch.setattr("sys.stdin", io.StringIO("hi\n\ndelete p\ny\nexit\n"))
    agent.cli_app()
    out = capsys.readouterr().out
    assert "hello" in out and "deleted it" in out
    # the second turn carries the first one, without the system message
    assert [m["role"] for m in client.requests[1]["messages"]][:2] == ["user", "assistant"]
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    agent.cli_app()  # EOF ends the chat


# -- context: history, memory, datetime --------------------------------------------------


def test_history_memory_and_datetime(tmp_path: Path) -> None:
    db = SqliteDb(tmp_path / "a.db")
    client = Script(call("update_user_memory", {"memory": "likes tea"}), say("noted"), say("tea"))
    agent = Agent("m", client=client, db=db, add_history_to_context=True,
                  enable_agentic_memory=True, add_datetime_to_context=True,
                  instructions=["be brief"])  # fmt: skip
    assert "update_user_memory" in agent.toolbox.tools
    agent.run("I like tea", session_id="s", user_id="u")
    assert db.get_memories("u") == ["likes tea"]
    agent.run("what do I like?", session_id="s", user_id="u")
    msgs = client.requests[2]["messages"]
    system = msgs[0]["content"]
    assert "be brief" in system and "UTC" in system and "- likes tea" in system
    assert msgs[1] == {"role": "user", "content": "I like tea"}
    assert msgs[2] == {"role": "assistant", "content": "noted"}
    assert agent._update_user_memory("x") == "Saved."
    agent._memory_user = None
    assert "nothing was saved" in agent._update_user_memory("x")
    with pytest.raises(ValueError, match="db="):
        Agent("m", client=client, enable_agentic_memory=True)


def test_anthropic_system_and_repr() -> None:
    script = SimpleNamespace(requests=[])

    def create(**kw: Any) -> Any:
        script.requests.append(kw)
        return {"content": [{"type": "text", "text": "ok"}]}

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    agent = Agent("m", client=client, instructions="sys", name="a1")
    assert agent.run("hi").content == "ok"
    assert script.requests[0]["system"] == "sys" and "tools" not in script.requests[0]
    assert "a1" in repr(agent) and isinstance(agent.model, Model)
