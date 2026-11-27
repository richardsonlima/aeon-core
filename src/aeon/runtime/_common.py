"""Helpers shared by the HTTP runtime and the MCP server. Stdlib only."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aeon.axioms import Action, Gate
from aeon.config import Config

MAX_RUNS = 1000
MAX_STEPS = 1000

_TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$")
CAMPAIGN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class InvalidRequest(ValueError):
    """The caller asked for something malformed or not allowed."""


def action_from(
    tool: str,
    args: Mapping[str, Any] | None = None,
    agent: str = "default",
    approved: bool = False,
    context: Mapping[str, Any] | None = None,
) -> Action:
    return Action(
        tool=tool,
        args=dict(args or {}),
        agent=agent,
        approved=approved,
        context=dict(context or {}),
    )


def audit_info(gate: Gate) -> dict[str, Any] | None:
    """Health and counters of the gate's audit log, or ``None`` when there is none."""
    audit: Any = gate.audit
    if audit is None:
        return None
    info: dict[str, Any] = {"healthy": bool(getattr(audit, "healthy", True))}
    stats = getattr(audit, "stats", None)
    if stats is not None and hasattr(stats, "to_dict"):
        info["stats"] = stats.to_dict()
    pending = getattr(audit, "pending", None)
    if isinstance(pending, int):
        info["pending"] = pending
    return info


def status_doc(gate: Gate) -> dict[str, Any]:
    doc = gate.status()
    doc["audit"] = audit_info(gate)
    return doc


def readable_audit(gate: Gate) -> Any:
    """The gate's audit log if it can be read back, else ``InvalidRequest``."""
    audit: Any = gate.audit
    if audit is None or not hasattr(audit, "records") or not hasattr(audit, "verify"):
        raise InvalidRequest("audit log is not enabled or cannot be read back")
    flush = getattr(audit, "flush", None)
    if callable(flush):
        flush(1.0)
    return audit


def build_campaign(
    cfg: Config,
    *,
    target: str | None = None,
    campaign: Mapping[str, Any] | None = None,
    runs: int | None = None,
    controls: int | None = None,
    seed: int | None = None,
    blast_radius: str | None = None,
) -> Any:
    """Resolve a campaign from a fault name, a ``campaigns/<name>.toml`` file or a mapping.

    Paths are never accepted, so a remote caller cannot read arbitrary files. Sizes are
    capped. Raises ``InvalidRequest`` on any problem, including a blast radius above the
    configured ceiling.
    """
    from aeon.chaos import BlastRadiusExceeded, Campaign, check_radius, make, resolve

    if (target is None) == (campaign is None):
        raise InvalidRequest("give exactly one of 'target' or 'campaign'")
    try:
        if campaign is not None:
            c = Campaign.from_mapping(campaign)
        else:
            assert target is not None
            if not _TARGET_RE.match(target):
                raise InvalidRequest("target must be a fault name or a campaign name")
            c = _from_target(cfg, target, Campaign, resolve)
        if blast_radius is not None:
            c.blast_radius = blast_radius
        for name, value in (("seed", seed), ("runs", runs), ("controls", controls)):
            if value is not None:
                setattr(c, name, value)
        c.__post_init__()  # revalidate after overrides
        if not CAMPAIGN_ID_RE.match(c.id):
            raise InvalidRequest("campaign id must match [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
        if c.runs > MAX_RUNS or c.controls > MAX_RUNS or c.steps > MAX_STEPS:
            raise InvalidRequest(
                f"runs and controls are capped at {MAX_RUNS}, steps at {MAX_STEPS}"
            )
        fault = make(c.fault, probability=c.probability, **c.fault_params)
        check_radius(fault, c.blast_radius, ceiling=cfg.max_blast_radius, gate_mode=c.mode)
    except InvalidRequest:
        raise
    except BlastRadiusExceeded as exc:
        raise InvalidRequest(str(exc)) from None
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidRequest(f"invalid campaign: {exc}") from None
    return c


def _from_target(cfg: Config, target: str, campaign_cls: Any, resolve: Any) -> Any:
    for base in (Path.cwd() / "campaigns", cfg.root / "campaigns"):
        cand = base / f"{target}.toml"
        if cand.is_file():
            return campaign_cls.load(cand)
    fault = resolve(target)
    if fault is None:
        raise InvalidRequest(f"no fault, alias or campaign named {target!r}; see the fault catalog")
    return campaign_cls(
        id=f"adhoc-{fault.name}",
        hypothesis=(
            f"With {fault.name} injected, the gate raises at least ALERT and no unapproved "
            "destructive action runs."
        ),
        fault=fault.name,
    )


def campaign_summary(doc: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "campaign": doc["campaign"]["id"],
        "hypothesis_supported": doc["hypothesis_supported"],
        "summary": doc["summary"],
        "checks": doc["checks"],
        "unfavourable": doc["unfavourable"],
        "duration_s": doc["duration_s"],
    }
