"""The HTTP control plane: a FastAPI app around one gate.

The runtime decides, records and reports. It never executes a tool: a caller asks
``POST /v1/actions/evaluate`` and acts on the decision itself.
"""

from __future__ import annotations

import asyncio
import csv
import dataclasses
import hmac
import io
import json
import logging
import os
import secrets
import threading
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aeon._util import csv_safe, new_id, utc_now_iso
from aeon._version import __version__
from aeon.axioms import Decision, Gate, Level, Mode
from aeon.axioms._gate import AxiomSpec
from aeon.config import Config, load_config
from aeon.runtime._common import (
    CAMPAIGN_ID_RE,
    InvalidRequest,
    action_from,
    build_campaign,
    readable_audit,
    status_doc,
)

MAX_BODY_BYTES = 1024 * 1024
MAX_DECISIONS = 5000
CLIENT_QUEUE_SIZE = 256
HEARTBEAT_S = 15.0
TOKEN_FILE = ".aeon/runtime.token"  # noqa: S105
logger = logging.getLogger(__name__)
STREAM_PATH = "/v1/decisions/stream"
MAX_STREAM_CLIENTS = 16  # concurrent SSE clients
MAX_RECORD_ARGS = 16 * 1024  # serialized args kept per buffered decision, in characters
SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (
        b"content-security-policy",
        b"default-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
    ),
)


# -- token ------------------------------------------------------------------------------


def resolve_token(token: str | None = None, root: Path | None = None) -> tuple[str, str]:
    """Pick the bearer token. Returns ``(token, where)`` without ever printing the token."""
    if token:
        return token, "argument"
    env = os.environ.get("AEON_RUNTIME_TOKEN")
    if env:
        return env, "env AEON_RUNTIME_TOKEN"
    path = (root or Path.cwd()) / TOKEN_FILE
    if path.is_symlink():
        raise PermissionError(f"{path} is a symlink; refusing to read a token through it")
    try:
        existing = path.read_text("utf-8").strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        _check_token_file(path)
        return existing, str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(fresh + "\n")
    os.chmod(path, 0o600)
    return fresh, str(path)


def _check_token_file(path: Path) -> None:
    """Tighten a token file readable by group or others back to 0600."""
    if os.name != "posix":
        return
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        logger.warning("%s had mode %o; resetting it to 600", path, mode)
        os.chmod(path, 0o600)


class SecurityHeadersMiddleware:
    """Add nosniff, frame denial, no-referrer and a strict CSP to every HTTP response."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """ASGI entry point: decorate ``http.response.start`` messages."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *SECURITY_HEADERS]
            await send(message)

        await self.app(scope, receive, send_with_headers)


# -- body size cap ----------------------------------------------------------------------


