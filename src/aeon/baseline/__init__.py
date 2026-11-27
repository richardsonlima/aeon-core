"""Behavioural baseline, deviation score and budget.

See docs/concepts/budget.md for the math. In short, per agent:

1. The first ``Budget.baseline_n`` results calibrate a baseline (latency mean and spread,
   error rate, repeat rate, token mean and spread, tool-call distribution).
2. Each later result gets a deviation score ``d_t``: a weighted sum of one-sided,
   clipped z-scores plus a tool-distribution drift term (Jensen-Shannon divergence).
3. The accumulated deviation is a one-sided CUSUM, ``S_t = max(0, S_{t-1} + d_t - k)``.
4. ``S_t`` crossing ``alert_at`` / ``limit_at`` / ``block_at`` yields ALERT / LIMIT / BLOCK.

Separately, the absolute envelope (``p99_ms``, ``error_rate``, ``max_cost``,
``max_tokens``) is checked over a rolling window and does not need calibration.

``record`` runs on the observation path; ``finding`` runs on the decision path and only
reads a cached level.
"""

from __future__ import annotations

import math
import threading
from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from aeon.axioms._types import Action, Finding, Level


@dataclass(frozen=True)
class Budget:
    """How much deviation an agent may accumulate, plus an optional absolute envelope.

    Thresholds apply to the accumulated deviation ``S_t`` (unitless, roughly "sigmas
    above slack, summed over steps"). Envelope fields left as ``None`` are not checked.
    """

    # absolute envelope (no calibration needed)
    p99_ms: float | None = None
    error_rate: float | None = None
    max_cost: float | None = None
    max_tokens: int | None = None
    on_breach: str = "LIMIT"
    # deviation against the calibrated baseline
    baseline_n: int = 50
    window: int = 50
    min_samples: int = 20
    slack: float = 1.0
    alert_at: float = 5.0
    limit_at: float = 10.0
    block_at: float = 20.0
    z_max: float = 10.0
    repeat_lookback: int = 3
    drift_scale: float = 0.1
    weights: Mapping[str, float] = field(
        default_factory=lambda: {
            "latency": 1.0,
            "error": 1.0,
            "repeat": 1.0,
            "tokens": 1.0,
            "drift": 1.0,
        }
    )

    def __post_init__(self) -> None:
        if not 0 <= self.alert_at <= self.limit_at <= self.block_at:
            raise ValueError("budget thresholds must satisfy 0 <= alert_at <= limit_at <= block_at")
        if self.baseline_n < 2 or self.window < 1 or self.min_samples < 1:
            raise ValueError("baseline_n must be >= 2, window and min_samples >= 1")
        Level.parse(self.on_breach)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Budget:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown budget keys: {', '.join(sorted(unknown))}")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["weights"] = dict(self.weights)
        return d


# The public site documents ``ChaosBudget(p99_ms=300, error_rate=0.02)``.
ChaosBudget = Budget


@dataclass
class Baseline:
    """Calibrated reference behaviour of one agent."""

    n: int
    latency_mean: float
    latency_std: float
    error_rate: float
    repeat_rate: float
    tokens_mean: float | None
    tokens_std: float | None
    tools: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Baseline:
        return cls(**dict(d))


@dataclass(frozen=True)
class Observation:
    tool: str
    latency_ms: float
    error: bool
    repeat: bool
    tokens: int | None = None
    cost: float | None = None


def _mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, math.sqrt(var)


