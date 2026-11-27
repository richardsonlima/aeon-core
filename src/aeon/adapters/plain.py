"""Plain Python tools behind the gate."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from aeon.adapters._common import as_text, blocked_message
from aeon.axioms import ActionBlocked, Gate, enforce

F = TypeVar("F", bound=Callable[..., Any])


class ToolBox:
    """A registry of Python tools. Every call goes through the gate first.

    >>> box = ToolBox(gate=my_gate)
    >>> @box.tool
    ... def read_file(path: str) -> str: ...
    >>> box.call("read_file", {"path": "notes.txt"})
    """

    def __init__(self, gate: Gate | None = None, agent: str = "default") -> None:
        self.gate = gate
        self.agent = agent
        self._tools: dict[str, Callable[..., Any]] = {}
        self._run = enforce(self._execute, gate=gate, agent=agent)
        self._arun = enforce(self._aexecute, gate=gate, agent=agent)

    # -- registry ----------------------------------------------------------------------

    def tool(self, fn: F) -> F:
        """Register ``fn`` under its own name. Usable as a decorator."""
        self.add(fn.__name__, fn)
        return fn

    def add(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    @property
    def tools(self) -> Mapping[str, Callable[..., Any]]:
        return dict(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def _lookup(self, name: str) -> Callable[..., Any]:
        try:
            return self._tools[name]
        except KeyError:
            known = ", ".join(sorted(self._tools)) or "none"
            raise KeyError(f"unknown tool {name!r}; registered tools: {known}") from None

    def _execute(self, tool: str, args: Mapping[str, Any]) -> Any:
        return self._lookup(tool)(**args)

    async def _aexecute(self, tool: str, args: Mapping[str, Any]) -> Any:
        result = self._lookup(tool)(**args)
        return await result if inspect.isawaitable(result) else result

    # -- calling -----------------------------------------------------------------------

    def call(self, name: str, args: Mapping[str, Any] | None = None) -> Any:
        """Run a tool through the gate. A denied call raises :class:`ActionBlocked`."""
        self._lookup(name)
        return self._run(name, dict(args or {}))

    async def acall(self, name: str, args: Mapping[str, Any] | None = None) -> Any:
        """Async variant of :meth:`call`. Sync tools are called directly, async ones awaited."""
        self._lookup(name)
        return await self._arun(name, dict(args or {}))

    def as_executor(self) -> Callable[[str, Mapping[str, Any]], Any]:
        """``(tool, args) -> result``, for code that already takes an executor."""
        return self.call

    def safe_call(self, name: str, args: Mapping[str, Any] | None = None) -> str:
        """Like :meth:`call` but returns text for the model instead of raising."""
        return self.run_text(name, args)[0]

    def run_text(self, name: str, args: Mapping[str, Any] | None = None) -> tuple[str, bool]:
        """Run a tool and return ``(text, is_error)``. Never raises for tool or gate errors."""
        try:
            return as_text(self.call(name, args)), False
        except ActionBlocked as exc:
            return blocked_message(exc), True
        except KeyError as exc:
            return f"Error: {exc.args[0]}", True
        except Exception as exc:
            return f"Error: {type(exc).__name__}: {exc}", True
