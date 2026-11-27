"""Tests for Team and Workflow."""

from __future__ import annotations

import pytest

from aeon.agents import Agent, Step, Team, Workflow
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools, require_approval
from tests.test_agent_sdk import Report, Script, call, delete_file, say

# -- team --------------------------------------------------------------------------------


def test_team_delegates_through_the_gate() -> None:
    bull = Agent("m", name="Bull", role="argue for", client=Script(say("buy")))
    bear = Agent("m", name="Bear", role="argue against", client=Script(say("sell")))
    coord = Script(
        call("delegate_to_bull", {"task": "case for"}, "a"),
        call("delegate_to_bear", {"task": "case against"}, "b"),
        say("balanced: hold"),
    )
    team = Team([bull, bear], "m", client=coord, instructions="be fair")
    run = team.run("invest?")
    assert run.content == "balanced: hold"
    assert [c.result for c in run.tool_calls] == ["buy", "sell"]
    assert len(team.member_runs) == 2
    system = coord.requests[0]["messages"][0]["content"]
    assert "Bull: argue for" in system and "be fair" in system
    assert "Team('team'" in repr(team)


def test_team_denied_delegation_and_stopped_member(capsys: pytest.CaptureFixture[str]) -> None:
    gate = Gate([deny_tools(["delegate_to_bear"])], mode="enforce")
    stuck = Agent("m", name="Bull", client=Script(say("x")), max_steps=1, output_schema=Report)
    bear = Agent("m", name="Bear", client=Script(say("y")))
    coord = Script(call("delegate_to_bull", {"task": "t"}), say("done"))
    team = Team([stuck, bear], "m", client=coord, gate=gate)
    run = team.print_response("go")
    assert run.tool_calls[0].result.startswith("[Bull stopped:")
    coord.replies = [call("delegate_to_bear", {"task": "t"})]
    assert team.run("go").tool_calls[0].blocked
    with pytest.raises(ValueError, match="at least one"):
        Team([], "m", client=coord)
    with pytest.raises(ValueError, match="distinct"):
        Team([bear, Agent("m", name="bear", client=coord)], "m", client=coord)


def test_team_continue_run() -> None:
    worker = Agent("m", name="w", client=Script(say("ok")))
    coord = Script(call("delegate_to_w", {"task": "t"}), say("fin"))
    team = Team([worker], "m", client=coord, gate=Gate([require_approval(["delegate_to_w"])]))
    team.coordinator.gate.mode = team.coordinator.gate.mode.parse("enforce")
    paused = team.run("go")
    assert paused.status == "paused"
    assert team.continue_run(paused).content == "fin"


# -- workflow ----------------------------------------------------------------------------


def test_workflow_runs_steps_in_order(capsys: pytest.CaptureFixture[str]) -> None:
    research = Agent("m", client=Script(say(" raw data ")))
    writer_client = Script(say("brief"))
    writer = Agent("m", client=writer_client)
    wf = Workflow([Step("Research", agent=research), Step("Clean", function=str.strip),
                   Step("Write", agent=writer)], name="w")  # fmt: skip
    out = wf.print_response("analyze")
    assert out.status == "completed" and out.content == "brief"
    assert [s.name for s in out.steps] == ["Research", "Clean", "Write"]
    assert writer_client.requests[0]["messages"][-1]["content"] == "raw data"
    assert "== Clean (completed)" in capsys.readouterr().out
    assert "Workflow('w'" in repr(wf)


def test_workflow_stops_at_a_step_that_does_not_complete(
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate = Gate([deny_tools(["delete_file"])], mode="enforce")
    blocked = Agent(
        "m", [delete_file], gate=gate, client=Script(call("delete_file", {"path": "p"}))
    )
    team = Team([Agent("m", name="x", client=Script(say("a")))], "m", client=Script(say("t")))
    after = Agent("m", client=Script())
    wf = Workflow([Step("Team", team=team), Step("Act", agent=blocked), Step("After", agent=after)])
    out = wf.print_response("go")
    assert out.status == "stopped" and out.stopped_at == "Act" and out.content is None
    assert "[stopped: safe_state]" in capsys.readouterr().out
    with pytest.raises(ValueError, match="exactly one"):
        Step("bad")
    with pytest.raises(ValueError, match="at least one"):
        Workflow([])
    with pytest.raises(ValueError, match="distinct"):
        Workflow([Step("a", function=str), Step("a", function=str)])
