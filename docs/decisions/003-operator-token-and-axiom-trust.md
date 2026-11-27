# 003. One operator token; axiom files are trusted code

- Status: accepted
- Date: 2026-11-27

## Context

A security review of the runtime found two design-level points:

1. The single bearer token allows both asking for decisions (`/v1/actions/evaluate`) and
   changing the gate (`/v1/mode`, `/v1/kill-switch`, `/v1/policies`, Safe State reset). An
   agent holding the token could switch its own gate to shadow.
2. Axiom files listed in `aeon.toml` are imported as Python. Starting the runtime or the MCP
   server inside an untrusted checkout runs that checkout's code, like a Makefile would.

## Decision

- The token is an **operator** credential. Agents must not receive it; an agent process
  that needs decisions should use the library (`enforce`) in-process. This is stated in
  `docs/security.md`.
- `aeon runtime start` and `aeon runtime mcp` print the resolved path of every axiom file at
  startup, so the operator sees what code is loaded.
- A separate, decision-only token and a trust prompt for configs discovered by walking up
  from the working directory are on the roadmap, not implemented.

## Consequences

Simple setup stays simple. The risk is documented rather than removed, and it is listed in
`docs/known-limits.md`.
