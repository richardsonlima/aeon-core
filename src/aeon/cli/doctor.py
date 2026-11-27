"""Checks run by ``aeon doctor``. Each returns a dict with status ok/warn/fail/info."""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any

from aeon._version import __version__

Check = dict[str, Any]


def _c(name: str, status: str, detail: str, hint: str | None = None) -> Check:
    return {"name": name, "status": status, "detail": detail, "hint": hint}


def check_python() -> Check:
    v = sys.version_info
    if v < (3, 10):
        return _c("python", "fail", platform.python_version(), "install Python 3.10 or newer")
    return _c("python", "ok", f"{platform.python_version()} ({sys.executable})")


def check_extras() -> list[Check]:
    out = []
    for extra, mods in (
        ("runtime", ("fastapi", "uvicorn")),
        ("openai", ("openai",)),
        ("anthropic", ("anthropic",)),
        ("langgraph", ("langgraph",)),
    ):
        have = all(importlib.util.find_spec(m) is not None for m in mods)
        out.append(
            _c(
                f"extra:{extra}",
                "info",
                "installed" if have else "not installed",
                None if have else f'pip install "aeon-core[{extra}]" if you need it',
            )
        )
    return out


def gate_self_test() -> Check:
    """Exercise the decision path in memory: block, shadow, fail-closed, kill-switch, chain."""
    from aeon.audit import AuditLog, MemoryBackend, verify_records
    from aeon.axioms import Action, AxiomSpec, Gate, Level

    problems = []
    be = MemoryBackend()
    log = AuditLog(be)
    try:
        deny = AxiomSpec("deny_rm", lambda a: a.tool != "rm", Level.BLOCK)

        def broken(a: Action) -> bool:
            raise RuntimeError("self-test")

        g = Gate([deny], mode="enforce", audit=log)
        if g.decide(Action("ls")).allowed is not True:
            problems.append("a clean action was not allowed")
        if g.decide(Action("rm")).allowed is not False:
            problems.append("BLOCK did not stop the action")
        if g.safe_state("default") is None:
            problems.append("BLOCK did not enter Safe State")
        s = Gate([deny], mode="shadow")
        if not s.decide(Action("rm")).allowed:
            problems.append("shadow mode interfered with an action")
        fc = Gate([AxiomSpec("broken", broken, Level.ALERT)], mode="enforce")
        if fc.decide(Action("ls")).allowed:
            problems.append("a failing axiom did not fail closed in enforce mode")
        ks = Gate(mode="shadow")
        ks.engage_kill_switch("self-test")
        if ks.decide(Action("ls")).allowed:
            problems.append("kill-switch did not block")
        if not log.flush(5):
            problems.append("audit writer did not flush within 5 s")
        if not verify_records(be.entries()).ok:
            problems.append("audit chain did not verify")
    finally:
        log.close()
    if problems:
        return _c(
            "gate self-test",
            "fail",
            "; ".join(problems),
            "this is a bug in aeon; please report it with `aeon doctor --json`",
        )
    return _c(
        "gate self-test",
        "ok",
        "block, Safe State, shadow, fail-closed, kill-switch and audit chain all behave",
    )


def run_doctor(config_path: str | None) -> list[Check]:
    from aeon.config import ConfigError, load_axiom_file, load_config

    checks = [check_python(), _c("aeon", "ok", f"{__version__} at {Path(__file__).parents[1]}")]
    try:
        cfg = load_config(Path(config_path) if config_path else None)
    except ConfigError as exc:
        checks.append(_c("config", "fail", str(exc), "fix the file or run `aeon init`"))
        checks.append(gate_self_test())
        checks.extend(check_extras())
        return checks
    if cfg.source:
        checks.append(_c("config", "ok", cfg.source))
    else:
        checks.append(
            _c(
                "config",
                "warn",
                "no aeon.toml found; using defaults",
                "run `aeon init` to create one",
            )
        )
    checks.append(
        _c(
            "mode",
            "info" if cfg.mode == "shadow" else "ok",
            cfg.mode,
            "shadow decides and records but never blocks; switch to enforce once "
            "the audit log looks right"
            if cfg.mode == "shadow"
            else None,
        )
    )

    loaded = 0
    for f in cfg.axioms:
        p = Path(f) if Path(f).is_absolute() else cfg.root / f
        try:
            loaded += len(load_axiom_file(p))
        except ConfigError as exc:
            checks.append(_c("axioms", "fail", str(exc), "fix the axiom file or the path"))
            break
    else:
        if cfg.axioms:
            checks.append(_c("axioms", "ok", f"{loaded} axiom(s) from {len(cfg.axioms)} file(s)"))
        else:
            checks.append(
                _c(
                    "axioms",
                    "warn",
                    "no axiom files configured",
                    'add `axioms = ["aeon_axioms.py"]` to aeon.toml',
                )
            )

    if not cfg.audit_enabled:
        checks.append(
            _c(
                "audit storage",
                "warn",
                "audit is off",
                "set [aeon.audit] path to keep a verifiable record",
            )
        )
    else:
        loc = cfg.audit_location()
        target = Path(loc.removeprefix("sqlite:"))
        parent = target.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=parent, prefix=".aeon-doctor-"):
                pass
            checks.append(_c("audit storage", "ok", f"{loc} (writable)"))
        except OSError as exc:
            checks.append(
                _c(
                    "audit storage",
                    "fail",
                    f"{parent} is not writable: {exc}",
                    "fix permissions or point [aeon.audit] path elsewhere",
                )
            )
        if target.exists():
            from aeon.audit import verify

            r = verify(loc)
            if r.ok:
                checks.append(_c("audit chain", "ok", f"{r.records} records verified"))
            else:
                checks.append(
                    _c(
                        "audit chain",
                        "fail",
                        f"broken at line {r.first_bad_line}: {r.reason}",
                        "inspect with `aeon audit verify`; keep the file as evidence",
                    )
                )
    checks.append(gate_self_test())
    checks.extend(check_extras())
    if os.environ.get("AEON_TELEMETRY"):
        checks.append(_c("telemetry", "info", "Æon sends no telemetry; AEON_TELEMETRY is ignored"))
    return checks
