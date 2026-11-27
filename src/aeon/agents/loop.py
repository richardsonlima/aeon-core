"""The agent: a model, gated tools, instructions, and the loop between them.

:class:`Agent` sends the conversation to the model, runs each tool call through a
:class:`~aeon.adapters.ToolBox` (so through the gate), returns the results, and repeats
until the model answers without a tool call. Around that loop it adds what an agent
application needs: sessions and user memory in SQLite, structured output, step events,
and human approval for tools behind a ``require_approval`` rule.

Nothing here imports a provider SDK. The loop stops before the next model call when the
operator kill-switch is engaged or the agent is held in Safe State.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from aeon.adapters._common import as_text, blocked_message, get, parse_arguments, total_tokens
from aeon.adapters.anthropic import tool_specs as anthropic_specs
from aeon.adapters.openai import tool_specs as openai_specs
from aeon.adapters.plain import ToolBox
from aeon.agents.models import Model, resolve_model
from aeon.agents.schema import OutputSchema
from aeon.agents.storage import SqliteDb
from aeon.axioms import ActionBlocked, ActionLimited, Gate, default_gate

__all__ = ["Agent", "AgentRun", "Event", "RunEvent", "RunOutput", "ToolCall"]

Status = Literal["completed", "paused", "stopped"]
StopReason = Literal["done", "max_steps", "kill_switch", "safe_state", "paused", "bad_output"]
Approval = Literal["pause", "deny"] | Callable[["ToolCall"], bool]


class RunEvent(str, Enum):
    """The steps of a run, in the order they happen."""

    run_started = "RunStarted"
    model_request_started = "ModelRequestStarted"
    model_request_completed = "ModelRequestCompleted"
    tool_call_started = "ToolCallStarted"
    tool_call_completed = "ToolCallCompleted"
    tool_call_blocked = "ToolCallBlocked"
    tool_call_approval_required = "ToolCallApprovalRequired"
    run_paused = "RunPaused"
    run_completed = "RunCompleted"
    run_stopped = "RunStopped"


@dataclass
class ToolCall:
    """One tool call the model asked for, and what happened to it.

    Attributes:
        name: Tool name as the model sent it.
        args: Decoded arguments (empty when they could not be decoded).
        result: The text returned to the model (empty while approval is pending).
        is_error: The call failed, was blocked, denied, or had bad arguments.
        blocked: The gate (or the human) denied the call.
        approval_required: A LIMIT rule asked for human approval.
        approved: The human's answer, once given.
        call_id: The provider's id for the call.
    """

    name: str
    args: dict[str, Any]
    result: str = ""
    is_error: bool = False
    blocked: bool = False
    approval_required: bool = False
    approved: bool | None = None
    call_id: str | None = None


@dataclass
class RunOutput:
    """The outcome of one run.

    Attributes:
        content: The answer: text, or the parsed object when ``output_schema`` is set.
        text: The model's final text, unparsed.
        status: ``completed``, ``paused`` (waiting for approval) or ``stopped``.
        stop_reason: Why the loop ended.
        pending: Tool calls waiting for approval when the run is paused.
    """

    run_id: str
    agent: str
    model: str
    session_id: str | None = None
    user_id: str | None = None
    content: Any = None
    text: str | None = None
    status: Status = "stopped"
    stop_reason: StopReason = "max_steps"
    steps: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    duration_s: float = 0.0
    messages: list[Any] = field(default_factory=list)
    pending: list[ToolCall] = field(default_factory=list)
    input: str = ""
    system: str | None = field(default=None, repr=False)
    batch: list[ToolCall] = field(default_factory=list, repr=False)
    schema_retries: int = field(default=0, repr=False)

    @property
    def blocked(self) -> list[ToolCall]:
        """The calls the gate or the human denied."""
        return [c for c in self.tool_calls if c.blocked]


AgentRun = RunOutput  # earlier name


@dataclass(frozen=True)
class Event:
    """One step of a run. ``run`` is set on the terminal and paused events."""

    event: RunEvent
    run_id: str
    data: Mapping[str, Any] = field(default_factory=dict)
    run: RunOutput | None = None


class Agent:
    """A model with tools behind the gate.

    Args:
        model: ``"provider:model"`` (``openrouter``, ``openai``, ``anthropic``, ``groq``,
            ``ollama``), a model id together with ``client=``, or a :class:`Model`.
        tools: Plain functions (their signature and docstring become the tool spec), or
            a :class:`~aeon.adapters.ToolBox`.
        name: The agent's name in the gate, the audit log and the session store.
        role: One line on what the agent does, used when it is a team member.
        instructions: System instructions, a string or a list of strings.
        gate: The gate for the tools. Defaults to the process default gate.
        client: An SDK or HTTP client, instead of building one from ``model``.
        db: A :class:`SqliteDb` for sessions and memory.
        session_id: Default session for :meth:`run`.
        user_id: Default user for :meth:`run`.
        add_history_to_context: Prepend earlier turns of the session.
        num_history_runs: How many earlier turns.
        enable_agentic_memory: Give the model an ``update_user_memory`` tool (gated like
            any tool) and put the saved facts in context. Needs ``db`` and a user id.
        add_datetime_to_context: Put the current UTC time in the instructions.
        output_schema: A dataclass, Pydantic model or JSON schema dict for the answer.
        approval: For a tool behind ``require_approval``: ``"pause"`` (the run pauses,
            :meth:`continue_run` resumes it), ``"deny"``, or a function that decides.
        max_steps: Maximum model calls per run.
        max_tokens: Output cap per model call (Messages API default: 1024).
        request: Extra fields for every model request, for example ``{"temperature": 0}``.
        debug: Print every step to stderr. Also on with ``AEON_DEBUG_AGENT=1``.

    Example:
        >>> agent = Agent("openrouter:openai/gpt-4o-mini", tools=[read_file])  # doctest: +SKIP
        >>> agent.print_response("Summarise notes.txt")  # doctest: +SKIP
    """

    def __init__(
        self,
        model: str | Model,
        tools: Sequence[Callable[..., Any]] | ToolBox = (),
        *,
        name: str = "agent",
        role: str | None = None,
        instructions: str | Sequence[str] | None = None,
        gate: Gate | None = None,
        client: Any = None,
        db: SqliteDb | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        add_history_to_context: bool = False,
        num_history_runs: int = 3,
        enable_agentic_memory: bool = False,
        add_datetime_to_context: bool = False,
        output_schema: Any = None,
        approval: Approval = "pause",
        max_steps: int = 10,
        max_tokens: int | None = None,
        request: Mapping[str, Any] | None = None,
        debug: bool = False,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if enable_agentic_memory and db is None:
            raise ValueError("enable_agentic_memory needs db=SqliteDb(...)")
        self.model = resolve_model(model, client)
        self.name = name
        self.role = role
        self.toolbox = _toolbox(tools, gate, name)
        self.instructions = (
            [instructions] if isinstance(instructions, str) else list(instructions or [])
        )
        self.db = db
        self.session_id = session_id
        self.user_id = user_id
        self.add_history_to_context = add_history_to_context
        self.num_history_runs = num_history_runs
        self.enable_agentic_memory = enable_agentic_memory
        self.add_datetime_to_context = add_datetime_to_context
        self.schema = OutputSchema.of(output_schema) if output_schema is not None else None
        self.approval = approval
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.request = dict(request or {})
        self.debug = debug or os.environ.get("AEON_DEBUG_AGENT", "") not in ("", "0")
        self._memory_user: str | None = None
        if enable_agentic_memory:
            self.toolbox.add("update_user_memory", self._update_user_memory)

    def __repr__(self) -> str:
        return f"Agent({self.name!r}, model={self.model.id!r}, tools={list(self.toolbox.tools)})"

    @property
    def gate(self) -> Gate:
        """The gate every tool call goes through."""
        return self.toolbox.gate if self.toolbox.gate is not None else default_gate()

    # -- public API --------------------------------------------------------------------

    def run(
        self,
        input: str | Sequence[Any],  # noqa: A002 - the conventional name for run input
        *,
        stream: bool = False,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> Any:
        """Run the loop for one input.

        Returns a :class:`RunOutput`, or with ``stream=True`` an iterator of
        :class:`Event` whose last item carries the run in ``event.run``.
        """
        events = self._start(input, session_id or self.session_id, user_id or self.user_id)
        return events if stream else _drain(events)

    def continue_run(
        self, run: RunOutput, approve: bool | Mapping[str, bool] = True, *, stream: bool = False
    ) -> Any:
        """Resume a paused run with the human's answer for each pending tool call.

        ``approve`` is one answer for all pending calls, or ``{tool_name: bool}``.
        """
        if run.status != "paused":
            raise ValueError(f"run {run.run_id} is not paused (status {run.status})")
        events = self._resume(run, approve)
        return events if stream else _drain(events)

    def print_response(self, input: str | Sequence[Any], **kwargs: Any) -> RunOutput:  # noqa: A002
        """Run and print each tool call with its verdict, then the answer. For development."""
        return _drain(self.run(input, stream=True, **kwargs), printing=True)

    def cli_app(self, *, session_id: str | None = None, user_id: str | None = None) -> None:
        """A terminal chat with the agent. Approvals are asked at the prompt; ``exit`` quits."""
        sid = session_id or self.session_id or f"cli-{uuid.uuid4().hex[:8]}"
        history: list[Any] = []
        while True:
            try:
                text = input("you> ").strip()
            except EOFError:
                print()
                return
            if text in ("exit", "quit"):
                return
            if not text:
                continue
            out = self.print_response([*history, _user(text)], session_id=sid, user_id=user_id)
            while out.status == "paused":
                answers = {c.name: _ask(c) for c in out.pending}
                out = _drain(self.continue_run(out, answers, stream=True), printing=True)
            history = [m for m in out.messages if get(m, "role") != "system"]

    # -- the loop ----------------------------------------------------------------------

    def _start(
        self, prompt: str | Sequence[Any], session_id: str | None, user_id: str | None
    ) -> Iterator[Event]:
        self._memory_user = user_id
        run = RunOutput(
            run_id=uuid.uuid4().hex,
            agent=self.name,
            model=self.model.id,
            session_id=session_id,
            user_id=user_id,
            input=prompt if isinstance(prompt, str) else _last_user_text(prompt),
        )
        turn = [_user(prompt)] if isinstance(prompt, str) else list(prompt)
        run.messages = self._context(run, with_history=isinstance(prompt, str)) + turn
        t0 = time.perf_counter()
        yield self._emit(Event(RunEvent.run_started, run.run_id, {"input": run.input}))
        yield from self._loop(run, t0)

    def _resume(self, run: RunOutput, approve: bool | Mapping[str, bool]) -> Iterator[Event]:
        t0 = time.perf_counter() - run.duration_s
        for call in run.pending:
            ok = approve if isinstance(approve, bool) else bool(approve.get(call.name, False))
            call.approved = ok
            self._finish_pending(call)
            yield self._emit(_tool_event(run, call))
        run.pending = []
        self._append_results(run, run.batch)
        run.batch = []
        run.status, run.stop_reason = "stopped", "max_steps"
        yield from self._loop(run, t0)

    def _loop(self, run: RunOutput, t0: float) -> Iterator[Event]:
        while run.steps < self.max_steps:
            halted = self._halted()
            if halted is not None:
                run.stop_reason = halted
                break
            yield self._emit(
                Event(RunEvent.model_request_started, run.run_id, {"step": run.steps + 1})
            )
            calls, text = self._request(run)
            data = {"step": run.steps, "tokens": run.tokens, "tool_calls": len(calls)}
            yield self._emit(Event(RunEvent.model_request_completed, run.run_id, data))
            if not calls:
                if self._finish(run, text):
                    break
                continue
            yield from self._tools(run, calls)
            if run.status == "paused":
                run.duration_s = time.perf_counter() - t0
                pending = {"pending": [c.name for c in run.pending]}
                yield self._emit(Event(RunEvent.run_paused, run.run_id, pending, run))
                return
            self._append_results(run, calls)
        run.duration_s = time.perf_counter() - t0
        self._store(run)
        kind = RunEvent.run_completed if run.status == "completed" else RunEvent.run_stopped
        yield self._emit(Event(kind, run.run_id, {"stop_reason": run.stop_reason}, run))

    def _tools(self, run: RunOutput, calls: list[ToolCall]) -> Iterator[Event]:
        for call in calls:
            start = {"name": call.name, "args": call.args}
            yield self._emit(Event(RunEvent.tool_call_started, run.run_id, start))
            self._execute(call)
            run.tool_calls.append(call)
            yield self._emit(_tool_event(run, call))
        pending = [c for c in calls if c.approval_required and c.approved is None]
        if pending:
            run.pending, run.batch = pending, calls
            run.status, run.stop_reason = "paused", "paused"

    def _finish(self, run: RunOutput, text: str) -> bool:
        """Accept the final text; with a schema, parse it (one retry). True when done."""
        run.text = text
        if self.schema is None:
            run.content, run.status, run.stop_reason = text, "completed", "done"
            return True
        try:
            run.content = self.schema.parse(text)
        except ValueError as exc:
            if run.schema_retries >= 1:
                run.status, run.stop_reason = "stopped", "bad_output"
                return True
            run.schema_retries += 1
            run.messages.append(_user(f"{exc}. Reply with only the JSON object."))
            return False
        run.status, run.stop_reason = "completed", "done"
        return True

    # -- context -----------------------------------------------------------------------

    def _context(self, run: RunOutput, *, with_history: bool) -> list[Any]:
        system = list(self.instructions)
        if self.add_datetime_to_context:
            now = datetime.now(timezone.utc)
            system.append(f"The current date and time is {now:%Y-%m-%d %H:%M} UTC.")
        if self.enable_agentic_memory and run.user_id and self.db is not None:
            facts = self.db.get_memories(run.user_id)
            known = "\n".join(f"- {f}" for f in facts) or "- none yet"
            system.append(f"Facts you saved about this user:\n{known}")
            system.append("Call update_user_memory to save a lasting fact about the user.")
        if self.schema is not None:
            system.append(self.schema.instruction())
        run.system = "\n\n".join(system) if system else None
        out: list[Any] = []
        if run.system and self.model.wire == "openai":
            out.append({"role": "system", "content": run.system})
        if with_history and self.add_history_to_context and self.db and run.session_id:
            for past in self.db.get_runs(run.session_id, self.num_history_runs):
                if past["output"] is not None:
                    out += [_user(past["input"]), {"role": "assistant", "content": past["output"]}]
        return out

    def _store(self, run: RunOutput) -> None:
        if self.db is None or not run.session_id:
            return
        self.db.add_run(
            run_id=run.run_id,
            session_id=run.session_id,
            agent=self.name,
            user_id=run.user_id,
            input=run.input,
            output=run.text if run.status == "completed" else None,
            status=run.status,
            tokens=run.tokens,
        )

    def _update_user_memory(self, memory: str) -> str:
        """Save one lasting fact about the user (a preference, a goal, a detail)."""
        if self.db is None or not self._memory_user:
            return "No user id for this run; nothing was saved."
        self.db.add_memory(self._memory_user, memory)
        return "Saved."

    # -- one model request -------------------------------------------------------------

    def _request(self, run: RunOutput) -> tuple[list[ToolCall], str]:
        if self.model.wire == "anthropic":
            return self._request_anthropic(run)
        extra: dict[str, Any] = dict(self.request)
        specs = openai_specs(self.toolbox)
        if specs:
            extra.setdefault("tools", specs)
        if self.max_tokens is not None:  # omitted otherwise: some models reject the field
            extra.setdefault("max_tokens", self.max_tokens)
        reply = self.model.client.chat.completions.create(
            model=self.model.id, messages=run.messages, **extra
        )
        run.steps += 1
        run.tokens += self._usage(reply)
        msg = get(get(reply, "choices")[0], "message")
        raw = get(msg, "tool_calls") or []
        run.messages.append(_openai_assistant(msg, raw))
        calls = []
        for c in raw:
            fn = get(c, "function")
            calls.append(_decode(get(fn, "name", ""), get(fn, "arguments"), get(c, "id")))
        return calls, get(msg, "content") or ""

    def _request_anthropic(self, run: RunOutput) -> tuple[list[ToolCall], str]:
        extra: dict[str, Any] = dict(self.request)
        if run.system:
            extra.setdefault("system", run.system)
        specs = anthropic_specs(self.toolbox)
        if specs:
            extra.setdefault("tools", specs)
        reply = self.model.client.messages.create(
            model=self.model.id, messages=run.messages, max_tokens=self.max_tokens or 1024, **extra
        )
        run.steps += 1
        run.tokens += self._usage(reply)
        blocks = [_block(b) for b in get(reply, "content") or []]
        run.messages.append({"role": "assistant", "content": blocks})
        uses = [b for b in blocks if b.get("type") == "tool_use"]
        calls = [_decode(str(b.get("name", "")), b.get("input"), b.get("id")) for b in uses]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return calls, text

    def _append_results(self, run: RunOutput, calls: Sequence[ToolCall]) -> None:
        if not calls:
            return
        if self.model.wire == "anthropic":
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": c.call_id,
                    "content": c.result,
                    "is_error": c.is_error,
                }
                for c in calls
            ]
            run.messages.append({"role": "user", "content": blocks})
        else:
            run.messages += [
                {"role": "tool", "tool_call_id": c.call_id, "content": c.result} for c in calls
            ]

    # -- one tool call -----------------------------------------------------------------

    def _execute(self, call: ToolCall) -> None:
        if call.is_error:  # bad arguments, already answered
            return
        try:
            call.result = as_text(self.toolbox.call(call.name, call.args))
        except ActionLimited as exc:
            self._limited(call, exc)
        except ActionBlocked as exc:
            call.result, call.is_error, call.blocked = blocked_message(exc), True, True
        except KeyError as exc:
            call.result, call.is_error = f"Error: {exc.args[0]}", True
        except Exception as exc:
            call.result, call.is_error = f"Error: {type(exc).__name__}: {exc}", True

    def _limited(self, call: ToolCall, exc: ActionLimited) -> None:
        call.approval_required = True
        if self.approval == "pause":
            return
        call.approved = bool(self.approval(call)) if callable(self.approval) else False
        if not call.approved:
            call.result, call.is_error, call.blocked = blocked_message(exc), True, True
            return
        self._finish_pending(call)

    def _finish_pending(self, call: ToolCall) -> None:
        if not call.approved:
            call.result = "The user did not approve this action."
            call.is_error, call.blocked = True, True
            return
        with _approved_once(self.gate, call.name):
            call.result, call.is_error = self.toolbox.run_text(call.name, call.args)
        call.blocked = call.result.startswith("Æon blocked")

    # -- helpers -----------------------------------------------------------------------

    def _halted(self) -> StopReason | None:
        g = self.gate
        if g.kill_switch.engaged:
            return "kill_switch"
        if g.safe_state(self.toolbox.agent) is not None:
            return "safe_state"
        return None

    def _usage(self, reply: Any) -> int:
        tokens = total_tokens(get(reply, "usage")) or 0
        monitor = self.gate.monitor
        if monitor is not None and tokens:
            monitor.record_usage(self.toolbox.agent, tokens=tokens)
        return tokens

    def _emit(self, ev: Event) -> Event:
        if self.debug:
            data = json.dumps(dict(ev.data), default=str, ensure_ascii=False)
            print(f"[aeon:{self.name}] {ev.event.value} {data}", file=sys.stderr)
        return ev


# -- module helpers ----------------------------------------------------------------------


def _toolbox(
    tools: Sequence[Callable[..., Any]] | ToolBox, gate: Gate | None, name: str
) -> ToolBox:
    if isinstance(tools, ToolBox):
        return tools
    box = ToolBox(gate=gate, agent=name)
    for fn in tools:
        box.add(getattr(fn, "__name__", repr(fn)), fn)
    return box


@contextmanager
def _approved_once(gate: Gate, tool: str) -> Iterator[None]:
    """Approve the next LIMIT decision for ``tool`` only (the human said yes)."""
    previous = gate.approver
    used = False

    def approver(decision: Any) -> bool:
        nonlocal used
        if not used and decision.action.tool == tool:
            used = True
            return True
        return bool(previous(decision)) if previous is not None else False

    gate.approver = approver
    try:
        yield
    finally:
        gate.approver = previous


def _decode(name: str, raw: Any, call_id: Any) -> ToolCall:
    try:
        return ToolCall(name, parse_arguments(raw), call_id=call_id)
    except ValueError as exc:
        return ToolCall(name, {}, f"Error: {exc}", is_error=True, call_id=call_id)


def _tool_event(run: RunOutput, call: ToolCall) -> Event:
    data: dict[str, Any] = {"name": call.name, "args": call.args, "result": call.result}
    if call.approval_required and call.approved is None:
        return Event(RunEvent.tool_call_approval_required, run.run_id, data)
    kind = RunEvent.tool_call_blocked if call.blocked else RunEvent.tool_call_completed
    return Event(kind, run.run_id, {**data, "is_error": call.is_error})


def _drain(events: Iterator[Event], *, printing: bool = False) -> RunOutput:
    out = None
    for ev in events:
        if printing:
            _print_event(ev)
        out = ev.run or out
    assert out is not None
    return out


def _print_event(ev: Event) -> None:
    d = ev.data
    if ev.event in (RunEvent.tool_call_completed, RunEvent.tool_call_blocked):
        mark = " BLOCKED" if ev.event is RunEvent.tool_call_blocked else ""
        print(f"-> {d['name']}({json.dumps(d['args'], ensure_ascii=False)}){mark}")
        print(f"   {str(d['result'])[:300]}")
    elif ev.event is RunEvent.tool_call_approval_required:
        print(f"-> {d['name']}({json.dumps(d['args'], ensure_ascii=False)}) needs approval")
    elif ev.run is not None and ev.event is not RunEvent.run_paused:
        run = ev.run
        if run.status == "completed":
            print(run.content if isinstance(run.content, str) else _pretty(run.content))
        else:
            print(f"[stopped: {run.stop_reason}]")


def _pretty(obj: Any) -> str:
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        obj = dump()
    elif hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        obj = asdict(obj)
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _ask(call: ToolCall) -> bool:
    try:
        answer = input(f"approve {call.name}({json.dumps(call.args, ensure_ascii=False)})? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes", "s", "sim")


def _user(text: str) -> dict[str, Any]:
    return {"role": "user", "content": text}


def _last_user_text(messages: Sequence[Any]) -> str:
    for m in reversed(messages):
        if get(m, "role") == "user" and isinstance(get(m, "content"), str):
            return str(get(m, "content"))
    return ""


def _openai_assistant(msg: Any, calls: Sequence[Any]) -> dict[str, Any]:
    """The assistant turn as a plain dict, which every Chat Completions server accepts.

    Fields the server added (for example OpenRouter's ``reasoning_details``) are kept and
    sent back unchanged, since reasoning models need them to continue.
    """
    out: dict[str, Any] = {k: v for k, v in _fields(msg).items() if v is not None}
    out["role"] = "assistant"
    out["content"] = get(msg, "content") or ""
    out.pop("tool_calls", None)
    if calls:
        out["tool_calls"] = [
            {
                "id": get(c, "id"),
                "type": "function",
                "function": {
                    "name": get(get(c, "function"), "name", ""),
                    "arguments": _args_text(get(get(c, "function"), "arguments")),
                },
            }
            for c in calls
        ]
    return out


def _fields(msg: Any) -> dict[str, Any]:
    if isinstance(msg, Mapping):
        return dict(msg)
    dump = getattr(msg, "model_dump", None)  # SDK objects (pydantic)
    if callable(dump):
        value = dump(exclude_none=True)
        return dict(value) if isinstance(value, Mapping) else {}
    return {}


def _args_text(raw: Any) -> str:
    if raw is None:
        return "{}"
    if isinstance(raw, str):
        return raw
    return json.dumps(raw)


def _block(block: Any) -> dict[str, Any]:
    """A Messages API content block as a plain dict (SDK objects or dicts)."""
    kind = get(block, "type")
    if kind == "text":
        return {"type": "text", "text": get(block, "text", "")}
    if kind == "tool_use":
        return {
            "type": "tool_use",
            "id": get(block, "id"),
            "name": get(block, "name"),
            "input": get(block, "input") or {},
        }
    if isinstance(block, Mapping):
        return dict(block)
    dump = getattr(block, "model_dump", None)
    return dump() if callable(dump) else {"type": kind}
