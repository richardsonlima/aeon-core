"""Serve the project documentation to coding agents over MCP (stdio).

Resources: every ``.md`` file under the docs directory, as ``aeon-docs://<relative path>``.
Tools: ``search_docs`` (case-insensitive term scoring) and ``read_doc``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import IO, Any

from aeon.runtime.mcp import (
    INVALID_PARAMS,
    RESOURCE_NOT_FOUND,
    JsonRpcServer,
    RpcError,
    Tool,
    ToolError,
    log,
    str_arg,
)

URI_PREFIX = "aeon-docs://"
MAX_FILES = 2000
MAX_BYTES = 1024 * 1024
_WORD = re.compile(r"\w+", re.UNICODE)


def default_docs_dir() -> Path:
    """Repo ``docs/`` in an editable install, else the bundled ``aeon/_docs/``."""
    here = Path(__file__).resolve()
    repo = here.parents[2]
    if (repo / "pyproject.toml").is_file() and (repo / "docs").is_dir():
        return repo / "docs"
    return here.parent / "_docs"


class DocsServer(JsonRpcServer):
    """MCP server exposing the Markdown docs as searchable, readable resources."""

    name = "aeon-docs"
    instructions = "Search and read the Æon documentation."

    def __init__(self, docs_dir: Path) -> None:
        super().__init__()
        self.root = docs_dir.resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"docs directory not found: {docs_dir}")
        self.add_method("resources/list", self._resources_list)
        self.add_method("resources/read", self._resources_read)
        self.add_tool(
            Tool(
                "search_docs",
                "Search the docs. Returns path, title and a snippet for the best matches.",
                self._search,
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": ["query"],
                },
            )
        )
        self.add_tool(
            Tool(
                "read_doc",
                "Read one markdown document by its relative path.",
                self._read,
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            )
        )

    def capabilities(self) -> dict[str, Any]:
        """Advertise the tools and resources this server provides."""
        return {"tools": {"listChanged": False}, "resources": {"listChanged": False}}

    # -- files -------------------------------------------------------------------------

    def files(self) -> list[Path]:
        """Return the Markdown files under the docs root, at most ``MAX_FILES``."""
        out: list[Path] = []
        for p in sorted(self.root.rglob("*.md")):
            if len(out) >= MAX_FILES:
                break
            if p.is_file() and self._inside(p):
                out.append(p)
        return out

    def _inside(self, p: Path) -> bool:
        try:
            return p.resolve().is_relative_to(self.root)
        except OSError:
            return False

    def rel(self, p: Path) -> str:
        """Return ``p`` as a POSIX path relative to the docs root."""
        return p.resolve().relative_to(self.root).as_posix()

    def resolve(self, path: str) -> Path:
        """Map a relative path (or an ``aeon-docs://`` uri) to a file, or raise ``ValueError``."""
        raw = path.removeprefix(URI_PREFIX)
        if (
            not raw
            or "\x00" in raw
            or "\\" in raw
            or raw.startswith("/")
            or re.match(r"^[A-Za-z]:", raw)
            or ".." in raw.split("/")
        ):
            raise ValueError(f"invalid doc path: {path!r}")
        target = (self.root / raw).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"invalid doc path: {path!r}")
        if target.suffix.lower() != ".md":
            raise ValueError("only .md documents can be read")
        if not target.is_file():
            raise FileNotFoundError(f"no such document: {raw}")
        return target

    def text(self, p: Path) -> str:
        """Read up to ``MAX_BYTES`` of ``p`` as UTF-8, replacing undecodable bytes."""
        with p.open("rb") as fh:
            return fh.read(MAX_BYTES).decode("utf-8", errors="replace")

    @staticmethod
    def title_of(body: str, fallback: str) -> str:
        """Return the first ``# `` heading in ``body``, or ``fallback`` if there is none."""
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip() or fallback
        return fallback

    # -- resources ---------------------------------------------------------------------

    def _resources_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        items = []
        for p in self.files():
            rel = self.rel(p)
            items.append(
                {
                    "uri": URI_PREFIX + rel,
                    "name": rel,
                    "title": self.title_of(self.text(p), p.stem),
                    "mimeType": "text/markdown",
                }
            )
        return {"resources": items}

    def _resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri.startswith(URI_PREFIX):
            raise RpcError(INVALID_PARAMS, f"uri must start with {URI_PREFIX}")
        try:
            p = self.resolve(uri)
        except FileNotFoundError:
            raise RpcError(RESOURCE_NOT_FOUND, f"resource not found: {uri}") from None
        except ValueError as exc:
            raise RpcError(INVALID_PARAMS, str(exc)) from None
        return {
            "contents": [
                {"uri": URI_PREFIX + self.rel(p), "mimeType": "text/markdown", "text": self.text(p)}
            ]
        }

    # -- tools -------------------------------------------------------------------------

    def _read(self, args: dict[str, Any]) -> dict[str, Any]:
        try:
            p = self.resolve(str_arg(args, "path"))
        except (ValueError, FileNotFoundError) as exc:
            raise ToolError(str(exc)) from None
        body = self.text(p)
        return {"path": self.rel(p), "title": self.title_of(body, p.stem), "text": body}

    def _search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str_arg(args, "query")
        limit = args.get("limit", 5)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ToolError("'limit' must be a positive integer")
        limit = min(limit, 20)
        terms = sorted({t.lower() for t in _WORD.findall(query)})
        if not terms:
            raise ToolError("query has no searchable terms")
        hits: list[tuple[int, str, dict[str, Any]]] = []
        for p in self.files():
            body = self.text(p)
            rel = self.rel(p)
            title = self.title_of(body, p.stem)
            low, low_title, low_rel = body.lower(), title.lower(), rel.lower()
            score = sum(low.count(t) + 5 * low_title.count(t) + 3 * low_rel.count(t) for t in terms)
            if score:
                hits.append(
                    (
                        score,
                        rel,
                        {
                            "path": rel,
                            "title": title,
                            "score": score,
                            "snippet": self._snippet(body, terms),
                        },
                    )
                )
        hits.sort(key=lambda h: (-h[0], h[1]))
        return {"query": query, "results": [h[2] for h in hits[:limit]]}

    @staticmethod
    def _snippet(body: str, terms: list[str]) -> str:
        """The body line that matches the most terms, preferring prose over headings."""
        best, best_key = "", (0, 0)
        for line in body.splitlines():
            low = line.lower()
            hits = sum(1 for t in terms if t in low)
            key = (hits, 0 if line.startswith("#") else 1)
            if hits and key > best_key:
                best, best_key = line.strip(), key
        if len(best) > 240:
            low = best.lower()
            i = min((low.find(t) for t in terms if t in low), default=0)
            start = max(0, i - 80)
            best = ("..." if start else "") + best[start : start + 240] + "..."
        return best


def serve_docs(
    docs_dir: str | None, stdin: IO[str] | None = None, stdout: IO[str] | None = None
) -> int:
    """Run the docs MCP server on stdin/stdout until EOF."""
    import sys

    from aeon.cli.main import CLIError

    path = Path(docs_dir) if docs_dir else default_docs_dir()
    if not path.is_dir():
        if docs_dir:
            raise CLIError(f"docs directory not found: {path}", "pass an existing --docs-dir")
        raise CLIError(
            "no documentation is bundled with this install",
            "pass --docs-dir <path>, or run from a source checkout that has docs/",
        )
    server = DocsServer(path)
    log(f"serving docs from {server.root}")
    return server.serve_streams(stdin or sys.stdin, stdout or sys.stdout)