def js_divergence(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """Jensen-Shannon divergence normalized to [0, 1] (base-2 logarithm)."""
    keys = set(p) | set(q)
    sp = sum(p.values()) or 1.0
    sq = sum(q.values()) or 1.0
    total = 0.0
    for k in keys:
        a = p.get(k, 0.0) / sp
        b = q.get(k, 0.0) / sq
        m = (a + b) / 2
        if a > 0:
            total += 0.5 * a * math.log2(a / m)
        if b > 0:
            total += 0.5 * b * math.log2(b / m)
    return max(0.0, min(1.0, total))


def p99(xs: list[float]) -> float:
    """Nearest-rank 99th percentile."""
    s = sorted(xs)
    return s[max(0, math.ceil(0.99 * len(s)) - 1)]


class _AgentState:
    def __init__(self, budget: Budget) -> None:
        self.calib: list[Observation] = []
        self.baseline: Baseline | None = None
        self.window: deque[Observation] = deque(maxlen=budget.window)
        self.recent_keys: deque[tuple[str, str]] = deque(maxlen=max(1, budget.repeat_lookback))
        self.accumulated = 0.0
        self.last_score = 0.0
        self.last_terms: dict[str, float] = {}
        self.max_accumulated = 0.0
        self.cost_total = 0.0
        self.tokens_total = 0
        self.steps = 0
        self.level = Level.GO
        self.reason = ""


class Monitor:
    """Tracks every agent's behaviour against a baseline and a budget."""

    def __init__(
        self, budget: Budget | None = None, baselines: Mapping[str, Baseline] | None = None
    ) -> None:
        self.budget = budget or Budget()
        self._lock = threading.Lock()
        self._agents: dict[str, _AgentState] = {}
        for agent, b in (baselines or {}).items():
            self._state(agent).baseline = b

    def _state(self, agent: str) -> _AgentState:
        st = self._agents.get(agent)
        if st is None:
            st = self._agents[agent] = _AgentState(self.budget)
        return st

    # -- observation path ----------------------------------------------------------------

    def record(
        self,
        action: Action,
        *,
        latency_ms: float,
        error: bool,
        tokens: int | None = None,
        cost: float | None = None,
    ) -> float:
        """Add one result. Returns this step's deviation score ``d_t``."""
        key = (action.tool, action.args_digest())
        with self._lock:
            st = self._state(action.agent)
            obs = Observation(
                action.tool, float(latency_ms), bool(error), key in st.recent_keys, tokens, cost
            )
            st.recent_keys.append(key)
            st.window.append(obs)
            st.steps += 1
            st.cost_total += cost or 0.0
            st.tokens_total += tokens or 0
            score = 0.0
            if st.baseline is None:
                st.calib.append(obs)
                if len(st.calib) >= self.budget.baseline_n:
                    st.baseline = self._calibrate(st.calib)
                    st.calib = []
            else:
                score, st.last_terms = self._score(st.baseline, obs, st.window)
                st.accumulated = max(0.0, st.accumulated + score - self.budget.slack)
                st.max_accumulated = max(st.max_accumulated, st.accumulated)
            st.last_score = score
            st.level, st.reason = self._level(st)
            return score

    def record_usage(
        self, agent: str, *, tokens: int | None = None, cost: float | None = None
    ) -> None:
        """Account tokens or cost not tied to one tool call (for example an LLM call)."""
        with self._lock:
            st = self._state(agent)
            st.cost_total += cost or 0.0
            st.tokens_total += tokens or 0
            st.level, st.reason = self._level(st)

    def _calibrate(self, obs: list[Observation]) -> Baseline:
        lat_m, lat_s = _mean_std([o.latency_ms for o in obs])
        toks = [float(o.tokens) for o in obs if o.tokens is not None]
        tok_m, tok_s = _mean_std(toks) if len(toks) >= 2 else (None, None)
        counts = Counter(o.tool for o in obs)
        return Baseline(
            n=len(obs),
            latency_mean=lat_m,
            latency_std=lat_s,
            error_rate=sum(o.error for o in obs) / len(obs),
            repeat_rate=sum(o.repeat for o in obs) / len(obs),
            tokens_mean=tok_m,
            tokens_std=tok_s,
            tools={k: float(v) for k, v in counts.items()},
        )

    def _score(
        self, b: Baseline, obs: Observation, window: deque[Observation]
    ) -> tuple[float, dict[str, float]]:
        bud, w = self.budget, self.budget.weights
        zc = bud.z_max

        def clip(z: float) -> float:
            return max(0.0, min(zc, z))

        def binary(x: bool, p: float) -> float:
            return clip((float(x) - p) / math.sqrt(max(p * (1 - p), 0.01)))

        sigma = max(b.latency_std, 0.1 * b.latency_mean, 1.0)
        terms = {
            "latency": clip((obs.latency_ms - b.latency_mean) / sigma),
            "error": binary(obs.error, b.error_rate),
            "repeat": binary(obs.repeat, b.repeat_rate),
        }
        if obs.tokens is not None and b.tokens_mean is not None:
            ts = max(b.tokens_std or 0.0, 0.1 * b.tokens_mean, 1.0)
            terms["tokens"] = clip((obs.tokens - b.tokens_mean) / ts)
        if len(window) >= bud.min_samples:
            recent = Counter(o.tool for o in window)
            terms["drift"] = clip(js_divergence(b.tools, recent) / bud.drift_scale)
        score = sum(w.get(k, 1.0) * v for k, v in terms.items())
        return score, terms

    def _level(self, st: _AgentState) -> tuple[Level, str]:
        bud = self.budget
        level, reasons = Level.GO, []
        if st.baseline is not None:
            s = st.accumulated
            for thr, lv in (
                (bud.block_at, Level.BLOCK),
                (bud.limit_at, Level.LIMIT),
                (bud.alert_at, Level.ALERT),
            ):
                if s >= thr and thr > 0:
                    level = lv
                    reasons.append(f"accumulated deviation {s:.2f} >= {thr:g} ({lv.name})")
                    break
        breach = Level.parse(bud.on_breach)
        samples = list(st.window)
        if len(samples) >= bud.min_samples:
            if bud.p99_ms is not None:
                v = p99([o.latency_ms for o in samples])
                if v > bud.p99_ms:
                    level = max(level, breach)
                    reasons.append(f"p99 latency {v:.1f} ms > {bud.p99_ms:g} ms")
            if bud.error_rate is not None:
                er = sum(o.error for o in samples) / len(samples)
                if er > bud.error_rate:
                    level = max(level, breach)
                    reasons.append(f"error rate {er:.3f} > {bud.error_rate:g}")
        if bud.max_cost is not None and st.cost_total > bud.max_cost:
            level = max(level, breach)
            reasons.append(f"cost {st.cost_total:.4f} > {bud.max_cost:g}")
        if bud.max_tokens is not None and st.tokens_total > bud.max_tokens:
            level = max(level, breach)
            reasons.append(f"tokens {st.tokens_total} > {bud.max_tokens}")
        return level, "; ".join(reasons)

    # -- decision path -------------------------------------------------------------------

    def finding(self, agent: str) -> Finding | None:
        st = self._agents.get(agent)
        if st is None or st.level is Level.GO:
            return None
        return Finding("budget", st.level, st.reason)

    # -- control -------------------------------------------------------------------------

    def reset_accumulated(self, agent: str) -> None:
        with self._lock:
            st = self._agents.get(agent)
            if st is not None:
                st.accumulated = 0.0
                st.window.clear()
                st.cost_total = 0.0
                st.tokens_total = 0
                st.level, st.reason = self._level(st)

    def baseline(self, agent: str) -> Baseline | None:
        st = self._agents.get(agent)
        return st.baseline if st else None

    def set_baseline(self, agent: str, baseline: Baseline) -> None:
        with self._lock:
            self._state(agent).baseline = baseline

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "budget": self.budget.to_dict(),
                "agents": {
                    a: {
                        "calibrated": st.baseline is not None,
                        "calibration_progress": (
                            self.budget.baseline_n if st.baseline else len(st.calib)
                        ),
                        "steps": st.steps,
                        "deviation": round(st.last_score, 4),
                        "terms": {k: round(v, 4) for k, v in st.last_terms.items()},
                        "accumulated": round(st.accumulated, 4),
                        "max_accumulated": round(st.max_accumulated, 4),
                        "level": st.level.name,
                        "reason": st.reason,
                        "cost_total": st.cost_total,
                        "tokens_total": st.tokens_total,
                    }
                    for a, st in self._agents.items()
                },
            }


__all__ = ["Baseline", "Budget", "ChaosBudget", "Monitor", "Observation", "js_divergence", "p99"]
