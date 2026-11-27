"""Small helpers shared by the decision and observation paths. Stdlib only."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from collections.abc import Mapping
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, non-JSON values stringified."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest(obj: Any) -> str:
    """sha256 of the canonical JSON form of ``obj``."""
    return sha256_hex(canonical_json(obj))


def new_id() -> str:
    return uuid.uuid4().hex


def utc_now_iso() -> str:
    """Wall-clock UTC timestamp with millisecond precision. Used for display, never for ordering."""
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int((t % 1) * 1000):03d}Z"


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def freeze(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping) if mapping else {}
