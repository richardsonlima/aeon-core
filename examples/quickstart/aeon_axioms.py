"""Axioms for the quickstart: destructive tools need explicit approval."""

from aeon.axioms import axiom

DESTRUCTIVE = {"delete_file", "drop_table", "send_email"}


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """A destructive tool runs only when a human approved it."""
    return action.tool not in DESTRUCTIVE or action.approved
