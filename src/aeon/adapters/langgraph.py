"""Guard LangChain / LangGraph tools so every invocation passes the gate.

Nothing is imported from ``langchain`` here. A tool is anything with ``name`` and
``invoke`` / ``ainvoke``, or a plain callable.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from aeon.axioms import Action, Gate, enforce


def _args_of(value: Any) -> dict[str, Any]:
    """Tool arguments from the input of ``invoke``: a mapping, a tool-call dict or a scalar."""
    if isinstance(value, Mapping):
        if value.get("type") == "tool_call" and isinstance(value.get("args"), Mapping):
            return dict(value["args"])
        return dict(value)
    return {} if value is None else {"input": value}


class GuardedTool:
    """A thin proxy over a tool object. Unknown attributes are delegated to the original."""

    def __init__(self, tool: Any, gate: Gate | None = None, agent: str = "default") -> None:
        name = str(tool.name)

        def to_action(a: tuple[Any, ...], kw: dict[str, Any]) -> Action:
            value = a[0] if a else kw.get("input")
            return Action(tool=name, args=_args_of(value), agent=agent)

        self._tool = tool
        self._invoke: Callable[..., Any] | None = None
        self._ainvoke: Callable[..., Any] | None = None
        if callable(getattr(tool, "invoke", None)):
            self._invoke = enforce(
                lambda input, config=None, **kw: tool.invoke(input, config, **kw),
                gate=gate,
                agent=agent,
                to_action=to_action,
            )
        if callable(getattr(tool, "ainvoke", None)):

            async def _raw_ainvoke(input: Any, config: Any = None, **kw: Any) -> Any:
                return await tool.ainvoke(input, config, **kw)

            self._ainvoke = enforce(_raw_ainvoke, gate=gate, agent=agent, to_action=to_action)

    @property
    def __wrapped__(self) -> Any:
        return self._tool

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        if self._invoke is None:
            raise AttributeError(f"{self._tool!r} has no invoke")
        return self._invoke(input, config, **kwargs)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        if self._ainvoke is None:
            raise AttributeError(f"{self._tool!r} has no ainvoke")
        return await self._ainvoke(input, config, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._tool(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        if item in {"_tool", "_invoke", "_ainvoke"}:
            raise AttributeError(item)
        return getattr(self._tool, item)

    def __repr__(self) -> str:
        return f"GuardedTool({self._tool!r})"


def _guard_object(tool: Any, gate: Gate | None, agent: str) -> Any:
    """Guard a tool object.

    Pydantic tools (LangChain ``BaseTool``) are shallow-copied with guarded
    ``invoke``/``ainvoke`` so they stay real tool instances for ``ToolNode``. Anything
    else gets a proxy.
    """
    proxy = GuardedTool(tool, gate, agent)
    if not callable(getattr(tool, "model_copy", None)):
        return proxy
    try:
        clone = tool.model_copy()
        for attr in ("invoke", "ainvoke"):
            if getattr(proxy, f"_{attr}") is not None:
                object.__setattr__(clone, attr, getattr(proxy, attr))
    except Exception:
        return proxy
    return clone


def guard_tools(
    tools: Sequence[Any], gate: Gate | None = None, agent: str = "default"
) -> list[Any]:
    """Wrap each tool so invoking it is checked by the gate first.

    Tool objects (``name`` plus ``invoke``/``ainvoke``) become :class:`GuardedTool`
    proxies, except pydantic tools such as LangChain's ``BaseTool``: those are copied with
    guarded ``invoke``/``ainvoke`` so ``isinstance`` checks and ``ToolNode`` keep working.
    Plain callables are wrapped with ``enforce`` and keep their own name. A denied call
    raises :class:`aeon.axioms.ActionBlocked`.
    """
    guarded: list[Any] = []
    for tool in tools:
        has_object_api = hasattr(tool, "name") and (
            callable(getattr(tool, "invoke", None)) or callable(getattr(tool, "ainvoke", None))
        )
        if has_object_api:
            guarded.append(_guard_object(tool, gate, agent))
        elif callable(tool) and not inspect.isclass(tool):
            guarded.append(enforce(tool, gate=gate, agent=agent))
        else:
            raise TypeError(f"cannot guard {tool!r}: expected a tool object or a callable")
    return guarded
