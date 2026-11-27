"""A minimal MCP server over stdio, stdlib only.

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout. Logs go to stderr, never to
stdout, because stdout carries the protocol. ``JsonRpcServer`` is the small base that the
docs server (``aeon.docs_mcp``) reuses; ``McpServer`` exposes the gate.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import IO, Any

from aeon._version import __version__
from aeon.axioms import Gate
from aeon.config import Config
from aeon.runtime._common import (
    InvalidRequest,
    action_from,
    build_campaign,
    campaign_summary,
    readable_audit,
    status_doc,
)

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = (PROTOCOL_VERSION, "2025-03-26", "2024-11-05")

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
RESOURCE_NOT_FOUND = -32002


class ToolError(Exception):
    """An expected tool failure. It is reported to the caller as ``isError`` content."""


class RpcError(Exception):
    """A JSON-RPC protocol error to return to the caller."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ToolHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler
    input_schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def log(message: str) -> None:
    print(f"aeon-mcp: {message}", file=sys.stderr, flush=True)


class JsonRpcServer:
    """JSON-RPC 2.0 plumbing plus the MCP lifecycle and tool methods."""

    name = "aeon"
    version = __version__
    instructions: str | None = None

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._methods: dict[str, Callable[[dict[str, Any]], Any]] = {
            "initialize": self._initialize,
            "ping": lambda _p: {},
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
        }

    # -- registration (for subclasses) -------------------------------------------------

    def add_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def add_method(self, name: str, fn: Callable[[dict[str, Any]], Any]) -> None:
        self._methods[name] = fn

    def capabilities(self) -> dict[str, Any]:
        return {"tools": {"listChanged": False}}

    # -- dispatch ----------------------------------------------------------------------

    def handle(self, message: Any) -> dict[str, Any] | None:
        """Handle one decoded message. Returns the response, or ``None`` for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._error(None, INVALID_REQUEST, "invalid request")
        method = message.get("method")
        if "id" not in message:
            return None  # notification (notifications/initialized, cancelled, ...)
        req_id = message["id"]
        if isinstance(req_id, bool) or not isinstance(req_id, (str, int)):
            return self._error(None, INVALID_REQUEST, "id must be a string or an integer")
        if not isinstance(method, str):
            return self._error(req_id, INVALID_REQUEST, "missing method")
        params = message.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return self._error(req_id, INVALID_PARAMS, "params must be an object")
        fn = self._methods.get(method)
        if fn is None:
            return self._error(req_id, METHOD_NOT_FOUND, f"method not found: {method}")
        try:
            result = fn(params)
        except RpcError as exc:
            return self._error(req_id, exc.code, exc.message)
        except Exception as exc:  # never let a handler kill the server loop
            log(f"internal error in {method}: {exc!r}")
            return self._error(req_id, INTERNAL_ERROR, "internal error")
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def handle_line(self, line: str) -> dict[str, Any] | None:
        try:
            message = json.loads(line)
        except ValueError:
            return self._error(None, PARSE_ERROR, "parse error")
        return self.handle(message)

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    # -- MCP methods -------------------------------------------------------------------

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_VERSIONS else PROTOCOL_VERSION
        result: dict[str, Any] = {
            "protocolVersion": version,
            "capabilities": self.capabilities(),
            "serverInfo": {"name": self.name, "version": self.version},
        }
        if self.instructions:
            result["instructions"] = self.instructions
        return result

    def _tools_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"tools": [t.describe() for t in self._tools.values()]}

    def _tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            raise RpcError(INVALID_PARAMS, f"unknown tool: {name!r}")
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise RpcError(INVALID_PARAMS, "arguments must be an object")
        try:
            result = tool.handler(arguments)
        except (ToolError, InvalidRequest) as exc:
            return self._tool_result({"error": str(exc)}, is_error=True, text=str(exc))
        except Exception as exc:
            log(f"tool {name} failed: {exc!r}")
            msg = f"tool failed: {type(exc).__name__}"
            return self._tool_result({"error": msg}, is_error=True, text=msg)
        return self._tool_result(result)

    @staticmethod
    def _tool_result(
        result: Any, *, is_error: bool = False, text: str | None = None
    ) -> dict[str, Any]:
        structured = result if isinstance(result, dict) else {"result": result}
        out: dict[str, Any] = {
            "content": [
                {
                    "type": "text",
                    "text": text if text is not None else json.dumps(result, default=str),
                }
            ],
            "structuredContent": json.loads(json.dumps(structured, default=str)),
        }
        if is_error:
            out["isError"] = True
        return out

    # -- transport ---------------------------------------------------------------------

    def serve_streams(self, stdin: IO[str], stdout: IO[str]) -> int:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            response = self.handle_line(line)
            if response is not None:
                stdout.write(json.dumps(response, default=str) + "\n")
                stdout.flush()
        return 0


# -- the gate as an MCP server ----------------------------------------------------------


def str_arg(args: Mapping[str, Any], key: str, default: str | None = None) -> str:
    value = args.get(key, default)
    if not isinstance(value, str) or not value:
        raise ToolError(f"'{key}' must be a non-empty string")
    return value


def _opt_int(args: Mapping[str, Any], key: str) -> int | None:
    value = args.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolError(f"'{key}' must be an integer")
    return value


class McpServer(JsonRpcServer):
    """Exposes a gate to coding agents: check an action, read status, verify the audit log."""

    name = "aeon"
    instructions = (
        "Æon gates agent actions. Call aeon_check_action before a risky action and honour "
        "the decision. This server never executes tools."
    )

    def __init__(self, gate: Gate | None = None, *, config: Config | None = None) -> None:
        super().__init__()
        from aeon.config import build_gate, load_config

        self.config = config or load_config()
        self.gate = gate if gate is not None else build_gate(self.config)
        obj = "object"
        self.add_tool(
            Tool(
                "aeon_check_action",
                "Ask the gate whether an action may run. Returns the decision record; "
                "the action is not executed.",
                self._check_action,
                {
                    "type": obj,
                    "properties": {
                        "tool": {"type": "string"},
                        "args": {"type": obj},
                        "agent": {"type": "string"},
                        "approved": {"type": "boolean"},
                    },
                    "required": ["tool"],
                },
            )
        )
        self.add_tool(
            Tool(
                "aeon_status",
                "Gate mode, kill switch, safe states, budget and audit health.",
                self._status,
            )
        )
        self.add_tool(
            Tool(
                "aeon_audit_verify",
                "Verify the hash chain of the audit log.",
                self._audit_verify,
                {"type": obj, "properties": {"expect_head": {"type": "string"}}},
            )
        )
        self.add_tool(
            Tool(
                "aeon_run_campaign",
                "Run a chaos campaign (a fault name or a campaign file name) against the "
                "simulated agent and return the summary, checks and unfavourable outcomes.",
                self._run_campaign,
                {
                    "type": obj,
                    "properties": {
                        "target": {"type": "string"},
                        "runs": {"type": "integer", "minimum": 1},
                        "controls": {"type": "integer", "minimum": 0},
                        "seed": {"type": "integer"},
                        "blast_radius": {"type": "string"},
                    },
                    "required": ["target"],
                },
            )
        )

    def _check_action(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_args = args.get("args", {})
        if not isinstance(raw_args, dict):
            raise ToolError("'args' must be an object")
        action = action_from(
            str_arg(args, "tool"),
            raw_args,
            str_arg(args, "agent", "default"),
            bool(args.get("approved", False)),
        )
        return self.gate.decide(action).to_record(include_args=self.gate.include_args)

    def _status(self, _args: dict[str, Any]) -> dict[str, Any]:
        return status_doc(self.gate)

    def _audit_verify(self, args: dict[str, Any]) -> dict[str, Any]:
        head = args.get("expect_head")
        if head is not None and not isinstance(head, str):
            raise ToolError("'expect_head' must be a string")
        audit = readable_audit(self.gate)
        return dict(audit.verify(head).to_dict())

    def _run_campaign(self, args: dict[str, Any]) -> dict[str, Any]:
        from aeon.chaos import run_campaign, save_result

        blast = args.get("blast_radius")
        if blast is not None and not isinstance(blast, str):
            raise ToolError("'blast_radius' must be a string")
        c = build_campaign(
            self.config,
            target=str_arg(args, "target"),
            runs=_opt_int(args, "runs"),
            controls=_opt_int(args, "controls"),
            seed=_opt_int(args, "seed"),
            blast_radius=blast,
        )
        doc = run_campaign(c, ceiling=self.config.max_blast_radius)
        path = save_result(doc)
        return {**campaign_summary(doc), "saved_to": str(path)}


def serve_stdio(config: str | None) -> int:
    """Run the gate MCP server on stdin/stdout until EOF."""
    from pathlib import Path

    from aeon.config import ConfigError, build_gate, load_config

    try:
        cfg = load_config(Path(config) if config else None)
        server = McpServer(build_gate(cfg), config=cfg)
    except ConfigError as exc:
        from aeon.cli.main import CLIError

        raise CLIError(str(exc), "check aeon.toml or pass --config") from None
    log(f"ready ({server.name} {server.version}, mode {server.gate.mode.value})")
    return server.serve_streams(sys.stdin, sys.stdout)
