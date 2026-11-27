"""Structured output: ask for JSON that matches a schema, then parse and validate it.

The schema comes from a dataclass, a Pydantic model (used only if you pass one; Pydantic
is not a dependency) or a JSON schema dict. The model is told to answer with only the
JSON object; the answer is parsed, fenced code is tolerated, and a failure raises
``ValueError`` with a message the agent sends back for one retry.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from typing import Any

from aeon.adapters._common import parameters_schema

__all__ = ["OutputSchema"]

_FENCE = re.compile(r"^```[a-zA-Z]*\s*(.*?)\s*```$", re.DOTALL)


@dataclass(frozen=True)
class OutputSchema:
    """A target type for the answer and its JSON schema."""

    target: Any
    json_schema: dict[str, Any]
    kind: str  # "pydantic", "dataclass" or "dict"

    @classmethod
    def of(cls, target: Any) -> OutputSchema:
        """Build from a Pydantic model class, a dataclass type, or a JSON schema dict."""
        if isinstance(target, dict):
            return cls(target, target, "dict")
        dump = getattr(target, "model_json_schema", None)
        if callable(dump):
            return cls(target, dict(dump()), "pydantic")
        if isinstance(target, type) and dataclasses.is_dataclass(target):
            return cls(target, parameters_schema(target), "dataclass")
        raise TypeError("output_schema must be a dataclass, a Pydantic model or a dict schema")

    def instruction(self) -> str:
        """The system instruction that asks for the JSON answer."""
        schema = json.dumps(self.json_schema, ensure_ascii=False)
        return (
            "When you give your final answer, reply with only a JSON object, no prose and "
            f"no code fence, that matches this JSON schema: {schema}"
        )

    def parse(self, text: str) -> Any:
        """Parse and validate the model's text.

        Raises:
            ValueError: The text is not JSON, or does not match the schema.
        """
        raw = text.strip()
        fenced = _FENCE.match(raw)
        if fenced:
            raw = fenced.group(1)
        try:
            value = json.loads(raw)
        except ValueError:
            raise ValueError("The answer was not valid JSON") from None
        if not isinstance(value, dict):
            raise ValueError("The answer was JSON but not an object")
        if self.kind == "pydantic":
            try:
                return self.target.model_validate(value)
            except Exception as exc:
                raise ValueError(f"The JSON did not match the schema: {exc}") from None
        missing = [k for k in self.json_schema.get("required", []) if k not in value]
        if missing:
            raise ValueError(f"The JSON is missing required fields: {', '.join(missing)}")
        if self.kind == "dataclass":
            names = {f.name for f in dataclasses.fields(self.target)}
            return self.target(**{k: v for k, v in value.items() if k in names})
        return value
