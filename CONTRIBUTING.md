# Contributing

## Setup

```bash
git clone https://github.com/richardsonlima/aeon-core
cd aeon-core
uv sync --group dev --extra runtime   # installs from uv.lock
```

## Checks

```bash
uv run --no-sync pytest                 # full suite
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy --strict
pre-commit install                      # optional: runs ruff and file hygiene on commit
```

The core install must stay dependency-free. Optional features go behind an extra and are imported lazily.

## Docs

The docs toolchain needs Python 3.12 (the docs group is empty on older versions):

```bash
uv sync --python 3.12 --group docs --extra runtime
uv run python scripts/gen_reference.py   # regenerate reference and evidence pages
uv run mkdocs build --strict
```

## Branches and commits

- Branch names: `feature/<topic>` or `fix/<topic>`.
- Commits follow Conventional Commits: `feat(audit): ...`, `fix(gate): ...`, `docs: ...`, `ci: ...`.
- Keep commits small and focused. Do not rewrite shared history.

## Claims and evidence

Every claim in the docs, README or release notes needs an entry in `docs/claims.yaml` that points to the test, benchmark or campaign that supports it. If you cannot measure it, do not claim it.

Unfavourable results must be published. A failed hypothesis, a fault the gate did not contain or a benchmark that got slower goes into the report and into `docs/known-limits.md`. Do not delete or soften it.

## Pull requests

Fill in the pull request template. A new dependency needs a written justification.
