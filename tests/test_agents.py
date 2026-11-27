"""Tests for aeon.agents: the HTTP clients (against a local server) and the agent loop."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from aeon.adapters import ToolBox
from aeon.agents import Agent, AnthropicClient, OpenAICompatible, ProviderError
from aeon.agents.clients import post_json
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools
from aeon.baseline import Monitor

# -- a local HTTP server -----------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    replies: ClassVar[list[tuple[int, bytes]]] = []
    seen: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        headers = {k.lower(): v for k, v in self.headers.items()}
        self.seen.append({"path": self.path, "headers": headers, "body": body})
        status, payload = self.replies.pop(0) if self.replies else (200, b"{}")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_: Any) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    _Handler.replies = []
    _Handler.seen = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _reply(status: int, obj: Any) -> tuple[int, bytes]:
    return status, json.dumps(obj).encode()


# -- clients -----------------------------------------------------------------------------


def test_openai_compatible_posts_and_auths(server: str) -> None:
    _Handler.replies = [_reply(200, {"choices": [{"message": {"content": "hi"}}]})]
    client = OpenAICompatible(server + "/v1/", api_key="k-1", headers={"x-title": "t"})
    out = client.chat.completions.create(model="m", messages=[], max_tokens=None)
    assert out["choices"][0]["message"]["content"] == "hi"
    seen = _Handler.seen[0]
    assert seen["path"] == "/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer k-1"
    assert seen["headers"]["x-title"] == "t"
    assert "max_tokens" not in seen["body"]  # None fields are dropped
    assert "OpenAICompatible" in repr(client)


def test_openai_compatible_key_from_env(server: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    OpenAICompatible(server).chat.completions.create(model="m", messages=[])
    assert _Handler.seen[0]["headers"]["authorization"] == "Bearer env-key"


def test_openai_compatible_without_key_sends_no_auth(
    server: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    OpenAICompatible(server).chat.completions.create(model="m", messages=[])
    assert "authorization" not in _Handler.seen[0]["headers"]


def test_anthropic_client_headers(server: str) -> None:
    _Handler.replies = [_reply(200, {"content": []})]
    client = AnthropicClient("a-key", base_url=server, headers={"authorization": "Bearer x"})
    client.messages.create(model="m", messages=[], max_tokens=10)
    seen = _Handler.seen[0]
    assert seen["path"] == "/v1/messages"
    assert seen["headers"]["x-api-key"] == "a-key"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"
    assert seen["headers"]["authorization"] == "Bearer x"
    assert "AnthropicClient" in repr(client)


def test_anthropic_client_needs_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicClient()


def test_http_error_carries_status_and_detail(server: str) -> None:
    _Handler.replies = [_reply(404, {"error": {"message": "no such model"}})]
    with pytest.raises(ProviderError) as info:
        OpenAICompatible(server, api_key="secret-key").chat.completions.create(model="x")
    assert info.value.status == 404
    assert "no such model" in str(info.value)
    assert "secret-key" not in str(info.value) + info.value.body


def test_non_json_and_non_object_replies(server: str) -> None:
    _Handler.replies = [(200, b"<html>"), (200, b"[1, 2]")]
    with pytest.raises(ProviderError, match="did not return JSON"):
        post_json(server, {}, {}, 5)
    with pytest.raises(ProviderError, match="not an object"):
        post_json(server, {}, {}, 5)


def test_unreachable_server() -> None:
    with pytest.raises(ProviderError, match="could not reach") as info:
        post_json("http://127.0.0.1:9/v1", {}, {}, 2)
    assert info.value.status is None


def test_bad_scheme_is_refused() -> None:
    with pytest.raises(ValueError, match="http"):
        OpenAICompatible("file:///etc/passwd")


# -- fake model clients ------------------------------------------------------------------


class _Script:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    def create(self, **kw: Any) -> Any:
        self.requests.append(json.loads(json.dumps(kw, default=str)))
        return self.replies.pop(0)


def _oai(script: _Script) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=script))


def _oai_reply(content: str | None = None, calls: list[Any] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = calls
    return {"choices": [{"message": msg}], "usage": {"total_tokens": 10}}


def _oai_call(cid: str, name: str, args: Any) -> dict[str, Any]:
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}


@pytest.fixture
def box() -> ToolBox:
    gate = Gate([deny_tools(["delete_file"])], mode="enforce", monitor=Monitor())
    b = ToolBox(gate=gate, agent="t")

    @b.tool
    def read_file(path: str) -> str:
        """Read a file."""
        return f"contents of {path}"

    @b.tool
    def delete_file(path: str) -> str:
        """Delete a file."""
        return f"deleted {path}"

    return b


# -- the loop, Chat Completions ----------------------------------------------------------


def test_openai_loop_runs_tools_and_finishes(box: ToolBox) -> None:
    script = _Script(
        [
            _oai_reply(calls=[_oai_call("c1", "read_file", '{"path": "a"}')]),
            _oai_reply(calls=[_oai_call("c2", "read_file", {"path": "b"})]),  # dict args
            _oai_reply(content="all done"),
        ]
    )
    agent = Agent(_oai(script), "m", box, system="be careful", request={"temperature": 0})
    run = agent.run("go")
    assert agent.provider == "openai"
    assert run.stop_reason == "done" and run.text == "all done"
    assert run.steps == 3 and run.tokens == 30
    assert [c.result for c in run.tool_calls] == ["contents of a", "contents of b"]
    first = script.requests[0]
    assert first["messages"][0] == {"role": "system", "content": "be careful"}
    assert first["temperature"] == 0 and "max_tokens" not in first
    assert {t["function"]["name"] for t in first["tools"]} == {"read_file", "delete_file"}
    # the assistant turn is sent back as a dict with string arguments
    assistant = script.requests[2]["messages"][4]
    assert assistant["tool_calls"][0]["function"]["arguments"] == '{"path": "b"}'
    assert box.gate is not None and box.gate.monitor is not None
    assert box.gate.monitor._state("t").tokens_total == 30


def test_openai_block_puts_agent_in_safe_state_and_stops(box: ToolBox) -> None:
    script = _Script(
        [
            _oai_reply(calls=[_oai_call("c1", "delete_file", '{"path": "prod.db"}')]),
            _oai_reply(content="never reached"),
        ]
    )
    run = Agent(_oai(script), "m", box, max_tokens=50).run("go")
    assert run.stop_reason == "safe_state" and run.text is None
    assert len(run.blocked) == 1 and run.blocked[0].is_error
    assert run.blocked[0].result.startswith("Æon blocked this action:")
    assert script.requests[0]["max_tokens"] == 50
    assert len(script.replies) == 1  # the model was not called again


def test_openai_bad_arguments_and_max_steps(box: ToolBox) -> None:
    script = _Script([_oai_reply(calls=[_oai_call("c1", "read_file", "{oops")])] * 2)
    run = Agent(_oai(script), "m", box, max_steps=2).run([{"role": "user", "content": "x"}])
    assert run.stop_reason == "max_steps" and run.steps == 2
    assert all(c.is_error and not c.blocked for c in run.tool_calls)
    assert run.tool_calls[0].result.startswith("Error: ")


def test_kill_switch_stops_before_the_model_is_called(box: ToolBox) -> None:
    assert box.gate is not None
    box.gate.engage_kill_switch("maintenance")
    script = _Script([_oai_reply(content="x")])
    run = Agent(_oai(script), "m", box).run("go")
    assert run.stop_reason == "kill_switch" and run.steps == 0
    assert not script.requests


def test_shadow_mode_records_but_does_not_block() -> None:
    gate = Gate([deny_tools(["delete_file"])], mode="shadow")
    b = ToolBox(gate=gate, agent="s")
    b.add("delete_file", lambda path: f"deleted {path}")
    script = _Script(
        [
            _oai_reply(calls=[_oai_call("c1", "delete_file", '{"path": "p"}')]),
            _oai_reply(content="done"),
        ]
    )
    run = Agent(_oai(script), "m", b).run("go")
    assert run.stop_reason == "done"
    assert run.tool_calls[0].result == "deleted p" and not run.tool_calls[0].blocked


# -- the loop, Messages API --------------------------------------------------------------


def _ant(script: _Script) -> Any:
    return SimpleNamespace(messages=script)


def test_anthropic_loop(box: ToolBox) -> None:
    script = _Script(
        [
            {
                "content": [
                    {"type": "text", "text": "reading"},
                    SimpleNamespace(
                        type="tool_use", id="u1", name="read_file", input={"path": "a"}
                    ),
                    {"type": "thinking", "thinking": "..."},
                ],
                "usage": {"input_tokens": 5, "output_tokens": 3},
            },
            {"content": [SimpleNamespace(type="text", text="done ")], "usage": None},
        ]
    )
    agent = Agent(_ant(script), "m", box, system="sys", max_steps=3)
    run = agent.run("go")
    assert agent.provider == "anthropic"
    assert run.stop_reason == "done" and run.text == "done "
    assert run.tokens == 8 and run.steps == 2
    first = script.requests[0]
    assert first["system"] == "sys" and first["max_tokens"] == 1024
    assert first["tools"][0]["input_schema"]["required"] == ["path"]
    results = script.requests[1]["messages"][2]
    assert results["role"] == "user"
    assert results["content"][0] == {
        "type": "tool_result",
        "tool_use_id": "u1",
        "content": "contents of a",
        "is_error": False,
    }
    assert script.requests[1]["messages"][1]["content"][2] == {
        "type": "thinking",
        "thinking": "...",
    }


def test_anthropic_block_and_unknown_block_objects(box: ToolBox) -> None:
    class Custom:
        type = "server_tool_use"

        def model_dump(self) -> dict[str, Any]:
            return {"type": "server_tool_use", "id": "s1"}

    class Bare:
        type = "redacted"

    script = _Script(
        [
            {
                "content": [
                    Custom(),
                    Bare(),
                    {"type": "tool_use", "id": "u1", "name": "delete_file", "input": {}},
                ]
            }
        ]
    )
    run = Agent(_ant(script), "m", box, provider="anthropic").run("go")
    assert run.stop_reason == "max_steps" or run.stop_reason == "safe_state"
    assert run.blocked and run.blocked[0].name == "delete_file"
    sent = run.messages[1]["content"]
    assert sent[0] == {"type": "server_tool_use", "id": "s1"}
    assert sent[1] == {"type": "redacted"}


# -- construction ------------------------------------------------------------------------


def test_provider_detection_and_validation(box: ToolBox) -> None:
    with pytest.raises(ValueError, match="provider"):
        Agent(object(), "m", box)
    with pytest.raises(ValueError, match="max_steps"):
        Agent(_oai(_Script([])), "m", box, max_steps=0)


def test_default_gate_is_used_without_one() -> None:
    b = ToolBox(agent="d")
    b.add("noop", lambda: "ok")
    agent = Agent(_oai(_Script([_oai_reply(content="hi")])), "m", b)
    assert agent.gate is not None
    assert agent.run("go").text == "hi"


def test_openrouter_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenAICompatible.openrouter()
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    client = OpenAICompatible.openrouter()
    assert client.base_url == "https://openrouter.ai/api/v1"


def test_reasoning_fields_are_sent_back(box: ToolBox) -> None:
    class SDKMessage:
        content = None
        tool_calls: ClassVar[list[dict[str, Any]]] = [_oai_call("c1", "read_file", '{"path": "a"}')]

        def model_dump(self, exclude_none: bool = False) -> dict[str, Any]:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": self.tool_calls,
                "reasoning_details": [{"type": "reasoning.encrypted", "data": "x"}],
            }

    script = _Script(
        [
            {"choices": [{"message": SDKMessage()}]},
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "ok",
                            "reasoning": "r",
                            "refusal": None,
                        }
                    }
                ]
            },
            _oai_reply(content="end"),
        ]
    )
    run = Agent(_oai(script), "m", box).run("go")
    sent = script.requests[1]["messages"][1]
    assert sent["reasoning_details"] == [{"type": "reasoning.encrypted", "data": "x"}]
    assert sent["tool_calls"][0]["function"]["arguments"] == '{"path": "a"}'
    assert run.text == "ok"
    assert run.messages[-1] == {"role": "assistant", "content": "ok", "reasoning": "r"}
