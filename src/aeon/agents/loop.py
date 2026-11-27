"""A tool-calling agent loop with every tool call behind the gate.

:class:`Agent` sends the conversation to a model, runs each tool call the model asks for
through a :class:`~aeon.adapters.ToolBox` (so through the gate), returns the results to
the model, and repeats until the model answers without a tool call. It works with the
official ``openai`` and ``anthropic`` SDK clients and with the clients in
:mod:`aeon.agents.clients`, and it never imports an SDK.

The loop stops early when the operator kill-switch is engaged or the agent is held in
Safe State, so a stopped agent does not keep spending tokens.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from aeon.adapters._common import get, parse_arguments, total_tokens
from aeon.adapters.anthropic import tool_specs as anthropic_specs
from aeon.adapters.openai import tool_specs as openai_specs
from aeon.adapters.plain import ToolBox
from aeon.axioms import Gate, default_gate

__all__ = ["Agent", "AgentRun", "ToolCall"]

Provider = Literal["auto", "openai", "anthropic"]
StopReason = Literal["done", "max_steps", "kill_switch", "safe_state"]


@dataclass(frozen=True)
class ToolCall:
    """One tool call the model asked for, and what happened to it.

    Attributes:
        name: Tool name as the model sent it.
        args: Decoded arguments (empty when they could not be decoded).
        result: The text returned to the model.
        is_error: The call failed, was blocked, or had bad arguments.
        blocked: The gate denied the call (enforce mode, or kill-switch or Safe State).
    """

    name: str
    args: dict[str, Any]
    result: str
    is_error: bool
    blocked: bool


@dataclass
class AgentRun:
    """The outcome of :meth:`Agent.run`.

    Attributes:
        text: The model's final answer, or ``None`` when the loop stopped first.
        stop_reason: ``done``, ``max_steps``, ``kill_switch`` or ``safe_state``.
        steps: Number of model calls.
        tool_calls: Every tool call, in order.
        tokens: Total tokens reported by the provider, when it reports usage.
        messages: The full conversation, ready to continue.
    """

    text: str | None
    stop_reason: StopReason
    steps: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    messages: list[Any] = field(default_factory=list)

    @property
    def blocked(self) -> list[ToolCall]:
        """The calls the gate denied."""
        return [c for c in self.tool_calls if c.blocked]


class Agent:
    """A model, a set of gated tools, and the loop between them.

    Args:
        client: An ``openai.OpenAI`` or ``anthropic.Anthropic`` client, or one of
            :class:`~aeon.agents.OpenAICompatible` / :class:`~aeon.agents.AnthropicClient`.
        model: Model name for the provider.
        toolbox: The tools. Every call goes through ``toolbox.gate`` (or the default gate).
        provider: ``openai`` (Chat Completions), ``anthropic`` (Messages) or ``auto``,
            which picks from the client's shape.
        system: Optional system prompt.
        max_steps: Maximum model calls per :meth:`run`.
        max_tokens: Output token cap per model call. Not sent to Chat Completions when
            ``None`` (some models reject the field); the Messages API needs one, so it
            defaults to 1024 there.
        request: Extra request fields passed to every call, for example
            ``{"temperature": 0}``.

    Example:
        >>> from aeon.agents import Agent, OpenAICompatible  # doctest: +SKIP
        >>> agent = Agent(OpenAICompatible("http://localhost:11434/v1"), "qwen2.5:3b", box)
        >>> agent.run("Summarise notes.txt").text  # doctest: +SKIP
    """

    def __init__(
        self,
        client: Any,
        model: str,
        toolbox: ToolBox,
        *,
        provider: Provider = "auto",
        system: str | None = None,
        max_steps: int = 10,
        max_tokens: int | None = None,
        request: Mapping[str, Any] | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.client = client
        self.model = model
        self.toolbox = toolbox
        self.provider: Literal["openai", "anthropic"] = (
            _detect(client) if provider == "auto" else provider
        )
        self.system = system
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.request = dict(request or {})

    @property
    def gate(self) -> Gate:
        """The gate every tool call goes through."""
        return self.toolbox.gate if self.toolbox.gate is not None else default_gate()

    def run(self, prompt: str | Sequence[Any]) -> AgentRun:
        """Run the loop for one user prompt, or continue a list of messages."""
        messages: list[Any] = (
            [{"role": "user", "content": prompt}] if isinstance(prompt, str) else list(prompt)
        )
        if self.provider == "anthropic":
            return self._run_anthropic(messages)
        return self._run_openai(messages)

    # -- shared ------------------------------------------------------------------------

    def _halted(self) -> StopReason | None:
        g = self.gate
        if g.kill_switch.engaged:
            return "kill_switch"
        if g.safe_state(self.toolbox.agent) is not None:
            return "safe_state"
        return None

    def _call_tool(self, name: str, raw_args: Any) -> ToolCall:
        try:
            args = parse_arguments(raw_args)
        except ValueError as exc:
            return ToolCall(name, {}, f"Error: {exc}", True, False)
        before = self.gate.counters["denied"]
        text, is_error = self.toolbox.run_text(name, args)
        blocked = self.gate.counters["denied"] > before
        return ToolCall(name, args, text, is_error, blocked)

    def _usage(self, reply: Any) -> int:
        tokens = total_tokens(get(reply, "usage")) or 0
        monitor = self.gate.monitor
        if monitor is not None and tokens:
            monitor.record_usage(self.toolbox.agent, tokens=tokens)
        return tokens

    # -- Chat Completions --------------------------------------------------------------

    def _run_openai(self, messages: list[Any]) -> AgentRun:
        if self.system and not any(get(m, "role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.system})
        extra: dict[str, Any] = dict(self.request)
        specs = openai_specs(self.toolbox)
        if specs:
            extra.setdefault("tools", specs)
        if self.max_tokens is not None:  # omitted otherwise: some models reject the field
            extra.setdefault("max_tokens", self.max_tokens)
        run = AgentRun(None, "max_steps", 0, messages=messages)
        for _ in range(self.max_steps):
            halted = self._halted()
            if halted is not None:
                run.stop_reason = halted
                return run
            reply = self.client.chat.completions.create(
                model=self.model, messages=messages, **extra
            )
            run.steps += 1
            run.tokens += self._usage(reply)
            msg = get(get(reply, "choices")[0], "message")
            calls = get(msg, "tool_calls") or []
            messages.append(_openai_assistant(msg, calls))
            if not calls:
                run.text = get(msg, "content") or ""
                run.stop_reason = "done"
                return run
            for call in calls:
                fn = get(call, "function")
                tc = self._call_tool(get(fn, "name", ""), get(fn, "arguments"))
                run.tool_calls.append(tc)
                messages.append(
                    {"role": "tool", "tool_call_id": get(call, "id"), "content": tc.result}
                )
        return run

    # -- Messages ----------------------------------------------------------------------

    def _run_anthropic(self, messages: list[Any]) -> AgentRun:
        specs = anthropic_specs(self.toolbox)
        run = AgentRun(None, "max_steps", 0, messages=messages)
        extra: dict[str, Any] = dict(self.request)
        if self.system:
            extra.setdefault("system", self.system)
        if specs:
            extra.setdefault("tools", specs)
        for _ in range(self.max_steps):
            halted = self._halted()
            if halted is not None:
                run.stop_reason = halted
                return run
            reply = self.client.messages.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens or 1024,
                **extra,
            )
            run.steps += 1
            run.tokens += self._usage(reply)
            blocks = [_block(b) for b in get(reply, "content") or []]
            messages.append({"role": "assistant", "content": blocks})
            uses = [b for b in blocks if b.get("type") == "tool_use"]
            if not uses:
                run.text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                run.stop_reason = "done"
                return run
            results = []
            for use in uses:
                tc = self._call_tool(str(use.get("name", "")), use.get("input"))
                run.tool_calls.append(tc)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.get("id"),
                        "content": tc.result,
                        "is_error": tc.is_error,
                    }
                )
            messages.append({"role": "user", "content": results})
        return run


def _detect(client: Any) -> Literal["openai", "anthropic"]:
    if get(client, "chat") is not None:
        return "openai"
    if get(client, "messages") is not None:
        return "anthropic"
    raise ValueError("cannot tell the provider from the client; pass provider=")


def _openai_assistant(msg: Any, calls: Sequence[Any]) -> dict[str, Any]:
    """The assistant turn as a plain dict, which every Chat Completions server accepts.

    Fields the server added (for example OpenRouter's ``reasoning_details``) are kept and
    sent back unchanged, since reasoning models need them to continue.
    """
    out: dict[str, Any] = {k: v for k, v in _fields(msg).items() if v is not None}
    out["role"] = "assistant"
    out["content"] = get(msg, "content") or ""
    out.pop("tool_calls", None)
    if calls:
        out["tool_calls"] = [
            {
                "id": get(c, "id"),
                "type": "function",
                "function": {
                    "name": get(get(c, "function"), "name", ""),
                    "arguments": _args_text(get(get(c, "function"), "arguments")),
                },
            }
            for c in calls
        ]
    return out


def _fields(msg: Any) -> dict[str, Any]:
    if isinstance(msg, Mapping):
        return dict(msg)
    dump = getattr(msg, "model_dump", None)  # SDK objects (pydantic)
    if callable(dump):
        value = dump(exclude_none=True)
        return dict(value) if isinstance(value, Mapping) else {}
    return {}


def _args_text(raw: Any) -> str:
    if raw is None:
        return "{}"
    if isinstance(raw, str):
        return raw
    return json.dumps(raw)


def _block(block: Any) -> dict[str, Any]:
    """A Messages API content block as a plain dict (SDK objects or dicts)."""
    kind = get(block, "type")
    if kind == "text":
        return {"type": "text", "text": get(block, "text", "")}
    if kind == "tool_use":
        return {
            "type": "tool_use",
            "id": get(block, "id"),
            "name": get(block, "name"),
            "input": get(block, "input") or {},
        }
    if isinstance(block, Mapping):
        return dict(block)
    dump = getattr(block, "model_dump", None)
    return dump() if callable(dump) else {"type": kind}
