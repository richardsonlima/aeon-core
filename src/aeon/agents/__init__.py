"""Run a real LLM agent with every tool call behind the gate.

:class:`Agent` is the loop (model call, gated tool calls, repeat). The clients reach a
provider over HTTP with the standard library only; the official SDK clients work too.
No SDK is imported here.
"""

from aeon.agents.clients import AnthropicClient, OpenAICompatible, ProviderError
from aeon.agents.loop import Agent, AgentRun, ToolCall

__all__ = [
    "Agent",
    "AgentRun",
    "AnthropicClient",
    "OpenAICompatible",
    "ProviderError",
    "ToolCall",
]
