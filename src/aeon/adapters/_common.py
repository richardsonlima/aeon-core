"""Shared helpers for the framework adapters (no SDK imports)."""

from __future__ import annotations

import inspect
import json
import logging
import types
import typing
from collections.abc import Callable, Mapping
from typing import Any

from aeon.axioms import ActionBlocked

logger = logging.getLogger(__name__)

_JSON_TYPES: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    tuple: "array",
    set: "array",
    dict: "object",
}


def get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a mapping or an attribute, so SDK objects and dicts both work."""
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def blocked_message(exc: ActionBlocked) -> str:
    d = exc.decision
    why = "; ".join(d.reasons) or d.gate_error or "blocked"
    return f"Æon blocked this action: {why}"


def as_text(result: Any) -> str:
    """Render a tool result for the model: strings as-is, everything else as JSON."""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, default=str)
    except (TypeError, ValueError):
        return str(result)


def parse_arguments(raw: Any) -> dict[str, Any]:
    """Decode tool-call arguments. Raises ``ValueError`` with a model-readable message."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid JSON arguments: {exc}") from None
    if not isinstance(value, dict):
        raise ValueError(f"arguments must be a JSON object, got {type(value).__name__}")
    return value


def _json_type(annotation: Any) -> dict[str, Any]:
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        options = [a for a in typing.get_args(annotation) if a is not type(None)]
        return _json_type(options[0]) if len(options) == 1 else {}
    if origin is typing.Literal:
        return {"enum": list(typing.get_args(annotation))}
    base = origin or annotation
    name = _JSON_TYPES.get(base)
    if name is None:
        return {}
    schema: dict[str, Any] = {"type": name}
    args = typing.get_args(annotation)
    if name == "array" and args and args[0] is not Ellipsis:
        item = _json_type(args[0])
        if item:
            schema["items"] = item
    return schema


def parameters_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """A JSON schema for ``fn``'s parameters, from its signature and type hints."""
    try:
        hints = typing.get_type_hints(fn)
    except Exception:  # unresolvable forward references: fall back to untyped params
        logger.debug("could not resolve type hints for %r", fn, exc_info=True)
        hints = {}
    properties: dict[str, Any] = {}
    required: list[str] = []
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        params = ()  # type: ignore[assignment]
    for p in params:
        if p.name in {"self", "cls"} or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        properties[p.name] = _json_type(hints.get(p.name, p.annotation))
        if p.default is inspect.Parameter.empty:
            required.append(p.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def description(fn: Callable[..., Any]) -> str:
    doc = inspect.getdoc(fn) or ""
    return doc.strip().splitlines()[0] if doc.strip() else ""


def total_tokens(usage: Any) -> int | None:
    """Total tokens from an SDK usage object, across the OpenAI and Anthropic shapes."""
    if usage is None:
        return None
    total = get(usage, "total_tokens")
    if isinstance(total, int):
        return total
    parts = [
        get(usage, k)
        for k in ("prompt_tokens", "completion_tokens", "input_tokens", "output_tokens")
    ]
    ints = [p for p in parts if isinstance(p, int)]
    return sum(ints) if ints else None
