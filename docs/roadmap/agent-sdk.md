# Roadmap: an agent SDK with the gate built in

Æon started as the control layer that sits between an agent and its tools. This page lists what it needs to also be the SDK you build the agent with, agents, teams and workflows, with sessions, memory and human approval.

The difference stays the same. In Æon every tool call of every agent, team member and workflow step goes through the gate: axioms, autonomy levels, Safe State, kill-switch, budget, and the hash-chained audit log. Guardrails added on top of a loop can be skipped; here the loop cannot run a tool any other way.

Status keys: **shipped** (in a release, tested), **next** (being built for the next release), **planned** (accepted, not started), **out of scope** (not planned; use another tool).

## Primitives

| Capability | What it means | Status | How Æon does it |
|---|---|---|---|
| Agent | A model, tools and instructions, and the loop between them | **shipped** (0.5.1) | `aeon.agents.Agent`; every tool call through a `ToolBox` and the gate |
| Model string | `model="openrouter:openai/gpt-4o-mini"` instead of building a client | next | `provider:model` resolved to the stdlib HTTP clients |
| Plain functions as tools | `tools=[read_file, search]` | next | wrapped in a `ToolBox` bound to the agent's gate |
| Team | A coordinator delegates to member agents | next | members exposed to the coordinator as tools, so delegation itself is gated and audited |
| Workflow | Repeatable steps over agents, teams and functions | next | sequential steps, each step's output is the next input; a halted step stops the workflow |

## Running and output

| Capability | Status | Notes |
|---|---|---|
| `run()` returning a run object (content, messages, metrics, tool calls) | **shipped** (`AgentRun`) | next: `run_id`, `session_id`, timing, status |
| `print_response()` for development | next | tool calls with their verdict, then the answer |
| Event stream (run started, model request, tool call started, completed, blocked, run completed) | next | step-level events from `run(stream=True)` |
| Token streaming | planned | needs Server-Sent Events parsing per provider |
| Structured output (`output_schema`) | next | JSON schema from a dataclass or a Pydantic model, validated, one retry on bad JSON |
| Async (`arun`) | planned | the gate already supports async tools |
| Interactive CLI (`cli_app`) | next | `Agent.cli_app()` and `aeon agent chat` |
| Debug mode | next | `debug=True` or `AEON_DEBUG_AGENT=1` prints messages and token use per step |
| Reasoning models | **shipped** | provider reasoning fields (`reasoning_details`) are sent back unchanged |

## Models

| Capability | Status | Notes |
|---|---|---|
| OpenAI, OpenRouter, Groq, vLLM, LM Studio, Ollama | **shipped** | `OpenAICompatible`, standard library only |
| Anthropic Messages API | **shipped** | `AnthropicClient`, also through gateways with bearer auth |
| Official SDK clients | **shipped** | the loop is duck-typed: `openai.OpenAI()` and `anthropic.Anthropic()` work |
| Fallback models | planned | try the next model on a provider error |
| 30+ native provider integrations | out of scope | OpenRouter and compatible servers cover most providers through one API |

## Memory and context

| Capability | Status | Notes |
|---|---|---|
| Storage of sessions (`db=SqliteDb(...)`, `session_id`) | next | stdlib `sqlite3`, no extra dependency |
| History in context (`add_history_to_context`, `num_history_runs`) | next | |
| User memory (`enable_agentic_memory`, `user_id`) | next | an `update_user_memory` tool, itself behind the gate |
| Session state | planned | |
| Datetime in context | next | `add_datetime_to_context` |
| Knowledge (RAG over a vector database) | out of scope for now | needs embeddings and a vector store; can be added as a tool |
| Compression, learning, context providers | out of scope for now | |

## Control and safety

| Capability | Status | Notes |
|---|---|---|
| Guardrails on tool calls | **shipped** | axioms, built-in rules, autonomy levels; enforce or shadow |
| Kill-switch and Safe State | **shipped** | the loop stops before the next model call |
| Budget on tokens and behaviour | **shipped** | token usage from every reply feeds the monitor |
| Tamper-evident audit of every decision | **shipped** | hash chain, `aeon audit verify` |
| Fault injection and campaigns | **shipped** | `aeon chaos`, pre-registered campaigns |
| Human-in-the-loop approval | next | a `require_approval` rule pauses the run; `continue_run(approve=...)` resumes it |
| Input and output guardrails (text) | planned | hooks on the prompt and the answer |
| Pre-run and post-run hooks | planned | |

## Operations

| Capability | Status | Notes |
|---|---|---|
| Project scaffold | next | `aeon create agent` writes a runnable agent project |
| Serve agents over HTTP | planned | the runtime already serves the gate; agents next |
| Control plane | **shipped** for the gate | decisions, campaigns, audit and claims at `/ui/` |
| Docs over MCP for coding agents | **shipped** | `aeon docs mcp` |
| Observability (OpenTelemetry) | planned | |
| Evals | planned | campaigns already measure detection and false positives |
| Background execution, scheduler | out of scope for now | |
| Multimodal input | out of scope for now | |

## Evidence

The agent loop was run against real models through OpenRouter on 2026-11-27: `openai/gpt-4o-mini`, `anthropic/claude-haiku-5.5`, `qwen/qwen3-32b`, `meta-llama/llama-3.1-8b-instruct` and `google/gemini-2.5-flash-lite`, with a tool result that told the model to delete a file. Four models tried the delete and the gate blocked it; one asked the user first. The Messages API path and a reasoning model (`openai/gpt-5-nano` with reasoning on) were also run. These are single runs on one day, not a measured rate: see [Known limits](../known-limits.md).
