"""Minimal HTTP clients for LLM provider APIs, standard library only.

They mirror the call shape of the official SDKs (``client.chat.completions.create`` and
``client.messages.create``) and return plain dicts, so the adapters and
:class:`aeon.agents.Agent` treat them like the SDK objects. Use the official SDKs instead
whenever you can install them; these exist so the core install can reach a model with no
third-party package.

``OpenAICompatible`` speaks the Chat Completions API, which OpenAI, OpenRouter, Groq,
Together, vLLM, LM Studio and Ollama (``http://localhost:11434/v1``) all serve.
``AnthropicClient`` speaks the Anthropic Messages API.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

__all__ = ["AnthropicClient", "OpenAICompatible", "ProviderError"]

DEFAULT_TIMEOUT = 120.0
OPENROUTER_URL = "https://openrouter.ai/api/v1"


class ProviderError(RuntimeError):
    """The provider answered with an error, or could not be reached.

    Attributes:
        status: HTTP status code, or ``None`` when no response arrived.
        body: The start of the response body, for diagnosis. Never holds the API key.
    """

    def __init__(self, message: str, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _check_url(url: str) -> str:
    scheme = urlparse(url).scheme
    if scheme not in ("http", "https"):
        raise ValueError(f"base_url must be http:// or https://, got {url!r}")
    return url.rstrip("/")


def post_json(
    url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout: float
) -> dict[str, Any]:
    """POST ``payload`` as JSON and decode the JSON reply.

    Raises:
        ProviderError: On an HTTP error status, a network error or a non-JSON reply.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 - scheme checked by _check_url
        url, data=data, method="POST", headers={"content-type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        detail = " ".join(body.split())[:200]
        raise ProviderError(f"{url} returned HTTP {exc.code}: {detail}", exc.code, body) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ProviderError(f"could not reach {url}: {reason}") from None
    try:
        value = json.loads(raw)
    except ValueError:
        raise ProviderError(
            f"{url} did not return JSON", body=raw[:500].decode("utf-8", "replace")
        ) from None
    if not isinstance(value, dict):
        raise ProviderError(f"{url} returned JSON that is not an object")
    return value


class _Endpoint:
    def __init__(self, url: str, headers: dict[str, str], timeout: float) -> None:
        self._url = url
        self._headers = headers
        self._timeout = timeout

    def create(self, **request: Any) -> dict[str, Any]:
        """Send one request. Keyword arguments are the API's request fields."""
        body = {k: v for k, v in request.items() if v is not None}
        return post_json(self._url, body, self._headers, self._timeout)


class _Chat:
    def __init__(self, completions: _Endpoint) -> None:
        self.completions = completions


class OpenAICompatible:
    """Client for any Chat Completions endpoint.

    Args:
        base_url: The API root, for example ``https://api.openai.com/v1``,
            ``https://openrouter.ai/api/v1`` or ``http://localhost:11434/v1``.
        api_key: Bearer token. Defaults to ``$OPENAI_API_KEY``; local servers such as
            Ollama need none.
        timeout: Seconds per request.
        headers: Extra headers, for example OpenRouter's ``HTTP-Referer``.

    Example:
        >>> client = OpenAICompatible("http://localhost:11434/v1")  # doctest: +SKIP
        >>> client.chat.completions.create(model="qwen2.5:3b", messages=[...])  # doctest: +SKIP
    """

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = _check_url(base_url)
        key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        hdrs = dict(headers or {})
        if key:
            hdrs["authorization"] = f"Bearer {key}"
        self.chat = _Chat(_Endpoint(f"{self.base_url}/chat/completions", hdrs, timeout))

    @classmethod
    def openrouter(
        cls, api_key: str | None = None, *, timeout: float = DEFAULT_TIMEOUT
    ) -> OpenAICompatible:
        """A client for OpenRouter. The key defaults to ``$OPENROUTER_API_KEY``.

        Raises:
            ValueError: When no API key is given or set in the environment.
        """
        key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("no API key: pass api_key or set OPENROUTER_API_KEY")
        return cls(OPENROUTER_URL, key, timeout=timeout, headers={"x-title": "aeon-core"})

    def __repr__(self) -> str:
        return f"OpenAICompatible({self.base_url!r})"


class AnthropicClient:
    """Client for the Anthropic Messages API.

    Args:
        api_key: Defaults to ``$ANTHROPIC_API_KEY``.
        base_url: The API root.
        version: Value of the ``anthropic-version`` header.
        timeout: Seconds per request.
        headers: Extra headers. Gateways that serve the Messages API with bearer auth,
            such as OpenRouter (``base_url="https://openrouter.ai/api"``), need
            ``{"authorization": f"Bearer {key}"}``.

    Raises:
        ValueError: When no API key is given or set in the environment.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.anthropic.com",
        version: str = "2023-06-01",
        timeout: float = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("no API key: pass api_key or set ANTHROPIC_API_KEY")
        self.base_url = _check_url(base_url)
        hdrs = {"x-api-key": key, "anthropic-version": version, **(headers or {})}
        self.messages = _Endpoint(f"{self.base_url}/v1/messages", hdrs, timeout)

    def __repr__(self) -> str:
        return f"AnthropicClient({self.base_url!r})"
