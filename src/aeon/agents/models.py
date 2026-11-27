"""Resolve ``"provider:model"`` strings to a client and a wire format.

``Agent(model="openrouter:openai/gpt-4o-mini")`` needs no client code: the provider picks
the base URL and the API key variable, and the rest of the string is the model id.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from aeon.adapters._common import get

__all__ = ["PROVIDERS", "Model", "resolve_model"]

Wire = Literal["openai", "anthropic"]

# provider -> (base URL, API key variable, wire format)
PROVIDERS: dict[str, tuple[str | None, str | None, Wire]] = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "openai"),
    "anthropic": ("https://api.anthropic.com", "ANTHROPIC_API_KEY", "anthropic"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai"),
    "ollama": ("http://localhost:11434/v1", None, "openai"),
    "compatible": (None, "OPENAI_API_KEY", "openai"),
}


@dataclass(frozen=True)
class Model:
    """A model id with the client that serves it.

    Attributes:
        id: The provider's model id, for example ``openai/gpt-4o-mini``.
        client: An object with ``chat.completions.create`` or ``messages.create``.
        wire: ``openai`` (Chat Completions) or ``anthropic`` (Messages API).
        provider: The provider name, when the model came from a string.
    """

    id: str
    client: Any
    wire: Wire
    provider: str | None = None


def detect_wire(client: Any) -> Wire:
    """Tell the API shape from the client: Chat Completions or Messages."""
    if get(client, "chat") is not None:
        return "openai"
    if get(client, "messages") is not None:
        return "anthropic"
    raise ValueError("cannot tell the provider from the client; pass a provider:model string")


def resolve_model(model: str | Model, client: Any = None, *, base_url: str | None = None) -> Model:
    """Turn ``"provider:model"`` (or a model id plus a client) into a :class:`Model`.

    Args:
        model: ``"openrouter:openai/gpt-4o-mini"``, ``"anthropic:claude-haiku-5.5"``,
            ``"ollama:qwen2.5:3b"``, a bare model id when ``client`` is given, or a
            :class:`Model`.
        client: An SDK or HTTP client to use instead of building one.
        base_url: Overrides the provider's URL (required for ``compatible``).

    Raises:
        ValueError: Unknown provider, no API key in the environment, or no base URL.
    """
    if isinstance(model, Model):
        return model
    if client is not None:
        return Model(model, client, detect_wire(client))
    provider, sep, model_id = model.partition(":")
    if not sep or not model_id:
        raise ValueError(
            f"model {model!r}: use provider:model, for example "
            "'openrouter:openai/gpt-4o-mini', or pass client="
        )
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; known: {', '.join(sorted(PROVIDERS))}")
    default_url, key_env, wire = PROVIDERS[provider]
    url = base_url or default_url
    if url is None:
        raise ValueError(f"provider {provider!r} needs base_url")
    key = os.environ.get(key_env) if key_env else None
    if key_env and not key and provider != "compatible":
        raise ValueError(f"{key_env} is not set; export it before running")
    return Model(model_id, _client(provider, wire, url, key), wire, provider)


def _client(provider: str, wire: Wire, url: str, key: str | None) -> Any:
    from aeon.agents.clients import AnthropicClient, OpenAICompatible

    if wire == "anthropic":
        return AnthropicClient(key, base_url=url)
    headers = {"x-title": "aeon-core"} if provider == "openrouter" else None
    return OpenAICompatible(url, key or "", headers=headers)
