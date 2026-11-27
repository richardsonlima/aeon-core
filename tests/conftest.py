from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

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


# -- a local HTTP server standing in for an LLM provider --------------------


class _Handler(BaseHTTPRequestHandler):
    replies: ClassVar[list[tuple[int, bytes]]] = []
    seen: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        headers = {k.lower(): v for k, v in self.headers.items()}
        self.seen.append({"path": self.path, "headers": headers, "body": body})
        status, payload = self.replies.pop(0) if self.replies else (200, b"{}")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_: Any) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    _Handler.replies = []
    _Handler.seen = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _reply(status: int, obj: Any) -> tuple[int, bytes]:
    return status, json.dumps(obj).encode()
