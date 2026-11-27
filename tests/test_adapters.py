from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from aeon.adapters import GuardedTool, ToolBox, guard_tools
from aeon.adapters import anthropic as anth
from aeon.adapters import openai as oai
from aeon.axioms import ActionBlocked, Gate
from aeon.axioms.builtin import deny_tools
from aeon.baseline import Monitor
from tests.conftest import ListSink


@pytest.fixture
def box(gate: Gate) -> ToolBox:
    gate.axioms.add(deny_tools(["delete_file"]))
    b = ToolBox(gate=gate, agent="t")

    @b.tool
    def read_file(path: str, limit: int = 10) -> str:
        """Read a file."""
        return f"contents of {path}"

    @b.tool
    def delete_file(path: str) -> str:
        return f"deleted {path}"

    @b.tool
    def boom() -> str:
        raise RuntimeError("kaput")

    return b


# -- plain ------------------------------------------------------------------------------


def test_toolbox_call_runs_and_audits(box: ToolBox, sink: ListSink) -> None:
    assert box.call("read_file", {"path": "a"}) == "contents of a"
    assert sink.of("decision")[0]["tool"] == "read_file"
    assert sink.of("decision")[0]["agent"] == "t"
    assert sink.of("result")[0]["ok"] is True


def test_toolbox_blocked_propagates(box: ToolBox) -> None:
    with pytest.raises(ActionBlocked):
        box.call("delete_file", {"path": "x"})


def test_toolbox_unknown_tool(box: ToolBox) -> None:
    with pytest.raises(KeyError, match="unknown tool 'nope'"):
        box.call("nope", {})


def test_toolbox_add_and_executor(gate: Gate) -> None:
    b = ToolBox(gate=gate)
    b.add("echo", lambda text: text)
    run = b.as_executor()
    assert run("echo", {"text": "hi"}) == "hi"
    assert "echo" in b


def test_toolbox_safe_call(box: ToolBox) -> None:
    assert box.safe_call("read_file", {"path": "a"}) == "contents of a"
    assert "unknown tool" in box.safe_call("nope")
    assert "RuntimeError: kaput" in box.safe_call("boom")
    assert box.safe_call("delete_file", {"path": "a"}).startswith("Æon blocked this action:")


def test_toolbox_acall_sync_and_async(gate: Gate) -> None:
    b = ToolBox(gate=gate)

    async def aecho(text: str) -> str:
        return text.upper()

    b.add("aecho", aecho)
    b.add("echo", lambda text: text)
    assert asyncio.run(b.acall("aecho", {"text": "hi"})) == "HI"
    assert asyncio.run(b.acall("echo", {"text": "hi"})) == "hi"


def test_toolbox_default_gate_is_lazy() -> None:
    b = ToolBox()
    b.add("echo", lambda text: text)
    assert b.call("echo", {"text": "x"}) == "x"  # default gate: shadow, audit off


# -- openai -----------------------------------------------------------------------------


def _chat_call(call_id: str, name: str, arguments: str) -> Any:
    return SimpleNamespace(
        id=call_id, type="function", function=SimpleNamespace(name=name, arguments=arguments)
    )


def test_openai_chat_completions_shapes(box: ToolBox, sink: ListSink) -> None:
    msg = SimpleNamespace(
        tool_calls=[
            _chat_call("c1", "read_file", json.dumps({"path": "a"})),
            _chat_call("c2", "delete_file", json.dumps({"path": "prod"})),
        ]
    )
    out = oai.run_tool_calls(msg, box)
    assert out[0] == {"role": "tool", "tool_call_id": "c1", "content": "contents of a"}
    assert out[1]["tool_call_id"] == "c2"
    assert out[1]["content"] == ("Æon blocked this action: tool 'delete_file' is on the deny list")
    verdicts = [d["verdict"] for d in sink.of("decision")]
    assert verdicts == ["GO", "BLOCK"]


def test_openai_accepts_full_completion_and_dicts(box: ToolBox) -> None:
    completion = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "c1", "function": {"name": "read_file", "arguments": '{"path":"a"}'}}
                    ]
                }
            }
        ]
    }
    out = oai.run_tool_calls(completion, box)
    assert out == [{"role": "tool", "tool_call_id": "c1", "content": "contents of a"}]


