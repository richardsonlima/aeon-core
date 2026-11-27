"""Configuration from ``aeon.toml`` or ``[tool.aeon]`` in ``pyproject.toml``.

``AEON_*`` environment variables take precedence. New installs default to shadow mode.
"""

from __future__ import annotations

import atexit
import importlib.util
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 only
    import tomli as tomllib

from aeon.axioms._gate import AxiomRegistry, AxiomSpec, Gate, capture
from aeon.axioms._types import Mode

DEFAULT_AUDIT = ".aeon/audit.jsonl"
CONFIG_NAMES = ("aeon.toml", ".aeon.toml")


@dataclass
class Config:
    """Resolved Aeon settings. ``root`` is the directory relative paths resolve against."""

    mode: str = "shadow"
    audit: str = DEFAULT_AUDIT
    fsync: bool = False
    include_args: bool = False
    axioms: list[str] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    environment: str = "dev"
    max_blast_radius: str = "staging"
    runtime: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    root: Path = field(default_factory=Path.cwd)

    @property
    def audit_enabled(self) -> bool:
        """Whether auditing is on: ``audit`` is not empty, ``off``, ``none``, ``false`` or ``0``."""
        return self.audit.strip().lower() not in {"", "off", "none", "false", "0"}

    def audit_location(self) -> str:
        """The audit spec with relative paths resolved against the config's directory."""
        a = self.audit
        if a == "memory" or not self.audit_enabled:
            return a
        prefix = ""
        if a.startswith("sqlite:"):
            prefix, a = "sqlite:", a[len("sqlite:") :]
        p = Path(a)
        return prefix + str(p if p.is_absolute() else self.root / p)

    def to_dict(self) -> dict[str, Any]:
        """Return the settings as a plain dict, with ``root`` as a string."""
        return {
            "mode": self.mode,
            "audit": self.audit,
            "fsync": self.fsync,
            "include_args": self.include_args,
            "axioms": list(self.axioms),
            "budget": dict(self.budget),
            "environment": self.environment,
            "max_blast_radius": self.max_blast_radius,
            "runtime": dict(self.runtime),
            "source": self.source,
            "root": str(self.root),
        }


class ConfigError(ValueError):
    """The configuration file or an ``AEON_*`` variable is invalid."""

    pass


def find_config(start: Path | None = None) -> Path | None:
    """Locate the config file, or return ``None`` if there is none.

    Uses ``AEON_CONFIG`` if set. Otherwise walks up from ``start`` (default: the working
    directory) to the repository root, looking for ``aeon.toml``, ``.aeon.toml`` or a
    ``pyproject.toml`` with a ``[tool.aeon]`` table.
    """
    explicit = os.environ.get("AEON_CONFIG")
    if explicit:
        return Path(explicit)
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        for name in CONFIG_NAMES:
            if (d / name).is_file():
                return d / name
        pp = d / "pyproject.toml"
        if pp.is_file():
            try:
                if "aeon" in tomllib.loads(pp.read_text("utf-8")).get("tool", {}):
                    return pp
            except (tomllib.TOMLDecodeError, OSError):
                pass
        if (d / ".git").exists():
            break
    return None


def load_config(path: Path | None = None) -> Config:
    """Load config from ``path`` (or discover it), then apply ``AEON_*`` overrides."""
    cfg = Config()
    src = path or find_config()
    if src is not None:
        try:
            raw = tomllib.loads(Path(src).read_text("utf-8"))
        except FileNotFoundError:
            raise ConfigError(f"config file not found: {src}") from None
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"{src}: invalid TOML: {exc}") from None
        section = (
            raw.get("tool", {}).get("aeon")
            if Path(src).name == "pyproject.toml"
            else raw.get("aeon", raw)
        )
        _apply(cfg, section or {}, str(src))
        cfg.source = str(src)
        cfg.root = Path(src).resolve().parent
    env = os.environ
    if "AEON_MODE" in env:
        cfg.mode = env["AEON_MODE"]
    if "AEON_AUDIT" in env:
        cfg.audit = env["AEON_AUDIT"]
    if "AEON_ENVIRONMENT" in env:
        cfg.environment = env["AEON_ENVIRONMENT"]
    if "AEON_MAX_BLAST_RADIUS" in env:
        cfg.max_blast_radius = env["AEON_MAX_BLAST_RADIUS"]
    if "AEON_AXIOMS" in env:
        cfg.axioms = [p for p in env["AEON_AXIOMS"].split(os.pathsep) if p]
    try:
        Mode.parse(cfg.mode)  # validate early
    except ValueError as exc:
        raise ConfigError(f"{cfg.source or 'AEON_MODE'}: {exc}") from None
    return cfg


def _apply(cfg: Config, section: Mapping[str, Any], src: str) -> None:
    known = {"mode", "include_args", "axioms", "audit", "budget", "chaos", "runtime"}
    unknown = set(section) - known
    if unknown:
        raise ConfigError(f"{src}: unknown keys in [aeon]: {', '.join(sorted(unknown))}")
    if "mode" in section:
        cfg.mode = str(section["mode"])
    if "include_args" in section:
        cfg.include_args = bool(section["include_args"])
    if "axioms" in section:
        ax = section["axioms"]
        cfg.axioms = [ax] if isinstance(ax, str) else [str(a) for a in ax]
    audit = section.get("audit", {})
    if isinstance(audit, str):
        cfg.audit = audit
    elif isinstance(audit, Mapping):
        cfg.audit = str(audit.get("path", cfg.audit))
        cfg.fsync = bool(audit.get("fsync", cfg.fsync))
    if isinstance(section.get("budget"), Mapping):
        cfg.budget = dict(section["budget"])
    chaos = section.get("chaos", {})
    if isinstance(chaos, Mapping):
        cfg.environment = str(chaos.get("environment", cfg.environment))
        cfg.max_blast_radius = str(chaos.get("max_blast_radius", cfg.max_blast_radius))
    if isinstance(section.get("runtime"), Mapping):
        cfg.runtime = dict(section["runtime"])


def load_axiom_file(path: str | os.PathLike[str]) -> list[AxiomSpec]:
    """Import a Python file and return the axioms it declares, without registering them."""
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"axiom file not found: {p}")
    with capture() as reg:
        mod_name = f"_aeon_axioms_{abs(hash(str(p.resolve())))}"
        spec = importlib.util.spec_from_file_location(mod_name, p)
        if spec is None or spec.loader is None:
            raise ConfigError(f"cannot import {p}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise ConfigError(f"{p}: error while importing axioms: {exc!r}") from exc
        # factory specs (aeon.axioms.builtin) assigned at module level count too
        for value in vars(module).values():
            if isinstance(value, AxiomSpec):
                reg.add(value)
    return list(reg.snapshot())


def build_gate(cfg: Config, *, axioms: AxiomRegistry | None = None) -> Gate:
    """Build a Gate from config: mode, audit log, budget monitor and axiom files."""
    from aeon.audit import AuditLog
    from aeon.baseline import Budget, Monitor

    registry = axioms if axioms is not None else AxiomRegistry()
    for f in cfg.axioms:
        p = Path(f)
        for spec in load_axiom_file(p if p.is_absolute() else cfg.root / p):
            registry.add(spec)
    audit = None
    if cfg.audit_enabled:
        audit = AuditLog(cfg.audit_location(), fsync=cfg.fsync)
        atexit.register(audit.close)
    monitor = Monitor(Budget.from_mapping(cfg.budget)) if cfg.budget else Monitor()
    return Gate(
        registry, mode=cfg.mode, audit=audit, monitor=monitor, include_args=cfg.include_args
    )
