"""Quickstart: gate a plain Python agent, first in shadow mode, then enforced."""

from aeon.axioms import ActionBlocked, default_gate, enforce


class Agent:
    def executor(self, tool, args):
        return {
            "read_file": lambda path: f"contents of {path}",
            "delete_file": lambda path: f"deleted {path}",
        }[tool](**args)


agent = Agent()
agent.executor = enforce(agent.executor)  # every tool call now passes the gate
gate = default_gate()  # built from aeon.toml, axioms from aeon_axioms.py
plan = [("read_file", {"path": "notes.txt"}), ("delete_file", {"path": "prod.db"})]

for mode in ("shadow", "enforce"):
    gate.set_mode(mode)
    print(f"-- {mode} mode")
    for tool, args in plan:
        try:
            print(f"   {tool} -> {agent.executor(tool, args)}")
        except ActionBlocked as exc:
            print(f"   {tool} -> {exc}")

gate.audit.flush(5)
c = gate.counters
print(f"decisions={c['decisions']} allowed={c['allowed']} denied={c['denied']}")
