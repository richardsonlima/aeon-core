# Build an agent

`aeon.agents` builds and runs LLM agents whose tool calls all go through the gate. No provider SDK is needed: the clients use the standard library. A blocked call comes back to the model as text, a `BLOCK` puts the agent in Safe State and stops the loop, and every decision lands in the audit log.

## The smallest agent

```python
from aeon.agents import Agent
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools


def read_file(path: str) -> str:
    """Read a text file and return its contents."""
    return open(path).read()


def delete_file(path: str) -> str:
    """Delete a file permanently."""
    ...


agent = Agent(
    "openrouter:openai/gpt-4o-mini",
    tools=[read_file, delete_file],
    gate=Gate([deny_tools(["delete_file"])], mode="enforce"),
    instructions="You are an ops assistant. Use the tools.",
)
agent.print_response("Summarise notes.txt")
```

Tools are plain functions: the signature becomes the JSON schema and the first docstring line the description. `run()` returns a `RunOutput` with `content`, `status` (`completed`, `paused`, `stopped`), `stop_reason`, `tool_calls` (each with `blocked`), `tokens`, `duration_s` and the full `messages`.

## Models

`model` is `provider:model`. The key comes from the environment.

| Provider | Example | Key |
|---|---|---|
| OpenRouter | `openrouter:openai/gpt-4o-mini` | `OPENROUTER_API_KEY` |
| OpenAI | `openai:gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic:claude-haiku-5.5` | `ANTHROPIC_API_KEY` |
| Groq | `groq:llama-3.1-8b-instant` | `GROQ_API_KEY` |
| Ollama | `ollama:qwen2.5:3b` | none |
| Any Chat Completions server | `resolve_model("compatible:m", base_url=...)` | `OPENAI_API_KEY`, optional |

You can also pass an official SDK client: `Agent("gpt-4o-mini", tools, client=openai.OpenAI())`. Reasoning fields the provider returns (`reasoning_details`) are sent back unchanged.

## Human approval

A `require_approval` rule makes a tool a `LIMIT`: the run pauses instead of running it.

```python
from aeon.axioms.builtin import require_approval

agent = Agent(model, [delete_file], gate=Gate([require_approval(["delete_file"])], mode="enforce"))
run = agent.run("Delete prod.db")
if run.status == "paused":
    print([c.name for c in run.pending])  # ['delete_file']
    run = agent.continue_run(run, approve=True)  # or approve={"delete_file": False}
```

`approval="deny"` refuses without pausing; `approval=lambda call: ...` decides inline. The yes applies to that one call only.

## Sessions and memory

```python
from aeon.agents import SqliteDb

agent = Agent(
    model,
    db=SqliteDb("agents.db"),
    add_history_to_context=True,  # earlier turns of the session
    num_history_runs=3,
    enable_agentic_memory=True,  # an update_user_memory tool, behind the gate
    add_datetime_to_context=True,
)
agent.run("I prefer short answers", session_id="s1", user_id="rick")
agent.run("What do I prefer?", session_id="s2", user_id="rick")  # from memory
```

The database stores prompts and answers in plain text: keep the file private.

## Structured output

```python
from dataclasses import dataclass


@dataclass
class Report:
    revenue: int
    costs: int


run = Agent(model, [read_file], output_schema=Report).run("Fill the report from q3.txt")
run.content  # Report(revenue=120, costs=80)
```

A dataclass, a Pydantic model or a JSON schema dict works. An invalid answer gets one retry; a second one stops the run with `stop_reason="bad_output"`.

## Events, debug and a terminal chat

```python
for event in agent.run("...", stream=True):
    print(event.event, event.data)  # RunStarted, ModelRequestCompleted, ToolCallBlocked, ...
```

`debug=True` (or `AEON_DEBUG_AGENT=1`) prints every step to stderr. `agent.cli_app()` is a terminal chat that asks for approvals at the prompt.

## Teams and workflows

```python
from aeon.agents import Step, Team, Workflow

bull = Agent(model, name="Bull", role="Make the case for.")
bear = Agent(model, name="Bear", role="Make the case against.")
team = Team([bull, bear], model, instructions="Hear both, then recommend.")
team.print_response("Should we adopt a monorepo?")

flow = Workflow([Step("Debate", team=team), Step("Brief", agent=writer)])
flow.run("Should we adopt a monorepo?").content
```

A team member is a tool of the coordinator (`delegate_to_bull`), so an axiom can deny a delegation and the kill-switch stops the whole team. A workflow stops at the first step that does not complete.

## From the command line

```bash
export OPENROUTER_API_KEY=...
aeon agent run "Read notes.txt and do what it says." --tools tools.py \
  --model openai/gpt-4o-mini --mode enforce
```

The tools are the public functions of `tools.py` (or its `TOOLS` list); the gate comes from `aeon.toml`. See the [example](https://github.com/richardsonlima/aeon-core/tree/main/examples/agent_sdk) and the [roadmap](../roadmap/agent-sdk.md).