def test_openai_no_tool_calls(box: ToolBox) -> None:
    assert oai.run_tool_calls(SimpleNamespace(tool_calls=None), box) == []


def test_openai_responses_shapes(box: ToolBox) -> None:
    resp = SimpleNamespace(
        output=[
            SimpleNamespace(type="message", content=[]),
            SimpleNamespace(
                type="function_call", call_id="r1", name="read_file", arguments='{"path":"a"}'
            ),
            SimpleNamespace(
                type="function_call", call_id="r2", name="delete_file", arguments='{"path":"p"}'
            ),
        ]
    )
    out = oai.run_tool_calls(resp, box)
    assert out[0] == {"type": "function_call_output", "call_id": "r1", "output": "contents of a"}
    assert out[1]["call_id"] == "r2"
    assert out[1]["output"].startswith("Æon blocked this action:")


@pytest.mark.parametrize("raw", ["{not json", "[1, 2]"])
def test_openai_malformed_arguments_become_error_message(
    box: ToolBox, sink: ListSink, raw: str
) -> None:
    out = oai.run_tool_calls(SimpleNamespace(tool_calls=[_chat_call("c1", "read_file", raw)]), box)
    assert out[0]["tool_call_id"] == "c1"
    assert out[0]["content"].startswith("Error: ")
    assert sink.of("decision") == []  # never reached the gate


def test_openai_empty_arguments_and_unknown_tool(box: ToolBox) -> None:
    out = oai.run_tool_calls(
        SimpleNamespace(tool_calls=[_chat_call("c1", "boom", ""), _chat_call("c2", "nope", "{}")]),
        box,
    )
    assert "kaput" in out[0]["content"]
    assert "unknown tool" in out[1]["content"]


def test_openai_tool_specs(box: ToolBox) -> None:
    chat = oai.tool_specs(box)
    spec = next(s for s in chat if s["function"]["name"] == "read_file")["function"]
    assert spec["description"] == "Read a file."
    assert spec["parameters"] == {
        "type": "object",
        "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["path"],
    }
    resp = oai.tool_specs(box, api="responses")
    assert next(s for s in resp if s["name"] == "read_file")["parameters"] == spec["parameters"]


def test_openai_record_usage() -> None:
    gate = Gate(mode="enforce", monitor=Monitor())
    oai.record_usage(SimpleNamespace(usage=SimpleNamespace(total_tokens=150)), gate, "a")
    oai.record_usage(SimpleNamespace(usage=None), gate, "a")
    oai.record_usage({"usage": {"input_tokens": 10, "output_tokens": 5}}, gate, "a")
    assert gate.monitor is not None
    assert gate.monitor._state("a").tokens_total == 165


def test_record_usage_without_monitor(gate: Gate) -> None:
    oai.record_usage(
        SimpleNamespace(usage=SimpleNamespace(total_tokens=5)), gate, "a"
    )  # no monitor: no-op


# -- anthropic --------------------------------------------------------------------------


def test_anthropic_tool_results(box: ToolBox, sink: ListSink) -> None:
    msg = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="working"),
            SimpleNamespace(type="tool_use", id="tu1", name="read_file", input={"path": "a"}),
            {"type": "tool_use", "id": "tu3", "name": "boom", "input": {}},
            SimpleNamespace(type="tool_use", id="tu2", name="delete_file", input={"path": "p"}),
        ]
    )
    out = anth.run_tool_uses(msg, box)
    assert out[0] == {
        "type": "tool_result",
        "tool_use_id": "tu1",
        "content": "contents of a",
        "is_error": False,
    }
    assert out[1]["is_error"] is True and "kaput" in out[1]["content"]
    assert out[2]["is_error"] is True
    assert out[2]["tool_use_id"] == "tu2"
    assert out[2]["content"].startswith("Æon blocked this action:")
    assert [d["verdict"] for d in sink.of("decision")] == ["GO", "GO", "BLOCK"]


def test_anthropic_bad_input_is_error(box: ToolBox) -> None:
    msg = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", id="t", name="read_file", input="{oops")]
    )
    out = anth.run_tool_uses(msg, box)
    assert out[0]["is_error"] is True and out[0]["content"].startswith("Error: ")


