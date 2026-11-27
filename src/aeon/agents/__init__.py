"""Build and run LLM agents with every tool call behind the gate.

:class:`Agent` is a model, plain functions as tools, and instructions, with sessions and
user memory (:class:`SqliteDb`), structured output, step events and human approval.
The clients reach a provider over HTTP with the standard library only; the official SDK
clients work too. No SDK is imported here.
"""

from aeon.agents.clients import AnthropicClient, OpenAICompatible, ProviderError
from aeon.agents.loop import Agent, AgentRun, Event, RunEvent, RunOutput, ToolCall
from aeon.agents.models import PROVIDERS, Model, resolve_model
from aeon.agents.storage import SqliteDb

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
    "ToolCall",
    "resolve_model",
]