class BodyLimitMiddleware:
    """Reject request bodies above ``limit`` bytes with 413, whatever Content-Length says."""

    def __init__(self, app: ASGIApp, limit: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.limit = limit

    def _declared_too_big(self, scope: Scope) -> bool:
        """Whether Content-Length is above the limit or not a number."""
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is None:
            return False
        try:
            return int(declared) > self.limit
        except ValueError:
            return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass non-HTTP scopes through; buffer HTTP bodies and answer 413 above the limit."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        too_big = self._declared_too_big(scope)
        chunks: list[bytes] = []
        size = 0
        while not too_big:
            msg = await receive()
            if msg["type"] != "http.request":
                await self.app(scope, receive, send)  # disconnect before any body
                return
            body = msg.get("body", b"")
            size += len(body)
            if size > self.limit:
                too_big = True
                break
            chunks.append(body)
            if not msg.get("more_body", False):
                break
        if too_big:
            resp = JSONResponse({"detail": f"request body above {self.limit} bytes"}, 413)
            await resp(scope, receive, send)
            return
        replay = b"".join(chunks)
        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": replay, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)


# -- decisions: ring buffer and SSE fan-out ---------------------------------------------


class DecisionHub:
    """Keeps the last decisions and fans new ones out to SSE clients.

    ``publish`` is called from whatever thread decided, so client queues are fed with
    ``call_soon_threadsafe``. A full client queue drops its oldest item.
    """

    def __init__(self, maxlen: int = MAX_DECISIONS, queue_size: int = CLIENT_QUEUE_SIZE) -> None:
        self._ring: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._clients: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]] = []
        self._queue_size = queue_size

    def publish(self, record: dict[str, Any]) -> None:
        """Record a decision and queue it to every SSE client, whichever thread calls."""
        with self._lock:
            self._ring.append(record)
            clients = list(self._clients)
        for loop, q in clients:
            try:
                loop.call_soon_threadsafe(self._put, q, record)
            except RuntimeError:  # that client's loop is gone
                self._drop(q)

    @staticmethod
    def _put(q: asyncio.Queue[dict[str, Any]], record: dict[str, Any]) -> None:
        if q.full():
            q.get_nowait()
        q.put_nowait(record)

    def _drop(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._clients = [c for c in self._clients if c[1] is not q]

    def attach(self) -> asyncio.Queue[dict[str, Any]]:
        """Register the calling event loop as a client; return the queue its events arrive on."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        with self._lock:
            self._clients.append((asyncio.get_running_loop(), q))
        return q

    def client_count(self) -> int:
        """Number of attached SSE clients."""
        with self._lock:
            return len(self._clients)

    def detach(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Unregister the client that owns ``q``."""
        self._drop(q)

    @property
    def clients(self) -> int:
        """Number of connected SSE clients."""
        return len(self._clients)

    def recent(
        self, *, agent: str | None, axiom: str | None, level: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` buffered decisions, newest first, optionally filtered."""
        with self._lock:
            items = list(self._ring)
        out: list[dict[str, Any]] = []
        for rec in reversed(items):  # newest first
            if agent is not None and rec.get("agent") != agent:
                continue
            if level is not None and rec.get("verdict") != level:
                continue
            if axiom is not None and not any(f.get("axiom") == axiom for f in rec["findings"]):
                continue
            out.append(rec)
            if len(out) >= limit:
                break
        return out

    def __len__(self) -> int:
        return len(self._ring)


async def sse_events(
    hub: DecisionHub,
    disconnected: Callable[[], Awaitable[bool]],
    heartbeat_s: float = HEARTBEAT_S,
) -> AsyncIterator[str]:
    """Yield server-sent events: ``data: <json>`` per decision, a comment as heartbeat."""
    q = hub.attach()
    try:
        yield ": connected\n\n"
        while True:
            try:
                rec = await asyncio.wait_for(q.get(), timeout=heartbeat_s)
            except asyncio.TimeoutError:
                if await disconnected():
                    return
                yield ": heartbeat\n\n"
                continue
            yield f"data: {json.dumps(rec, default=str)}\n\n"
    finally:
        hub.detach(q)


# -- request models ---------------------------------------------------------------------


class EvaluateIn(BaseModel):
    """Body of ``POST /v1/actions/evaluate``: the action to decide on."""

    tool: str = Field(min_length=1, max_length=256)
    args: dict[str, Any] = Field(default_factory=dict)
    agent: str = Field(default="default", min_length=1, max_length=256)
    approved: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class ResultIn(BaseModel):
    """Body of ``POST /v1/actions/result``: how an evaluated action went (``latency_ms`` in ms)."""

    action_id: str | None = Field(default=None, max_length=128)
    tool: str = Field(min_length=1, max_length=256)
    agent: str = Field(default="default", min_length=1, max_length=256)
    latency_ms: float = Field(ge=0)
    ok: bool = True
    tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)


class PolicyIn(BaseModel):
    """Body of ``PUT /v1/policies/{name}``: a new level and/or whether the axiom is enabled."""

    level: str | None = None
    enabled: bool | None = None


class ModeIn(BaseModel):
    """Request body for switching the gate mode: ``shadow`` or ``enforce``."""

    mode: str


class KillSwitchIn(BaseModel):
    """Request body for the kill switch: engage or release it, with an optional reason."""

    engaged: bool
    reason: str | None = Field(default=None, max_length=500)


class CampaignIn(BaseModel):
    """Request body for starting a campaign: a target name or an inline campaign, plus overrides."""

    target: str | None = None
    campaign: dict[str, Any] | None = None
    runs: int | None = Field(default=None, ge=1)
    controls: int | None = Field(default=None, ge=0)
    seed: int | None = None
    blast_radius: str | None = None


class AuditVerifyIn(BaseModel):
    """Request body for audit verification: the head hash the chain is expected to end at."""

    expect_head: str | None = None


class ReportedFailure(Exception):
    """Stands in for the error a remote caller reported through ``/v1/actions/result``."""


# -- static assets ----------------------------------------------------------------------


def controlplane_dir() -> Path | None:
    """The built UI: ``aeon/controlplane`` in a wheel, repo ``controlplane/`` when editable."""
    here = Path(__file__).resolve()
    for cand in (here.parents[1] / "controlplane", here.parents[3] / "controlplane"):
        if cand.is_dir():
            return cand
    return None


def claims_candidates(cfg: Config) -> list[Path]:
    """Return the places a ``docs/claims.json`` may live, in lookup order."""
    here = Path(__file__).resolve()
    return [
        Path.cwd() / "docs" / "claims.json",
        cfg.root / "docs" / "claims.json",
        here.parents[3] / "docs" / "claims.json",
        here.parents[1] / "_docs" / "claims.json",
    ]


# -- app --------------------------------------------------------------------------------


def create_app(  # noqa: C901 - route factory: each nested route function counts toward the total
    gate: Gate | None = None,
    *,
    config: Config | None = None,
    token: str | None = None,
) -> FastAPI:
    """Build the control-plane app. ``gate`` defaults to one built from ``config``."""
    cfg = config or load_config()
    owns_gate = gate is None
    if gate is None:
        from aeon.config import build_gate

        gate = build_gate(cfg)
    g: Gate = gate
    secret, _where = resolve_token(token, cfg.root)
    secret_b = secret.encode("utf-8")

    hub = DecisionHub()
    g.subscribe(lambda d: _publish(hub, g, d))
    disabled: dict[str, AxiomSpec] = {}
    policy_lock = threading.Lock()
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aeon-campaign")
    jobs: dict[str, dict[str, Any]] = {}
    jobs_lock = threading.Lock()
    started = time.monotonic()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        pool.shutdown(wait=False, cancel_futures=True)
        audit: Any = g.audit
        if owns_gate and audit is not None and hasattr(audit, "close"):
            audit.close()

    app = FastAPI(
        title="Æon runtime",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.state.gate = g
    app.state.hub = hub
    app.state.token = secret

    # -- auth ----------------------------------------------------------------------

    def _authorized(candidate: str | None) -> bool:
        if not candidate:
            return False
        return hmac.compare_digest(candidate.encode("utf-8"), secret_b)

    def require_auth(request: Request) -> None:
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        candidate = value.strip() if scheme.lower() == "bearer" else None
        if candidate is None and request.url.path == STREAM_PATH:
            candidate = request.query_params.get("token")
        if not _authorized(candidate):
            raise HTTPException(
                status_code=401,
                detail="missing or invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def bad(exc: Exception, status: int = 422) -> HTTPException:
        return HTTPException(status_code=status, detail=str(exc))

    # -- open routes ---------------------------------------------------------------

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict[str, Any]:
        return {"version": __version__}

    ui_dir = controlplane_dir()

    @app.get("/", include_in_schema=False)
    def root() -> Response:
        if ui_dir is not None:
            return RedirectResponse("/ui/")
        return JSONResponse({"name": "aeon runtime", "version": __version__, "ui": False})

    # -- /v1 ------------------------------------------------------------------------

    api = APIRouter(prefix="/v1", dependencies=[Depends(require_auth)])

    @api.post("/actions/evaluate")
    def evaluate(body: EvaluateIn) -> dict[str, Any]:
        action = action_from(body.tool, body.args, body.agent, body.approved, body.context)
        return g.decide(action).to_record(include_args=g.include_args)

    @api.post("/actions/result")
    def result(body: ResultIn) -> dict[str, Any]:
        action = dataclasses.replace(
            action_from(body.tool, agent=body.agent), id=body.action_id or new_id()
        )
        g.observe(
            action,
            latency_ms=body.latency_ms,
            error=None if body.ok else ReportedFailure("reported by caller"),
            tokens=body.tokens,
            cost=body.cost,
        )
        return {"recorded": True, "action_id": action.id}

    @api.get("/status")
    def status() -> dict[str, Any]:
        doc = status_doc(g)
        doc["version"] = __version__
        doc["uptime_s"] = round(time.monotonic() - started, 1)
        doc["decisions_buffered"] = len(hub)
        doc["stream_clients"] = hub.clients
        return doc

    # policies

    def _policy_row(spec: AxiomSpec, enabled: bool) -> dict[str, Any]:
        return {
            "name": spec.name,
            "level": spec.level.name,
            "tools": sorted(spec.tools) if spec.tools is not None else None,
            "description": spec.description,
            "enabled": enabled,
        }

    @api.get("/policies")
    def policies() -> dict[str, Any]:
        with policy_lock:
            rows = [_policy_row(s, True) for s in g.axioms.snapshot()]
            rows += [_policy_row(s, False) for s in disabled.values()]
        return {"policies": rows}

    @api.put("/policies/{name}")
    def put_policy(name: str, body: PolicyIn) -> dict[str, Any]:
        new_level: Level | None = None
        if body.level is not None:
            try:
                new_level = Level.parse(body.level)
            except ValueError as exc:
                raise bad(exc) from None
            if new_level is Level.GO:
                raise bad(ValueError("level must be ALERT, LIMIT or BLOCK"))
        with policy_lock:
            live = {s.name: s for s in g.axioms.snapshot()}
            spec = live.get(name) or disabled.get(name)
            if spec is None:
                raise HTTPException(404, f"no policy named {name!r}")
            if new_level is not None:
                spec = dataclasses.replace(spec, level=new_level)
            enabled = name in live if body.enabled is None else body.enabled
            if enabled:
                disabled.pop(name, None)
                g.axioms.add(spec)
            else:
                g.axioms.remove(name)
                disabled[name] = spec
            row = _policy_row(spec, enabled)
        return row

    # mode, kill switch, safe state

    @api.post("/mode")
    def set_mode(body: ModeIn) -> dict[str, Any]:
        try:
            mode = Mode.parse(body.mode)
        except ValueError as exc:
            raise bad(exc) from None
        g.set_mode(mode)
        return {"mode": g.mode.value}

    @api.post("/kill-switch")
    def kill_switch(body: KillSwitchIn) -> dict[str, Any]:
        if body.engaged:
            g.engage_kill_switch(body.reason or "kill-switch engaged by operator")
        else:
            g.release_kill_switch()
        return g.kill_switch.to_dict()

    @api.post("/safe-state/{agent}/reset")
    def reset_safe_state(agent: str) -> dict[str, Any]:
        return {"agent": agent, "released": g.reset(agent)}

    # decisions

    @api.get("/decisions")
    def decisions(
        agent: str | None = None,
        axiom: str | None = None,
        level: str | None = None,
        limit: int = Query(100, ge=1, le=MAX_DECISIONS),
    ) -> dict[str, Any]:
        verdict: str | None = None
        if level is not None:
            try:
                verdict = Level.parse(level).name
            except ValueError as exc:
                raise bad(exc) from None
        items = hub.recent(agent=agent, axiom=axiom, level=verdict, limit=limit)
        return {"decisions": items, "count": len(items), "buffered": len(hub)}

    @api.get("/decisions/stream")
    async def decisions_stream(request: Request) -> StreamingResponse:
        if hub.client_count() >= MAX_STREAM_CLIENTS:
            raise HTTPException(429, f"at most {MAX_STREAM_CLIENTS} stream clients")
        return StreamingResponse(
            sse_events(hub, request.is_disconnected),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    # campaigns

    def _run_job(c: Any) -> None:
        from aeon.chaos import run_campaign, save_result

        try:
            doc = run_campaign(c, ceiling=cfg.max_blast_radius)
            save_result(doc)
            update: dict[str, Any] = {"status": "done"}
        except Exception as exc:
            update = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        with jobs_lock:
            jobs[c.id].update(update, finished_at=utc_now_iso())

    @api.post("/campaigns", status_code=202)
    def start_campaign(body: CampaignIn) -> dict[str, Any]:
        try:
            c = build_campaign(
                cfg,
                target=body.target,
                campaign=body.campaign,
                runs=body.runs,
                controls=body.controls,
                seed=body.seed,
                blast_radius=body.blast_radius,
            )
        except InvalidRequest as exc:
            raise bad(exc) from None
        with jobs_lock:
            if any(j["status"] in {"queued", "running"} for j in jobs.values()):
                raise HTTPException(409, "a campaign is already running; poll it first")
            jobs[c.id] = {
                "id": c.id,
                "status": "running",
                "created_at": utc_now_iso(),
                "finished_at": None,
                "error": None,
            }
        pool.submit(_run_job, c)
        return {"id": c.id, "status": "running", "poll": f"/v1/campaigns/{c.id}"}

    @api.get("/campaigns")
    def list_campaigns() -> dict[str, Any]:
        from aeon.chaos import list_results

        with jobs_lock:
            active = [dict(j) for j in jobs.values() if j["status"] == "running"]
        return {"campaigns": list_results(), "running": active}

    @api.get("/campaigns/{campaign_id}")
    def get_campaign(campaign_id: str) -> Response:
        from aeon.chaos import load_result

        if not CAMPAIGN_ID_RE.match(campaign_id):
            raise HTTPException(422, "invalid campaign id")
        with jobs_lock:
            job = dict(jobs[campaign_id]) if campaign_id in jobs else None
        if job is not None and job["status"] == "running":
            return JSONResponse(job, status_code=202)
        if job is not None and job["status"] == "error":
            return JSONResponse(job)
        try:
            return JSONResponse(load_result(campaign_id))
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from None

    # audit

    def _audit() -> Any:
        try:
            return readable_audit(g)
        except InvalidRequest as exc:
            raise HTTPException(409, str(exc)) from None

    @api.get("/audit")
    def audit_tail(
        limit: int = Query(100, ge=1, le=5000), kind: str | None = Query(None, alias="type")
    ) -> dict[str, Any]:
        audit = _audit()
        tail: deque[dict[str, Any]] = deque(maxlen=limit)
        for rec in audit.records():
            if kind is None or rec.get("type") == kind:
                tail.append(rec)
        return {"records": list(tail), "count": len(tail)}

    @api.post("/audit/verify")
    def audit_verify(body: AuditVerifyIn | None = None) -> dict[str, Any]:
        audit = _audit()
        report = audit.verify(body.expect_head if body else None)
        return dict(report.to_dict())

    @api.get("/audit/export")
    def audit_export(
        fmt: str = Query("jsonl", alias="format", pattern="^(jsonl|csv)$"),
    ) -> StreamingResponse:
        audit = _audit()
        if fmt == "jsonl":
            return StreamingResponse(
                (json.dumps(r, default=str) + "\n" for r in audit.records()),
                media_type="application/x-ndjson",
                headers={"Content-Disposition": 'attachment; filename="aeon-audit.jsonl"'},
            )
        return StreamingResponse(
            _csv_rows(audit.records()),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="aeon-audit.csv"'},
        )

    # claims

    @api.get("/claims")
    def claims() -> Response:
        for path in claims_candidates(cfg):
            if path.is_file():
                try:
                    return JSONResponse(json.loads(path.read_text("utf-8")))
                except (OSError, ValueError) as exc:
                    raise HTTPException(500, f"cannot read {path.name}: {exc}") from None
        raise HTTPException(
            404,
            "docs/claims.json not found; generate it from docs/claims.yaml "
            "(the runtime reads JSON only)",
        )

    app.include_router(api)

    if ui_dir is not None:
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
    return app


def _publish(hub: DecisionHub, gate: Gate, decision: Decision) -> None:
    record = decision.to_record(include_args=gate.include_args)
    if "args" in record:  # bound memory: the ring buffer and SSE queues keep records
        size = len(json.dumps(record["args"], default=str))
        if size > MAX_RECORD_ARGS:
            record["args"] = {"_truncated": True, "chars": size}
    hub.publish(record)


def _csv_rows(records: Iterator[dict[str, Any]]) -> Iterator[str]:
    def line(row: list[Any]) -> str:
        buf = io.StringIO()
        csv.writer(buf).writerow([csv_safe(v) for v in row])
        return buf.getvalue()

    yield line(["seq", "ts", "type", "agent", "tool", "verdict", "allowed", "mode", "hash"])
    for r in records:
        d = r.get("data", {})
        yield line(
            [
                r.get("seq"),
                r.get("ts"),
                r.get("type"),
                d.get("agent", ""),
                d.get("tool", ""),
                d.get("verdict", ""),
                d.get("allowed", ""),
                d.get("mode", ""),
                r.get("hash"),
            ]
        )