def test_anthropic_specs_and_usage(box: ToolBox) -> None:
    spec = next(s for s in anth.tool_specs(box) if s["name"] == "read_file")
    assert spec["input_schema"]["required"] == ["path"]
    assert spec["description"] == "Read a file."
    gate = Gate(mode="enforce", monitor=Monitor())
    anth.record_usage(
        SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=25)), gate, "a"
    )
    assert gate.monitor is not None
    assert gate.monitor._state("a").tokens_total == 125


# -- langgraph --------------------------------------------------------------------------


class FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"{name} tool"
        self.calls: list[Any] = []

    def invoke(self, input: Any, config: Any = None, **kw: Any) -> str:
        self.calls.append(input)
        return f"{self.name}:{input}"

    async def ainvoke(self, input: Any, config: Any = None, **kw: Any) -> str:
        self.calls.append(input)
        return f"a-{self.name}:{input}"


def test_guard_tools_proxy_allows_and_blocks(gate: Gate, sink: ListSink) -> None:
    gate.axioms.add(deny_tools(["delete_file"]))
    read, delete = FakeTool("read_file"), FakeTool("delete_file")
    g_read, g_delete = guard_tools([read, delete], gate=gate, agent="lg")
    assert isinstance(g_read, GuardedTool)
    assert g_read.name == "read_file" and g_read.description == "read_file tool"
    assert g_read.invoke({"path": "a"}) == "read_file:{'path': 'a'}"
    with pytest.raises(ActionBlocked):
        g_delete.invoke({"path": "p"})
    assert delete.calls == []
    decisions = sink.of("decision")
    assert [d["agent"] for d in decisions] == ["lg", "lg"]
    assert decisions[0]["arg_keys"] == ["path"]


def test_guard_tools_unwraps_tool_call_dict(gate: Gate) -> None:
    seen: list[dict[str, Any]] = []
    gate.subscribe(lambda d: seen.append(dict(d.action.args)))
    (t,) = guard_tools([FakeTool("read_file")], gate=gate)
    t.invoke({"type": "tool_call", "name": "read_file", "args": {"path": "a"}, "id": "1"})
    assert seen == [{"path": "a"}]


def test_guard_tools_async(gate: Gate) -> None:
    gate.axioms.add(deny_tools(["delete_file"]))
    g_read, g_delete = guard_tools([FakeTool("read_file"), FakeTool("delete_file")], gate=gate)
    assert asyncio.run(g_read.ainvoke({"path": "a"})) == "a-read_file:{'path': 'a'}"
    with pytest.raises(ActionBlocked):
        asyncio.run(g_delete.ainvoke({"path": "p"}))


def test_guard_tools_plain_callables(gate: Gate) -> None:
    gate.axioms.add(deny_tools(["delete_file"]))

    def read_file(path: str) -> str:
        return path

    def delete_file(path: str) -> str:
        return path

    g_read, g_delete = guard_tools([read_file, delete_file], gate=gate)
    assert g_read(path="a") == "a"
    with pytest.raises(ActionBlocked):
        g_delete(path="a")


def test_guard_tools_rejects_junk(gate: Gate) -> None:
    with pytest.raises(TypeError):
        guard_tools([object()], gate=gate)


def test_guard_tools_proxy_delegates_attributes(gate: Gate) -> None:
    t = FakeTool("x")
    t.extra = "value"  # type: ignore[attr-defined]
    (g,) = guard_tools([t], gate=gate)
    assert g.extra == "value"
    with pytest.raises(AttributeError):
        _ = g.missing


def test_guard_tools_real_langchain_tool(gate: Gate) -> None:
    tools = pytest.importorskip("langchain_core.tools")
    gate.axioms.add(deny_tools(["delete_file"]))

    @tools.tool
    def read_file(path: str) -> str:
        """Read a file."""
        return f"contents of {path}"

    @tools.tool
    def delete_file(path: str) -> str:
        """Delete a file."""
        return f"deleted {path}"

    g_read, g_delete = guard_tools([read_file, delete_file], gate=gate)
    assert isinstance(g_read, tools.BaseTool)
    assert g_read.invoke({"path": "a"}) == "contents of a"
    assert asyncio.run(g_read.ainvoke({"path": "b"})) == "contents of b"
    with pytest.raises(ActionBlocked):
        g_delete.invoke({"path": "p"})
    assert read_file.invoke({"path": "z"}) == "contents of z"  # original untouched
