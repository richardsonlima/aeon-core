"""Anthropic Messages API tool-use loop helpers.

Duck-typed: nothing here imports the ``anthropic`` package, so the helpers also work with
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


def run_tool_uses(message: Any, toolbox: ToolBox) -> list[dict[str, Any]]:
    """Execute every ``tool_use`` block of an assistant message through the gate.

    Returns ``tool_result`` blocks to send back as the next user message. Denied calls
    and tool errors are returned with ``is_error`` set; nothing here raises for them.
    """
    blocks: list[dict[str, Any]] = []
    for block in get(message, "content") or []:
        if get(block, "type") != "tool_use":
            continue
        try:
            args = parse_arguments(get(block, "input"))
            text, is_error = toolbox.run_text(get(block, "name", ""), args)
        except ValueError as exc:
            text, is_error = f"Error: {exc}", True
        blocks.append(
            {
                "type": "tool_result",
                "tool_use_id": get(block, "id"),
                "content": text,
                "is_error": is_error,
            }
        )
    return blocks


def record_usage(message: Any, gate: Gate | None = None, agent: str = "default") -> None:
    """Feed the message's token usage to the gate's budget monitor, when present."""
    g = gate if gate is not None else default_gate()
    tokens = total_tokens(get(message, "usage"))
    if g.monitor is not None and tokens is not None:
        g.monitor.record_usage(agent, tokens=tokens)


def tool_specs(toolbox: ToolBox) -> list[dict[str, Any]]:
    """Tool definitions for the request (``input_schema`` form)."""
    return [
        {
            "name": name,
            "description": description(fn),
            "input_schema": parameters_schema(fn),
        }
        for name, fn in toolbox.tools.items()
    ]
