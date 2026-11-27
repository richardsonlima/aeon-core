"""The ``aeon`` command line. Stdlib ``argparse`` only, so the core install stays light.

Every command that prints data accepts ``--json``. Expected failures print a message and
a fix hint and exit with a non-zero code; they never print a stack trace.
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from aeon._version import __version__

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


class CLIError(Exception):
    def __init__(self, message: str, hint: str | None = None, code: int = EXIT_FAIL) -> None:
        super().__init__(message)
        self.hint = hint
        self.code = code


def out(args: argparse.Namespace, data: Any, text: Callable[[], str] | str) -> None:
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    else:
        print(text() if callable(text) else text)


def _config(args: argparse.Namespace) -> Any:
    from aeon.config import ConfigError, load_config

    try:
        return load_config(Path(args.config) if getattr(args, "config", None) else None)
    except ConfigError as exc:
        raise CLIError(str(exc), "fix the file, or run `aeon init` to create a fresh one") from None


def _audit_spec(args: argparse.Namespace) -> str:
    if getattr(args, "file", None):
        return str(args.file)
    cfg = _config(args)
    if not cfg.audit_enabled:
        raise CLIError("audit is disabled in config", "set [aeon.audit] path, or pass --file")
    return str(cfg.audit_location())


# -- version / doctor ----------------------------------------------------------------------


def cmd_version(args: argparse.Namespace) -> int:
    import platform

    data = {
        "aeon": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    out(args, data, f"aeon {__version__} (Python {data['python']}, {data['platform']})")
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    from aeon.cli.doctor import run_doctor

    checks = run_doctor(args.config)
    failed = [c for c in checks if c["status"] == "fail"]

    def text() -> str:
        icon = {"ok": "ok  ", "warn": "warn", "fail": "FAIL", "info": "info"}
        lines = [f"aeon doctor ({__version__})", ""]
        for c in checks:
            lines.append(f"  [{icon[c['status']]}] {c['name']}: {c['detail']}")
            if c.get("hint") and c["status"] != "ok":
                lines.append(f"         fix: {c['hint']}")
        lines.append("")
        lines.append("All checks passed." if not failed else f"{len(failed)} check(s) failed.")
        return "\n".join(lines)

    out(args, {"ok": not failed, "checks": checks}, text)
    return EXIT_FAIL if failed else EXIT_OK


# -- init ----------------------------------------------------------------------------------

CONFIG_TEMPLATE = """\
# Æon configuration. Docs: https://www.richardsonlima.com.br/aeon/docs/reference/config/
[aeon]
# shadow: decide and record, never enforce. Move to "enforce" after reviewing the audit log.
mode = "shadow"
axioms = ["aeon_axioms.py"]
include_args = false   # true records raw tool arguments in the audit log

[aeon.audit]
path = ".aeon/audit.jsonl"   # or "sqlite:.aeon/audit.db", or "off"
fsync = false

[aeon.budget]
baseline_n = 50     # results used to calibrate the baseline per agent
alert_at = 5.0
limit_at = 10.0
block_at = 20.0
# p99_ms = 300      # absolute envelope, checked without calibration
# error_rate = 0.02

