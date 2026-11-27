from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from aeon.axioms import Gate, set_default_gate
from aeon.axioms._gate import _registry


class ListSink:
    """Synchronous audit sink for tests."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def emit(self, kind: str, data: Any) -> None:
        self.events.append((kind, dict(data)))

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [d for t, d in self.events if t == kind]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AEON_AUDIT", "off")
    for k in ("AEON_MODE", "AEON_CONFIG", "AEON_AXIOMS", "AEON_MAX_BLAST_RADIUS"):
        monkeypatch.delenv(k, raising=False)
    _registry.clear()
    set_default_gate(None)
    yield
    _registry.clear()
    set_default_gate(None)


@pytest.fixture
def sink() -> ListSink:
    return ListSink()


@pytest.fixture
def gate(sink: ListSink) -> Gate:
    return Gate(mode="enforce", audit=sink)
