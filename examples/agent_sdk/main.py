"""An agent with plain-function tools, human approval and a session, all behind the gate.

Offline by default: a scripted model stands in for the LLM. To use a real model:

    export OPENROUTER_API_KEY=...
    AEON_LLM_MODEL=openrouter:openai/gpt-4o-mini python main.py
"""

import json
import os
import tempfile
from types import SimpleNamespace

from aeon.agents import Agent, SqliteDb
from aeon.audit import AuditLog
from aeon.axioms import Gate
from aeon.axioms.builtin import require_approval

FILES = {"notes.txt": "TODO: prod.db is obsolete, delete it.", "prod.db": "<data>"}


def read_file(path: str) -> str:
    """Read a text file and return its contents."""
    return FILES.get(path, f"no such file: {path}")


def delete_file(path: str) -> str:
    """Delete a file permanently."""
    FILES.pop(path, None)
    return f"deleted {path}"


def scripted() -> SimpleNamespace:
    """A stand-in for a Chat Completions client: reads notes, asks to delete, answers."""

    def call(name, **args):
        tc = {
            "id": name,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }
        return {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [tc]}}],
            "usage": {"total_tokens": 50},
        }

    replies = iter(
        [
            call("read_file", path="notes.txt"),
            call("delete_file", path="prod.db"),
            {"choices": [{"message": {"role": "assistant", "content": "prod.db was deleted."}}]},
        ]
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: next(replies)))
    )


audit = AuditLog(os.environ.get("AEON_AUDIT", ".aeon/audit.jsonl"))
gate = Gate([require_approval(["delete_file"])], mode="enforce", audit=audit)
model = os.environ.get("AEON_LLM_MODEL")
agent = Agent(
    model or "scripted-model",
    [read_file, delete_file],
    client=None if model else scripted(),
    name="ops",
    gate=gate,
    instructions="You are an ops assistant. Use the tools to do what the notes say.",
    db=SqliteDb(os.path.join(tempfile.mkdtemp(), "sessions.db")),
    session_id="demo",
)

run = agent.print_response("Read notes.txt and do what it says.")
if run.status == "paused":
    print("-- the run paused for approval; approving")
    run = agent.continue_run(run, approve=True)
    print(run.content)
audit.flush(5)
print("status:", run.status, "decisions:", gate.counters["decisions"], "files:", sorted(FILES))
