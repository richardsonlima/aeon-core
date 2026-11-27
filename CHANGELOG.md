# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow [Semantic Versioning](https://semver.org/) once it has a stable release.

## [Unreleased]

The v0.5.0 rewrite. Nothing is published yet: there is no PyPI release and no tag for 0.5.0. The previous code is kept at tag `v0.4.0-ULTRA`.

### Added

- `aeon.axioms`: `@axiom`, `enforce`, `Gate`, the autonomy levels `GO`, `ALERT`, `LIMIT` and `BLOCK`, per-agent Safe State, a kill-switch, and shadow mode as the default. The gate fails safe: an axiom or gate error blocks the action in enforce mode and is recorded in shadow mode. No third-party dependencies.
- `aeon.axioms.builtin`: `deny_tools`, `allow_tools`, `rate_limit`, `deny_arg_pattern` and `require_approval`.
- `aeon.baseline`: per-agent behavioural baseline, clipped one-sided z-scores, Jensen-Shannon tool drift, a CUSUM accumulator, and an absolute envelope (`p99_ms`, `error_rate`, `max_cost`, `max_tokens`). `ChaosBudget` is an alias of `Budget`.
- `aeon.audit`: append-only, hash-chained audit log written off the decision path, with JSONL, SQLite and in-memory backends, `audit.gap` and `audit.backend_error` records, and `aeon audit verify|tail|export`.
- `aeon.chaos`: a catalog of eight faults with a blast-radius guard (`dev`, `staging`, `prod-shadow`), pre-registered TOML campaigns with control runs and Wilson intervals, a simulated `ops-assistant` scenario, and `aeon chaos list|run` and `aeon report`. Nine campaigns ship in `campaigns/`.
- `aeon.adapters`: `ToolBox` for plain Python, and helpers for OpenAI (Chat Completions and Responses), Anthropic Messages and LangGraph tools. The adapters import no SDK.
- `aeon` command: `init`, `doctor`, `axioms list|check`, `run`, `chaos`, `report`, `audit`, `runtime start` (alias `serve`), `runtime mcp`, `ui`, `docs mcp` and `version`. Every data command accepts `--json`.
- Configuration through `aeon.toml` (or `[tool.aeon]`) and `AEON_*` variables.
- A local HTTP runtime (FastAPI, extra `runtime`) with bearer-token auth, loopback-only binding, a Host allowlist, a decision stream and a static control plane UI. An MCP server over stdio for the gate (`aeon_check_action`, `aeon_status`, `aeon_audit_verify`, `aeon_run_campaign`) and one for these docs.
- A Dockerfile and `compose.yaml` (built locally, not published).
- Benchmarks (`benchmarks/`, `python benchmarks/run_all.py`) with committed results, and `docs/claims.yaml` generated from tests and results with a `specified`, `implemented`, `measured` status ladder.
- A test suite, CI, and documentation in English and Brazilian Portuguese: concepts, guides, reference, a knowledge base, known limits, a security page, an audit of v0.4, architecture decision records, draft blog posts and `llms.txt`.

### Changed

- The package is a rewrite with a different purpose: gating the actions of LLM agents and checking that they fail safe, not a general assistant framework. See `docs/decisions/001-rewrite-v0.5.md`.
- Python 3.10 or newer (v0.4 declared 3.9 and documented 3.10).
- The core install has no third-party dependencies (`tomli` on Python 3.10 only). FastAPI and uvicorn are in the `runtime` extra, and provider SDKs are optional extras.
- `aeon` is now an installed console script (v0.4 had no `[project.scripts]` entry). The command line uses the standard library only.
- Configuration is `aeon.toml`, not `aeon.yaml`.
- The README and docs no longer use "production-ready" or certification wording.

### Removed

- The v0.4 subpackages: `automation`, `cache`, `core`, `cortex`, `dialogue`, `dispatcher`, `economics`, `executive`, `extensions`, `gateway`, `health`, `hive`, `integrations`, `memory`, `observability`, `routing`, `security`, `synapse` and `tools`, and the old `axioms`, `cli` and `runtime` subpackages (the new package reuses those three names for different code), together with the `aeon.Agent` API, the Typer `init`, `run` and `serve` commands, the `aeon.yaml` loader, the Playwright browser automation and the SQLite event-sourced memory.
- The legacy top-level documents and example folders, including printed claims of SIL, DO-178C or IEC 61508 certification that had no basis.
- **If you use any of the above, pin `aeon-core==0.4.0`.** The code stays available at tag `v0.4.0-ULTRA`.

### Known issues

See `docs/known-limits.md`. Highlights: the default budget raised false positives in up to 70% of clean control runs on the simulated agent, so eight of nine pre-registered campaigns did not meet their hypothesis; the audit queue dropped 2,081 of 50,000 events in a burst test; there is no audit signing and no Postgres backend; and all campaign results come from a scripted simulated agent, not an LLM.

## [0.4.0-ULTRA] - 2026-02-18

Tag `v0.4.0-ULTRA`. Autonomous native engine: browser automation, persistent event-sourced memory, trust levels, the `aeon` CLI built with Typer, a declarative `aeon.yaml` runtime and a gateway server. No tests existed at this version (see `docs/audit.md`).

## [0.3.0-ULTRA] - 2026-02-13

Tag `v0.3.0-ULTRA`. Routing, gateway, security and health layers.

## [0.2.0-alpha] - 2026-02-05

Tag `v0.2.0-alpha`.

## [0.1.0] - 2026-02-05

Tag `v0.1.0`. First tagged version.

[Unreleased]: https://github.com/richardsonlima/aeon-core/compare/v0.4.0-ULTRA...HEAD
[0.4.0-ULTRA]: https://github.com/richardsonlima/aeon-core/releases/tag/v0.4.0-ULTRA
[0.3.0-ULTRA]: https://github.com/richardsonlima/aeon-core/releases/tag/v0.3.0-ULTRA
[0.2.0-alpha]: https://github.com/richardsonlima/aeon-core/releases/tag/v0.2.0-alpha
[0.1.0]: https://github.com/richardsonlima/aeon-core/releases/tag/v0.1.0
