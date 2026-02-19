# AGENTS.md - Æon Operational & Safety Guidelines

This document defines the **Deterministic Boundary** for all Æon agents. It serves as the bridge between stochastic reasoning (System 1) and executive control (System 2).

## Technical Standards (Engineering Rigor)
- **Typing:** Strict adherence to `StrictTypeHints` using Pydantic V2 for all tool parameters.
- **Memory:** Every state transition must be committed to the `EventStore` (Event Sourcing) before execution.
- **Verification:** All tools must implement a `pre_flight_check()` to allow Axiom interception.

## Operational Constraints (The Immutable Axioms)
1. **System Integrity:**
   - **Forbidden:** Destructive shell commands (e.g., `rm -rf`, `mkfs`, `dd` on system partitions) are globally blocked.
   - **Isolation:** Filesystem operations are restricted to `~/.aeon/workspace` unless `TrustLevel.FULL` is verified.
2. **Safety Intercepts:**
   - High-risk operations require **Human-in-the-Loop (HITL)** approval via the `Gatekeeper` module.
   - **Temporal Guard:** No automated system changes allowed between 00:00 and 04:00 (Local Time) without a redundant `ActivityAxiom`.

## Core Identity (Soul & Context)
- **Identity Hash:** Agents must verify their hash against `SOUL.md` at every initialization.
- **Situational Awareness:** Every reasoning loop must be injected with `SituationalContext` (Timestamp, Location, System Health).
- **Identity Consistency:** Actions must never deviate from the "Primary Directive" defined in the agent's manifest.

## Capability Protocol (L2/L5)
- **macOS Native:** Direct interaction with Reminders, Notes, and Safari must use the `MacOSTool` (AppleScript Bridge).
- **Browser Sovereignty:** All Playwright automation must run in sandboxed, ephemeral profiles.
- **Inter-Agent (A2A):** Communication must use **L1 Packet Protocols** with cryptographic signatures and formal "Hiring" cycles.

## Lifecycle Commands
- **Bootstrap:** `aeon init --safety-check`
- **Audit:** `aeon verify --master`
- **Production:** `aeon serve --trust-level RESTRICTED --port 8000`