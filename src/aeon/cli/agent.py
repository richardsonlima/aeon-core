"""``aeon agent run``: run a real LLM agent from the command line, tools behind the gate.

The tools come from a Python file (trusted code, like axiom files): its ``TOOLS`` list if
it has one, otherwise every public function defined in it. The gate is built from
``aeon.toml`` (mode, axioms, audit, budget), so the run is recorded like any other.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["PROVIDERS", "add_parser", "cmd_agent_run", "load_tools", "make_client"]

from aeon.agents.models import PROVIDERS


def _error(message: str, hint: str | None = None) -> Exception:
    from aeon.cli.main import CLIError

    return CLIError(message, hint)


def load_tools(path: Path) -> list[Callable[..., Any]]:
    """Import ``path`` and return its tools: ``TOOLS`` if defined, else public functions."""
    if not path.is_file():
        raise _error(f"tools file not found: {path}", "pass a Python file with tool functions")
    sys.path.insert(0, str(path.resolve().parent))
    try:
        ns = runpy.run_path(str(path), run_name="aeon_agent_tools")
    except Exception as exc:
        raise _error(f"{path}: error while importing tools: {exc!r}") from None
    declared = ns.get("TOOLS")
    if declared is not None:
        tools = [t for t in declared if callable(t)]
    else:
        tools = [
            v
            for k, v in ns.items()
            if inspect.isfunction(v)
            and not k.startswith("_")
            and v.__module__ == "aeon_agent_tools"
        ]
    if not tools:
        raise _error(f"{path}: no tools found", "define functions, or a TOOLS = [...] list")
    return tools


def _pick_provider(name: str | None) -> str:
    if name:
        return name
    for candidate in ("openrouter", "anthropic", "openai"):
        env = PROVIDERS[candidate][1]
        if env and os.environ.get(env):
            return candidate
    raise _error(
        "no provider: no API key in the environment",
        "set OPENROUTER_API_KEY, ANTHROPIC_API_KEY or OPENAI_API_KEY, or pass --provider ollama",
    )


def make_client(provider: str, model: str, base_url: str | None = None) -> Any:
    """Resolve ``provider`` and ``model`` to a :class:`~aeon.agents.Model`."""
    from aeon.agents import resolve_model

    try:
        return resolve_model(f"{provider}:{model}", base_url=base_url)
    except ValueError as exc:
        hint = "export the API key" if "not set" in str(exc) else None
        raise _error(str(exc), hint) from None


def cmd_agent_run(args: argparse.Namespace) -> int:
    """Run the agent loop once and print each tool call, the answer and the counters."""
    from aeon.adapters import ToolBox
    from aeon.agents import Agent, ProviderError
    from aeon.cli.main import _config
    from aeon.config import ConfigError, build_gate

    model = args.model or os.environ.get("AEON_LLM_MODEL")
    if not model:
        raise _error("no model", "pass --model, or set AEON_LLM_MODEL")
    provider = _pick_provider(args.provider)
    resolved = make_client(provider, model, args.base_url)
    tools_path = Path(args.tools)
    tools = load_tools(tools_path)

    cfg = _config(args)
    if args.mode:
        cfg.mode = args.mode
    try:
        gate = build_gate(cfg)
    except ConfigError as exc:
        raise _error(str(exc), "check the axiom files listed in aeon.toml") from None
    box = ToolBox(gate=gate, agent=args.agent)
    for fn in tools:
        box.add(fn.__name__, fn)
    if not args.json:
        print(f"tools: {tools_path.resolve()} ({', '.join(box.tools)})", file=sys.stderr)
        print(f"provider {provider}, model {model}, mode {gate.mode.value}", file=sys.stderr)

    agent = Agent(
        resolved,
        box,
        name=args.agent,
        instructions=args.system,
        max_steps=args.max_steps,
        max_tokens=args.max_tokens,
        approval=_approve_at_prompt if sys.stdin.isatty() else "deny",
    )
    try:
        run = agent.run(args.prompt)
    except ProviderError as exc:
        raise _error(str(exc), "check the model name, the API key and the base URL") from None
    finally:
        flush = getattr(gate.audit, "flush", None)
        if callable(flush):
            flush(5)

    data = _as_data(run, provider, model, gate)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        _print_run(run, gate)
    return 0


def _as_data(run: Any, provider: str, model: str, gate: Any) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "mode": gate.mode.value,
        "stop_reason": run.stop_reason,
        "steps": run.steps,
        "tokens": run.tokens,
        "text": run.text,
        "tool_calls": [
            {
                "name": c.name,
                "args": c.args,
                "blocked": c.blocked,
                "is_error": c.is_error,
                "result": c.result,
            }
            for c in run.tool_calls
        ],
        "counters": dict(gate.counters),
    }


def _print_run(run: Any, gate: Any) -> None:
    for c in run.tool_calls:
        mark = " BLOCKED" if c.blocked else (" error" if c.is_error else "")
        print(f"-> {c.name}({json.dumps(c.args, ensure_ascii=False)}){mark}")
        print(f"   {c.result[:300]}")
    print(run.text if run.text is not None else f"[stopped: {run.stop_reason}]")
    k = gate.counters
    print(
        f"\n[aeon] stop={run.stop_reason} steps={run.steps} tokens={run.tokens} "
        f"decisions={k['decisions']} denied={k['denied']}",
        file=sys.stderr,
    )


def _approve_at_prompt(call: Any) -> bool:
    answer = input(f"approve {call.name}({json.dumps(call.args, ensure_ascii=False)})? [y/N] ")
    return answer.strip().lower() in ("y", "yes", "s", "sim")


def add_parser(sub: Any, add: Callable[..., argparse.ArgumentParser]) -> None:
    """Register ``aeon agent run`` on the top-level subparsers."""
    ag = sub.add_parser(
        "agent",
        help="run a real LLM agent with its tools behind the gate",
        description="run a real LLM agent with its tools behind the gate",
    )
    ags = ag.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    sp = add("run", cmd_agent_run, "run one prompt through the agent loop", ags)
    sp.add_argument("prompt", help="the user prompt")
    sp.add_argument("--tools", required=True, help="Python file with the tool functions")
    sp.add_argument("--model", help="model name (default: $AEON_LLM_MODEL)")
    sp.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help="default: the first of OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY set",
    )
    sp.add_argument("--base-url", help="override the provider's API URL")
    sp.add_argument("--system", help="system prompt")
    sp.add_argument("--agent", default="cli-agent", help="agent name in the gate and audit")
    sp.add_argument("--max-steps", type=int, default=10)
    sp.add_argument("--max-tokens", type=int, help="output token cap per model call")
    sp.add_argument("--mode", choices=["shadow", "enforce"], help="override the configured mode")
