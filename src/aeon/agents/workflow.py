"""A workflow: named steps run in order, each step's output the next step's input.

A step is an :class:`~aeon.agents.Agent`, a :class:`~aeon.agents.Team`, or a plain
function ``(text) -> text``. Agent and team steps keep every tool call behind the gate;
a step that does not complete (blocked into Safe State, kill-switch, paused for approval,
out of steps) stops the workflow there, so a later step never acts on a missing result.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from aeon.agents.loop import Agent, RunOutput
from aeon.agents.team import Team

__all__ = ["Step", "StepOutput", "Workflow", "WorkflowOutput"]


@dataclass(frozen=True)
class Step:
    """One step. Give exactly one of ``agent``, ``team`` or ``function``."""

    name: str
    agent: Agent | None = None
    team: Team | None = None
    function: Callable[[str], Any] | None = None

    def __post_init__(self) -> None:
        given = [x for x in (self.agent, self.team, self.function) if x is not None]
        if len(given) != 1:
            raise ValueError(f"step {self.name!r}: give exactly one of agent, team, function")


@dataclass
class StepOutput:
    """What one step produced."""

    name: str
    content: Any
    status: str
    run: RunOutput | None = None


@dataclass
class WorkflowOutput:
    """The outcome of a workflow run.

    Attributes:
        content: The last completed step's output.
        status: ``completed``, or ``stopped`` when a step did not complete.
        stopped_at: The name of the step that stopped the workflow.
    """

    name: str
    content: Any = None
    status: Literal["completed", "stopped"] = "completed"
    steps: list[StepOutput] = field(default_factory=list)
    stopped_at: str | None = None


class Workflow:
    """Steps over agents, teams and functions, run in order.

    Args:
        steps: The steps; names must be distinct.
        name: The workflow's name.

    Raises:
        ValueError: No steps, or duplicate step names.
    """

    def __init__(self, steps: Sequence[Step], *, name: str = "workflow") -> None:
        if not steps:
            raise ValueError("a workflow needs at least one step")
        if len({s.name for s in steps}) != len(steps):
            raise ValueError("workflow steps need distinct names")
        self.steps = list(steps)
        self.name = name

    def __repr__(self) -> str:
        return f"Workflow({self.name!r}, steps={[s.name for s in self.steps]})"

    def run(self, input: str, **kwargs: Any) -> WorkflowOutput:  # noqa: A002
        """Run every step in order. ``kwargs`` (``session_id``, ``user_id``) go to agents."""
        out = WorkflowOutput(self.name)
        current: Any = input
        for step in self.steps:
            result = self._run_step(step, current, kwargs)
            out.steps.append(result)
            if result.status != "completed":
                out.status, out.stopped_at = "stopped", step.name
                return out
            current = result.content
        out.content = current
        return out

    def print_response(self, input: str, **kwargs: Any) -> WorkflowOutput:  # noqa: A002
        """Run and print each step's output."""
        out = self.run(input, **kwargs)
        for s in out.steps:
            print(f"== {s.name} ({s.status})")
            print(
                s.content if s.content is not None else f"[stopped: {s.run and s.run.stop_reason}]"
            )
        return out

    @staticmethod
    def _run_step(step: Step, text: Any, kwargs: dict[str, Any]) -> StepOutput:
        if step.function is not None:
            return StepOutput(step.name, step.function(str(text)), "completed")
        runner: Agent | Team = step.agent if step.agent is not None else step.team  # type: ignore[assignment]
        run: RunOutput = runner.run(str(text), **kwargs)
        content = run.content if run.status == "completed" else None
        return StepOutput(step.name, content, run.status, run)
