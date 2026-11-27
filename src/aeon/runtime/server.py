"""Run the control plane with uvicorn."""

from __future__ import annotations

import contextlib
import ipaddress
import os
import socket
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

DEFAULT_PORT = 8787


def _cli_error(message: str, hint: str | None = None) -> Exception:
    from aeon.cli.main import CLIError

    return CLIError(message, hint)


def is_loopback(host: str) -> bool:
    """Whether ``host`` is ``localhost`` or a loopback IP address."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def check_bind_host(host: str) -> None:
    """Refuse a non-loopback bind unless ``AEON_RUNTIME_ALLOW_REMOTE=1``."""
    if is_loopback(host) or os.environ.get("AEON_RUNTIME_ALLOW_REMOTE") == "1":
        return
    raise _cli_error(
        f"refusing to bind {host!r}: the runtime has no TLS and is meant for loopback only",
        "use --host 127.0.0.1, or set AEON_RUNTIME_ALLOW_REMOTE=1 and put it behind a "
        "TLS proxy you control",
    )


def _check_port_free(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError as exc:
            raise _cli_error(
                f"cannot listen on {host}:{port}: {exc.strerror or exc}",
                "pick another port with --port, or stop the process using it",
            ) from None


def _open_when_ready(host: str, port: int, url: str) -> None:
    def run() -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with contextlib.suppress(OSError), socket.create_connection((host, port), 0.5):
                with contextlib.suppress(Exception):
                    webbrowser.open(url)
                return
            time.sleep(0.1)

    threading.Thread(target=run, name="aeon-open-ui", daemon=True).start()


def serve(host: str, port: int, config: str | None, open_ui: bool) -> int:
    """Serve the control plane until interrupted. Errors become ``CLIError`` with a hint."""
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    from aeon.config import ConfigError, load_config
    from aeon.runtime.app import create_app, resolve_token

    check_bind_host(host)
    try:
        cfg = load_config(Path(config) if config else None)
    except ConfigError as exc:
        raise _cli_error(str(exc), "check aeon.toml or pass --config") from None
    _check_port_free(host, port)
    token, where = resolve_token(None, cfg.root)
    try:
        app = create_app(config=cfg, token=token)
    except ConfigError as exc:
        raise _cli_error(str(exc), "check the axiom files listed in aeon.toml") from None
    if not is_loopback(host):
        print("warning: bound to a non-loopback address; traffic is plain HTTP", flush=True)
    else:  # DNS rebinding guard: only loopback host names may address the runtime
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "::1"]
        )

    shown = f"[{host}]" if ":" in host else host
    base = f"http://{shown}:{port}"
    print(f"aeon runtime listening on {base}", flush=True)
    print(f"mode {app.state.gate.mode.value}; bearer token in {where}", flush=True)
    if open_ui:
        _open_when_ready(host, port, f"{base}/ui/#token={token}")

    server_config: Any = uvicorn.Config(app, host=host, port=port, log_level="warning")
    try:
        uvicorn.Server(server_config).run()
    except OSError as exc:
        raise _cli_error(
            f"runtime stopped: {exc.strerror or exc}", "check the host and port"
        ) from None
    return 0
