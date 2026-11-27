"""Build and run LLM agents with every tool call behind the gate.

:class:`Agent` is a model, plain functions as tools, and instructions, with sessions and
user memory (:class:`SqliteDb`), structured output, step events and human approval.
:class:`Team` delegates to member agents and :class:`Workflow` runs steps in order. The
clients reach a provider over HTTP with the standard library only; the official SDK
clients work too. No SDK is imported here.
"""

from aeon.agents.clients import AnthropicClient, OpenAICompatible, ProviderError
from aeon.agents.loop import Agent, AgentRun, Event, RunEvent, RunOutput, ToolCall
from aeon.agents.models import PROVIDERS, Model, resolve_model
from aeon.agents.storage import SqliteDb
from aeon.agents.team import Team
from aeon.agents.workflow import Step, StepOutput, Workflow, WorkflowOutput

__all__ = [
    "PROVIDERS",
    "Agent",
    "AgentRun",
    "AnthropicClient",
    "Event",
    "Model",
    "OpenAICompatible",
    "ProviderError",
    "RunEvent",
    "RunOutput",
    "SqliteDb",
    "Step",
    "StepOutput",
    "Team",
    "ToolCall",
    "Workflow",
    "WorkflowOutput",
    "resolve_model",
]
