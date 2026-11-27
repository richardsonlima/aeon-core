# Audit of aeon-core before the v0.5.0 rewrite

Date: 2026-11-27. Audited commit: `b6c8706` (branch `develop`, same tree as tag `v0.4.0-ULTRA` plus merges).

## What exists

| Area | State at `b6c8706` |
|---|---|
| Package | `src/aeon/`, 90 files, about 7,250 lines of Python across 25 subpackages (`core`, `executive`, `routing`, `gateway`, `security`, `health`, `cache`, `hive`, `memory`, `tools`, `cortex`, `economics`, ...). |
| Packaging | `pyproject.toml` with hatchling, version `0.4.0`, `requires-python >=3.9` while the classifiers and README say 3.10+. |
| Runtime dependencies | 17 hard dependencies in the core install, including `openai`, `playwright`, `fastapi`, `uvicorn`, `sqlalchemy`, `beautifulsoup4`. |
| CLI | `src/aeon/cli/main.py` (Typer) with `init`, `run`, `serve`. **No `[project.scripts]` entry**, so `aeon` is not installed: `uv run aeon --help` fails with `Failed to spawn: aeon`. |
| Tests | **None.** There is no `tests/` directory. The `examples/verify_*.py` scripts print results but assert nothing that CI runs. |
| CI | One workflow, `publish-pypi.yml`, that publishes on any `v*` tag. It runs no tests, no lint, no type check, and it uses `actions/setup-python@v4`. |
| Docs | Seven top-level markdown files (`README.md`, `ARCHITECTURE.md`, `ULTRA.md`, `INTEGRATION.md`, `AI_ASSISTANT.md`, `DESIGN_INDEPENDENCE.md`, `QUICK_START.md`). `README.md` links to a `README_pt.md` that does not exist. No CHANGELOG, although the publish workflow links to one. |
| License | Apache-2.0 (`LICENSE`). Kept. |
| Repository hygiene | `.DS_Store`, runtime checkpoint JSON files (`src/aeon/core/vault/checkpoints/*.json`) and personal assistant notes (`.aeon/user.md`, `.aeon/facts.md`) are committed. |

## What works (run on 2026-11-27, macOS arm64, Python 3.10.21 via uv)

- `import aeon` succeeds.
- `uv run aeon --help` fails: there is no console script.
- No test suite exists, so nothing else can be called "working" with evidence.

## What is missing compared to the target product

Everything the v0.5.0 brief defines as the core is absent or different:

- `aeon.axioms.axiom` and `aeon.axioms.enforce` (documented on the public site) do not exist. The closest code is `aeon.executive.safety.ExecutiveRegistry`, which validates LLM *output* dicts, prints to stdout and has no levels, no Safe State, no shadow mode and no fail-closed behaviour.
- No autonomy levels (ALERT / LIMIT / BLOCK), no kill-switch, no shadow mode.
- No behavioural baseline, deviation score or budget.
- No fault catalog, blast radius or campaigns (`aeon chaos run` is shown on the site but not implemented).
- No hash-chained audit log and no `aeon audit verify` (shown on the site, not implemented). `memory/events.py` is an event store without hash chaining.
- No `aeon doctor`, no benchmarks, no `claims.yaml`, no known-limits page.

## What contradicts the honesty rules

| Location | Claim | Problem |
|---|---|---|
| `README.md` | "production-ready framework", "Improved SIL-4 compliant axioms with TMR" | No tests, no evidence, certification language. |
| `examples_industrial_critical/*.py` | "SIL 3/4 certified", "DO-178C Level A Certification", "formally verified", "IEC 61508:2010 SIL 4 CERTIFIED" printed at runtime | Certification claims with no basis. |
| `ULTRA.md`, `INTEGRATION.md`, `AI_ASSISTANT.md`, `DESIGN_INDEPENDENCE.md` | "Production-Ready", "Feature complete" | No tests. |
| Public site `docs.dc.html` | `@axiom(on_violation="BLOCK", response_time_ms=0.1)` | A 0.1 ms figure with no committed measurement. |
| Public site `docs.dc.html` | audit line `sig=ed25519:ok` | No signing existed in the code. |
| Public site `docs.dc.html` | `from aeon import Agent, ChaosBudget` quickstart | `ChaosBudget` did not exist. |

In total, `grep` finds 22 lines in the repository with certification or "production-ready" language.

## Decisions taken in this audit

1. **Rewrite, do not refactor in place** (ADR [001](decisions/001-rewrite-v0.5.md)). The existing modules solve a different problem (a general assistant framework) and pull heavy dependencies into the core. The brief requires a dependency-free core. The v0.4.0 code stays available at tag `v0.4.0-ULTRA`; nothing is deleted from history.
2. **Public site conflicts are kept out of scope for code.** The brief forbids editing `aeon/` on the site without review. The code adopts the names the site shows (`axiom`, `enforce`, `on_violation`, `action.tool`, `action.approved`, `aeon chaos run`, `aeon audit verify`, `aeon doctor`, `ChaosBudget(p99_ms=..., error_rate=...)`, `aeon serve` as an alias of `aeon runtime start`). The site changes needed (remove `response_time_ms=0.1` until measured, remove `sig=ed25519`, drop `Agent` from the quickstart) are listed in [`site-changes.md`](site-changes.md) for review.
3. **Existing decision kept, with a conflict noted:** the site calls the axiom engine "aeon-axioms, a standalone module". In v0.5.0 it is the `aeon.axioms` subpackage of `aeon-core`, which has no dependencies, so importing it alone already has that effect. A separate distribution is not built.

## Plan

The phases of the brief, executed on branch `feature/v0.5.0`:

1. Foundation: packaging (hatchling, `src/` layout, extras), CI, `aeon doctor`, `aeon version`.
2. Gate: axioms, `enforce`, levels, Safe State, kill-switch, shadow mode.
3. Audit chain: hash chain, JSONL and SQLite backends, `aeon audit tail|verify|export`.
4. Baseline and budget.
5. Chaos: fault catalog, blast radius, campaigns, `aeon chaos`, `aeon report`.
6. Adapters and examples (plain Python, OpenAI, Anthropic, LangGraph) with fake models.
7. Benchmarks and claims.
8. Runtime: FastAPI, MCP, Docker.
9. Control Plane.
10. Docs, KB, changelog, blog, `llms.txt`, docs over MCP, EN/PT.
11. Release readiness: wheel smoke tests, trusted publishing, SBOM, `RELEASE.md`.
