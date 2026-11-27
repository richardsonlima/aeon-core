"""OpenAI tool-calling loop helpers (Chat Completions and Responses).

Duck-typed: nothing here imports the ``openai`` package, so the helpers also work with
dict payloads and test doubles.
"""

from __future__ import annotations

from typing import Any

from aeon.adapters._common import (
    description,
    get,
    parameters_schema,
    parse_arguments,
    total_tokens,
)
from aeon.adapters.plain import ToolBox
from aeon.axioms import Gate, default_gate


def _chat_message(obj: Any) -> Any:
    choices = get(obj, "choices")
    if choices:
        return get(choices[0], "message")
    return obj


def _run(box: ToolBox, name: str, raw: Any) -> tuple[str, bool]:
    try:
        args = parse_arguments(raw)
    except ValueError as exc:
        return f"Error: {exc}", True
    return box.run_text(name, args)


def run_tool_calls(message_or_response: Any, toolbox: ToolBox) -> list[dict[str, Any]]:
    """Execute every tool call in a model reply and return the result items.

    Accepts a Chat Completions message or full completion (returns ``role: tool``
    messages) or a Responses API response (returns ``function_call_output`` items).
    Denied calls come back as text the model can react to; nothing here raises for a
    blocked action, a bad tool name or malformed arguments.
    """
    output = get(message_or_response, "output")
    if isinstance(output, (list, tuple)):
        results: list[dict[str, Any]] = []
        for item in output:
            if get(item, "type") != "function_call":
                continue
            text, _ = _run(toolbox, get(item, "name", ""), get(item, "arguments"))
            results.append(
                {"type": "function_call_output", "call_id": get(item, "call_id"), "output": text}
            )
        return results

    message = _chat_message(message_or_response)
    calls = get(message, "tool_calls") or []
    messages: list[dict[str, Any]] = []
    for call in calls:
        fn = get(call, "function")
        text, _ = _run(toolbox, get(fn, "name", ""), get(fn, "arguments"))
        messages.append({"role": "tool", "tool_call_id": get(call, "id"), "content": text})
    return messages


def record_usage(response: Any, gate: Gate | None = None, agent: str = "default") -> None:
    """Feed the response's token usage to the gate's budget monitor, when present."""
    g = gate if gate is not None else default_gate()
    tokens = total_tokens(get(response, "usage"))
    if g.monitor is not None and tokens is not None:
        g.monitor.record_usage(agent, tokens=tokens)


def tool_specs(toolbox: ToolBox, *, api: str = "chat") -> list[dict[str, Any]]:
    """Tool definitions for the request. ``api`` is ``"chat"`` or ``"responses"``."""
    specs: list[dict[str, Any]] = []
    for name, fn in toolbox.tools.items():
        params = parameters_schema(fn)
        if api == "responses":
            specs.append(
                {
                    "type": "function",
                    "name": name,
                    "description": description(fn),
                    "parameters": params,
                }
            )
        else:
            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description(fn),
                        "parameters": params,
                    },
                }
            )
    return specs
