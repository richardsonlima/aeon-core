"""A team: a coordinator agent that delegates tasks to member agents.

Each member becomes a tool of the coordinator (``delegate_to_<name>``), so delegation is
itself a gated, audited tool call: an axiom can deny delegating to a member, and the
kill-switch stops the whole team. Members keep their own tools and gates.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from aeon.adapters.plain import ToolBox
from aeon.agents.loop import Agent, RunOutput
from aeon.agents.models import Model
from aeon.axioms import Gate

__all__ = ["Team"]


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    return slug or "member"


class Team:
    """A coordinator model and the member agents it can hand tasks to.

    Args:
        members: The member agents. Their ``name`` and ``role`` describe them to the
            coordinator.
        model: The coordinator's model, as for :class:`Agent`.
        name: The team's name (the coordinator's agent name in the gate).
        instructions: How the coordinator should work, for example "hear both sides,
            then synthesize a recommendation".
        gate: The gate for delegation calls.
        **agent_options: Passed to the coordinator :class:`Agent` (``client``, ``db``,
            ``session_id``, ``max_steps``, ``request``, ``debug``...).

    Raises:
        ValueError: No members, or two members with the same name.
    """

    def __init__(
        self,
        members: Sequence[Agent],
        model: str | Model,
        *,
        name: str = "team",
        instructions: str | Sequence[str] | None = None,
        gate: Gate | None = None,
        **agent_options: Any,
    ) -> None:
        if not members:
            raise ValueError("a team needs at least one member")
        self.members = {_slug(m.name): m for m in members}
        if len(self.members) != len(members):
            raise ValueError("team members need distinct names")
        box = ToolBox(gate=gate, agent=name)
        for slug, member in self.members.items():
            box.add(f"delegate_to_{slug}", self._delegate(member))
        roster = "\n".join(
            f"- {m.name}: {m.role or 'no role given'} (tool delegate_to_{s})"
            for s, m in self.members.items()
        )
        own = [instructions] if isinstance(instructions, str) else list(instructions or [])
        system = [
            "You coordinate a team. Hand tasks to members with their delegate tools, "
            "then combine what they report into the final answer.",
            f"Members:\n{roster}",
            *own,
        ]
        self.coordinator = Agent(model, box, name=name, instructions=system, **agent_options)
        self.name = name
        self.member_runs: list[RunOutput] = []

    def __repr__(self) -> str:
        return f"Team({self.name!r}, members={list(self.members)})"

    def _delegate(self, member: Agent) -> Callable[[str], str]:
        def delegate(task: str) -> str:
            out = member.run(task)
            self.member_runs.append(out)
            if out.status == "completed":
                return out.content if isinstance(out.content, str) else str(out.content)
            return f"[{member.name} stopped: {out.stop_reason}]"

        delegate.__doc__ = f"Hand a task to {member.name}. {member.role or ''}".strip()
        return delegate

    def run(self, input: str | Sequence[Any], **kwargs: Any) -> Any:  # noqa: A002
        """Run the coordinator; see :meth:`Agent.run`."""
        self.member_runs = []
        return self.coordinator.run(input, **kwargs)

    def continue_run(self, run: RunOutput, approve: bool | Mapping[str, bool] = True) -> Any:
        """Resume a paused coordinator run; see :meth:`Agent.continue_run`."""
        return self.coordinator.continue_run(run, approve)

    def print_response(self, input: str | Sequence[Any], **kwargs: Any) -> RunOutput:  # noqa: A002
        """Run and print the delegations and the final answer."""
        self.member_runs = []
        return self.coordinator.print_response(input, **kwargs)
