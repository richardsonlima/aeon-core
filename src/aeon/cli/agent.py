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

# provider -> (base URL, API key variable, wire format)
PROVIDERS: dict[str, tuple[str | None, str | None, str]] = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "openai"),
    "anthropic": ("https://api.anthropic.com", "ANTHROPIC_API_KEY", "anthropic"),
    "ollama": ("http://localhost:11434/v1", None, "openai"),
    "compatible": (None, "OPENAI_API_KEY", "openai"),
}


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


def make_client(provider: str, base_url: str | None = None) -> tuple[Any, str]:
    """Build the HTTP client for ``provider`` and return it with its wire format."""
    from aeon.agents import AnthropicClient, OpenAICompatible

    default_url, key_env, wire = PROVIDERS[provider]
    url = base_url or default_url
    if url is None:
        raise _error("--provider compatible needs --base-url")
    key = os.environ.get(key_env) if key_env else None
    if key_env and not key and provider != "compatible":
        raise _error(f"{key_env} is not set", f"export {key_env}=... before running")
    if wire == "anthropic":
        return AnthropicClient(key, base_url=url), wire
    headers = {"x-title": "aeon-core"} if provider == "openrouter" else None
    return OpenAICompatible(url, key or "", headers=headers), wire


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
    client, wire = make_client(provider, args.base_url)
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
        client,
        model,
        box,
        provider="anthropic" if wire == "anthropic" else "openai",
        system=args.system,
        max_steps=args.max_steps,
        max_tokens=args.max_tokens,
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