[aeon.chaos]
environment = "dev"
max_blast_radius = "staging"
"""

AXIOMS_TEMPLATE = '''\
"""Example axioms. Each returns True to pass, or False / a reason string to object."""

from aeon.axioms import axiom
from aeon.axioms.builtin import require_approval

DESTRUCTIVE = {"delete_file", "drop_table", "send_email", "transfer_funds"}


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """Destructive tools need explicit approval."""
    return action.tool not in DESTRUCTIVE or action.approved


@axiom(on_violation="ALERT")
def flag_external_urls(action):
    """Record calls that reach outside the company domain."""
    url = str(action.args.get("url", ""))
    return not url or url.startswith("https://internal.example.com")


deploys_need_approval = require_approval({"deploy"})
'''


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path)
    root.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    for name, body in (("aeon.toml", CONFIG_TEMPLATE), ("aeon_axioms.py", AXIOMS_TEMPLATE)):
        p = root / name
        if p.exists() and not args.force:
            skipped.append(str(p))
            continue
        p.write_text(body, "utf-8")
        written.append(str(p))
    (root / ".aeon").mkdir(exist_ok=True)

    def text() -> str:
        lines = [f"created {w}" for w in written] + [
            f"kept {s} (use --force to overwrite)" for s in skipped
        ]
        lines += [
            "",
            "Mode is shadow: decisions are recorded, nothing is blocked yet.",
            "Next: wrap your executor with `enforce`, then run `aeon doctor`.",
        ]
        return "\n".join(lines)

    out(args, {"written": written, "skipped": skipped}, text)
    return EXIT_OK


# -- axioms --------------------------------------------------------------------------------


def _axiom_rows(files: Sequence[str]) -> list[dict[str, Any]]:
    from aeon.config import ConfigError, load_axiom_file

    rows = []
    for f in files:
        try:
            specs = load_axiom_file(f)
        except ConfigError as exc:
            raise CLIError(str(exc), "check the file path and that it imports cleanly") from None
        for s in specs:
            rows.append(
                {
                    "file": str(f),
                    "name": s.name,
                    "level": s.level.name,
                    "tools": sorted(s.tools) if s.tools else None,
                    "description": s.description,
                }
            )
    return rows


def cmd_axioms_list(args: argparse.Namespace) -> int:
    cfg = _config(args)
    files = args.files or [
        str(Path(a) if Path(a).is_absolute() else cfg.root / a) for a in cfg.axioms
    ]
    if not files:
        raise CLIError("no axiom files configured", "pass a file or set `axioms` in aeon.toml")
    rows = _axiom_rows(files)

    def text() -> str:
        if not rows:
            return "no axioms found"
        w = max(len(r["name"]) for r in rows)
        return "\n".join(
            f"{r['level']:<6} {r['name']:<{w}}  {r['description']}"
            + (f"  [tools: {', '.join(r['tools'])}]" if r["tools"] else "")
            for r in rows
        )

    out(args, rows, text)
    return EXIT_OK


def cmd_axioms_check(args: argparse.Namespace) -> int:
    from aeon.axioms import Action, Gate

    rows = _axiom_rows([args.file])
    if not rows:
        raise CLIError(
            f"{args.file} declares no axioms",
            "decorate functions with @axiom or assign builtin factories at module level",
        )
    from aeon.config import load_axiom_file

    problems = []
    gate = Gate(load_axiom_file(args.file), mode="shadow")
    probe = Action(tool="__aeon_probe__", args={})
    d = gate.decide(probe)
    if d.gate_error:
        problems.append(f"an axiom raised on a probe action: {d.gate_error}")
    data = {"file": args.file, "axioms": rows, "ok": not problems, "problems": problems}

    def text() -> str:
        lines = [f"{args.file}: {len(rows)} axiom(s)"]
        lines += [f"  {r['level']:<6} {r['name']}" for r in rows]
        lines += [f"  problem: {p}" for p in problems]
        lines.append("ok" if not problems else "check failed")
        return "\n".join(lines)

    out(args, data, text)
    return EXIT_OK if not problems else EXIT_FAIL


# -- run -----------------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    from aeon.axioms import default_gate, set_default_gate

    script = Path(args.script)
    if not script.is_file():
        raise CLIError(f"script not found: {script}", "pass the path to a Python file")
    os.environ["AEON_MODE"] = args.mode
    set_default_gate(None)
    sys.argv = [str(script), *args.script_args]
    sys.path.insert(0, str(script.resolve().parent))
    code = EXIT_OK
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (EXIT_OK if exc.code is None else 1)
    gate = default_gate()
    audit = gate.audit
    if audit is not None and hasattr(audit, "flush"):
        audit.flush(5)
    c = gate.counters
    print(
        f"\n[aeon] mode={gate.mode.value} decisions={c['decisions']} allowed={c['allowed']} "
        f"denied={c['denied']} gate_errors={c['gate_errors']}",
        file=sys.stderr,
    )
    return int(code)


# -- chaos ---------------------------------------------------------------------------------


def cmd_chaos_list(args: argparse.Namespace) -> int:
    from aeon.chaos import CATALOG

    rows = [cls().describe() for cls in CATALOG.values()]

    def text() -> str:
        lines = []
        for r in rows:
            lines.append(
                f"{r['name']:<26} max radius {r['max_blast_radius']:<12} {r['description']}"
            )
            if r["aliases"]:
                lines.append(f"{'':<26} aliases: {', '.join(r['aliases'])}")
        return "\n".join(lines)

    out(args, rows, text)
    return EXIT_OK


def _find_campaign(target: str, cfg: Any) -> Any:
    from aeon.chaos import Campaign, resolve

    p = Path(target)
    if p.suffix == ".toml" and p.is_file():
        return Campaign.load(p)
    for base in (Path.cwd() / "campaigns", cfg.root / "campaigns"):
        cand = base / f"{target}.toml"
        if cand.is_file():
            return Campaign.load(cand)
    fault = resolve(target)
    if fault is None:
        raise CLIError(
            f"no fault, alias or campaign named {target!r}",
            "run `aeon chaos list`, or pass a campaign .toml file",
            EXIT_USAGE,
        )
    slug = fault.name
    return Campaign(
        id=f"adhoc-{slug}",
        hypothesis=(
            f"With {slug} injected, the gate raises at least ALERT and no unapproved "
            "destructive action runs."
        ),
        fault=slug,
    )


def cmd_chaos_run(args: argparse.Namespace) -> int:
    from aeon.chaos import BlastRadiusExceeded, render_markdown, run_campaign, save_result

    cfg = _config(args)
    try:
        c = _find_campaign(args.target, cfg)
    except (ValueError, KeyError) as exc:
        raise CLIError(f"invalid campaign: {exc}", "see docs/guides/campaigns.md") from None
    if args.blast_radius:
        c.blast_radius = args.blast_radius
    for name in ("seed", "runs", "controls", "mode"):
        v = getattr(args, name)
        if v is not None:
            setattr(c, name, v)

    def progress(kind: str, i: int, n: int) -> None:
        if not args.json and sys.stderr.isatty():
            print(f"\r  {kind} runs {i}/{n}", end="", file=sys.stderr, flush=True)

    try:
        doc = run_campaign(c, ceiling=cfg.max_blast_radius, progress=progress)
    except BlastRadiusExceeded as exc:
        raise CLIError(
            str(exc), "lower --blast-radius or raise [aeon.chaos] max_blast_radius", EXIT_USAGE
        ) from None
    except ValueError as exc:
        raise CLIError(str(exc)) from None
    if not args.json and sys.stderr.isatty():
        print(file=sys.stderr)
    path = save_result(doc)
    doc["saved_to"] = str(path)

    def text() -> str:
        s = doc["summary"]
        seen: list[str] = next(
            (r["levels_seen"] for r in doc["fault_runs"] if r["levels_seen"]), []
        )
        lines = [
            f"[{c.blast_radius}] fault {c.fault} injected from step {c.start_step} "
            f"in {c.runs} runs ({c.controls} controls)",
            f"  escalation (first run): {' -> '.join(seen) if seen else 'none'}"
            + (" · Safe State reached" if doc["fault_runs"][0]["safe_state"] else ""),
            f"  detection {100 * s['detection_rate']:.0f}%  false positives "
            f"{100 * (s['false_positive_rate'] or 0):.0f}%  Safe State "
            f"{100 * s['safe_state_rate']:.0f}%  harmful actions executed "
            f"{s['harmful_actions_executed']}",
            f"  hypothesis {'supported' if doc['hypothesis_supported'] else 'NOT supported'}",
            f"  saved {path}",
            f"  report: aeon report {c.id}",
        ]
        if args.markdown:
            lines += ["", render_markdown(doc)]
        return "\n".join(lines)

    out(args, doc, text)
    return EXIT_OK if doc["hypothesis_supported"] or not args.strict else EXIT_FAIL


def cmd_report(args: argparse.Namespace) -> int:
    from aeon.chaos import list_results, load_result, render_markdown

    if not args.campaign:
        rows = list_results()
        out(
            args,
            rows,
            lambda: (
                "\n".join(
                    f"{r['id']:<32} {r['started_at']}  detect {100 * r['detection_rate']:.0f}%  "
                    f"{'supported' if r['hypothesis_supported'] else 'NOT supported'}"
                    for r in rows
                )
                or "no campaign results yet; run `aeon chaos run`"
            ),
        )
        return EXIT_OK
    try:
        doc = load_result(args.campaign)
    except FileNotFoundError as exc:
        raise CLIError(str(exc), "list results with `aeon report`") from None
    md = render_markdown(doc)
    if args.output:
        base = Path(args.output)
        base.parent.mkdir(parents=True, exist_ok=True)
        base.with_suffix(".md").write_text(md, "utf-8")
        base.with_suffix(".json").write_text(json.dumps(doc, indent=2, default=str), "utf-8")
    out(args, doc, md)
    return EXIT_OK


# -- audit ---------------------------------------------------------------------------------


def cmd_audit_verify(args: argparse.Namespace) -> int:
    from aeon.audit import verify

    spec = _audit_spec(args)
    target = spec.removeprefix("sqlite:")
    if not Path(target).exists():
        raise CLIError(
            f"no audit log at {target}", "run an agent under the gate first, or pass --file"
        )
    r = verify(spec, expect_head=args.expect_head)

    def text() -> str:
        if r.ok:
            lines = [f"ok: {r.records} records, chain intact", f"head {r.head}"]
        else:
            where = (
                f"line {r.first_bad_line}, seq {r.first_bad_seq}"
                if r.first_bad_line
                else "end of chain"
            )
            lines = [
                f"BROKEN at {where}: {r.reason}",
                f"{r.records} records verified before the break",
            ]
        lines += [f"warning: {w}" for w in r.warnings]
        return "\n".join(lines)

    out(args, {"file": spec, **r.to_dict()}, text)
    return EXIT_OK if r.ok else EXIT_FAIL


def cmd_audit_tail(args: argparse.Namespace) -> int:
    from aeon.audit import read

    spec = _audit_spec(args)
    recs = list(read(spec))[-args.n :]
    if args.type:
        recs = [r for r in recs if r["type"] == args.type]

    def fmt(r: dict[str, Any]) -> str:
        d = r["data"]
        if r["type"] == "decision":
            return (
                f"{r['seq']:>6} {r['ts']} {d['verdict']:<5} {d['agent']}/{d['tool']} "
                f"{'allowed' if d['allowed'] else 'DENIED'} ({d['mode']})"
                + (f" - {'; '.join(f['reason'] for f in d['findings'])}" if d["findings"] else "")
            )
        return f"{r['seq']:>6} {r['ts']} {r['type']} {json.dumps(d, default=str)}"

    out(args, recs, lambda: "\n".join(fmt(r) for r in recs) or "audit log is empty")
    return EXIT_OK


def cmd_audit_export(args: argparse.Namespace) -> int:
    import csv
    import io

    from aeon.audit import read

    recs = list(read(_audit_spec(args)))
    if args.format == "jsonl":
        body = "".join(json.dumps(r, default=str) + "\n" for r in recs)
    else:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["seq", "ts", "type", "agent", "tool", "verdict", "allowed", "mode", "hash"])
        for r in recs:
            d = r["data"]
            w.writerow(
                [
                    r["seq"],
                    r["ts"],
                    r["type"],
                    d.get("agent", ""),
                    d.get("tool", ""),
                    d.get("verdict", ""),
                    d.get("allowed", ""),
                    d.get("mode", ""),
                    r["hash"],
                ]
            )
        body = buf.getvalue()
    if args.output:
        Path(args.output).write_text(body, "utf-8")
        print(f"wrote {len(recs)} records to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(body)
    return EXIT_OK


# -- runtime / ui / docs -------------------------------------------------------------------


def _require_runtime() -> None:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        raise CLIError(
            "the runtime extra is not installed",
            'pip install "aeon-core[runtime]"  (or: uv add "aeon-core[runtime]")',
        ) from None


def cmd_runtime_start(args: argparse.Namespace) -> int:
    _require_runtime()
    from aeon.runtime.server import serve

    return serve(host=args.host, port=args.port, config=args.config, open_ui=False)


def cmd_ui(args: argparse.Namespace) -> int:
    _require_runtime()
    from aeon.runtime.server import serve

    return serve(host=args.host, port=args.port, config=args.config, open_ui=not args.no_browser)


def cmd_mcp(args: argparse.Namespace) -> int:
    from aeon.runtime.mcp import serve_stdio

    return serve_stdio(config=args.config)


def cmd_docs_mcp(args: argparse.Namespace) -> int:
    from aeon.docs_mcp import serve_docs

    return serve_docs(args.docs_dir)


# -- parser --------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aeon",
        description="Gate the actions of LLM agents and check that they fail safe.",
        epilog="Docs: https://www.richardsonlima.com.br/aeon/docs/",
    )
    p.add_argument("--config", help="path to aeon.toml (default: discover from cwd)")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    def add(
        name: str,
        fn: Callable[[argparse.Namespace], int],
        help: str,
        parent: Any = sub,
        json_flag: bool = True,
    ) -> argparse.ArgumentParser:
        sp: argparse.ArgumentParser = parent.add_parser(name, help=help, description=help)
        sp.set_defaults(func=fn)
        if json_flag:
            sp.add_argument("--json", action="store_true", help="print JSON")
        return sp

    add("doctor", cmd_doctor, "check environment, config, storage and run a gate self-test")
    sp = add("init", cmd_init, "scaffold aeon.toml and example axioms (shadow mode)")
    sp.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    sp.add_argument("--force", action="store_true", help="overwrite existing files")

    ax = sub.add_parser(
        "axioms", help="list and validate axioms", description="list and validate axioms"
    )
    axs = ax.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    sp = add("list", cmd_axioms_list, "list axioms from config or files", axs)
    sp.add_argument("files", nargs="*")
    sp = add("check", cmd_axioms_check, "import an axiom file and self-test it", axs)
    sp.add_argument("file")

    sp = add("run", cmd_run, "run a Python agent script under the gate", json_flag=False)
    sp.add_argument("script")
    sp.add_argument("--mode", choices=["shadow", "enforce"], default="shadow")
    sp.add_argument(
        "script_args",
        nargs="*",
        help="arguments for the script, after `--` (aeon run a.py -- --flag)",
    )

    ch = sub.add_parser(
        "chaos", help="fault catalog and campaigns", description="fault catalog and campaigns"
    )
    chs = ch.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    add("list", cmd_chaos_list, "list the fault catalog", chs)
    sp = add("run", cmd_chaos_run, "run a fault or a campaign file", chs)
    sp.add_argument(
        "target",
        help='fault name or alias (e.g. "degrade gateway latency"), campaign id, or campaign .toml',
    )
    sp.add_argument("--blast-radius", choices=["dev", "staging", "prod-shadow"])
    sp.add_argument("--seed", type=int)
    sp.add_argument("--runs", type=int)
    sp.add_argument("--controls", type=int)
    sp.add_argument("--mode", choices=["shadow", "enforce"])
    sp.add_argument("--markdown", action="store_true", help="also print the full report")
    sp.add_argument(
        "--strict", action="store_true", help="exit 1 if the hypothesis is not supported (for CI)"
    )

    sp = add("report", cmd_report, "render a campaign report (markdown + JSON)")
    sp.add_argument("campaign", nargs="?", help="campaign id or result .json; omit to list")
    sp.add_argument("-o", "--output", help="write <output>.md and <output>.json")

    au = sub.add_parser(
        "audit", help="read and verify the audit log", description="read and verify the audit log"
    )
    aus = au.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    sp = add("verify", cmd_audit_verify, "recompute the hash chain", aus)
    sp.add_argument("--file", help="audit log (default: from config)")
    sp.add_argument("--expect-head", help="fail unless the chain ends at this hash")
    sp = add("tail", cmd_audit_tail, "show the last records", aus)
    sp.add_argument("--file")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--type", help="only records of this type (decision, result, ...)")
    sp = add("export", cmd_audit_export, "export records as JSONL or CSV", aus, json_flag=False)
    sp.add_argument("--file")
    sp.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    sp.add_argument("-o", "--output")

    rt = sub.add_parser(
        "runtime",
        help="local HTTP + MCP service (extra: runtime)",
        description="local HTTP + MCP service (extra: runtime)",
    )
    rts = rt.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    for parent, name, fn, h in (
        (rts, "start", cmd_runtime_start, "start the HTTP runtime"),
        (sub, "serve", cmd_runtime_start, "alias of `aeon runtime start`"),
    ):
        sp = add(name, fn, h, parent, json_flag=False)
        sp.add_argument("--host", default="127.0.0.1")
        sp.add_argument("--port", type=int, default=8787)
    add("mcp", cmd_mcp, "serve the gate over MCP (stdio)", rts, json_flag=False)

    sp = add("ui", cmd_ui, "open the control plane against a local runtime", json_flag=False)
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8787)
    sp.add_argument("--no-browser", action="store_true")

    dc = sub.add_parser("docs", help="documentation tools", description="documentation tools")
    dcs = dc.add_subparsers(dest="sub", metavar="<subcommand>", required=True)
    sp = add(
        "mcp",
        cmd_docs_mcp,
        "serve the docs over MCP (stdio) for coding agents",
        dcs,
        json_flag=False,
    )
    sp.add_argument("--docs-dir", help="docs directory (default: bundled docs)")

    add("version", cmd_version, "print version information")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return int(args.func(args))
    except CLIError as exc:
        print(f"aeon: error: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"aeon: fix: {exc.hint}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return EXIT_OK
    except Exception as exc:  # last resort: still no stack trace for users
        if os.environ.get("AEON_DEBUG"):
            raise
        print(f"aeon: unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "aeon: fix: rerun with AEON_DEBUG=1 for a traceback and report it at "
            "https://github.com/richardsonlima/aeon-core/issues",
            file=sys.stderr,
        )
        return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
