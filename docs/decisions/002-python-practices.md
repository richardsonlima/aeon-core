# 002. Python development practices

- Status: accepted
- Date: 2026-11-27

## Context

I follow the practices taught in my Python course (portal-python): src layout, a lockfile,
development tools in dependency groups, ruff with a curated rule set, mypy strict, a coverage
floor, dependency and secret scanning, loggers in libraries, no silent `except`.

## Decision

- Dev and docs tools live in `[dependency-groups]`; `uv.lock` is committed and CI installs
  with `uv sync --locked`. Published extras (`runtime`, `openai`, ...) stay extras.
- Ruff selects `E F W I N A B C90 D UP SIM RUF S PT`, max complexity 10, Google docstrings.
  Ruff and mypy are pinned to the same versions in the dev group and in pre-commit.
- mypy strict plus `warn_unreachable` and the `truthy-bool`, `ignore-without-code` and
  `redundant-expr` error codes.
- Coverage floor of 88% (measured 91% branch coverage on 2026-11-27), enforced in the CI job
  that has the runtime extra installed.
- CI runs `pip-audit` on the locked dependencies and gitleaks; pre-commit runs gitleaks too.
- The library only creates loggers (`logging.getLogger(__name__)`) and attaches a
  `NullHandler` to `aeon`. Broad `except Exception` exists only at fail-safe boundaries
  (gate, audit writer, MCP loop, CLI) and always counts and logs the error.

## Deviations from the course, kept on purpose

- Python 3.10+ is supported, so PEP 695 syntax is not used.
- The core has no third-party dependencies (no pydantic, httpx, tenacity), and the CLI uses
  argparse.
- The version comes from `src/aeon/_version.py` through hatch, still a single source.
- Exception names such as `ActionBlocked`, `ToolTimeout` and `RateLimited` keep their public
  names without an `Error` suffix (ruff N818 ignored): they name events the caller handles.
