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

This replaces `.venv` with a Python 3.12 environment without the dev group. Run the setup `uv sync` again before you go back to the checks. To keep both, build the docs in a separate environment: `UV_PROJECT_ENVIRONMENT=.venv-docs uv sync --python 3.12 --group docs --extra runtime`, then `UV_PROJECT_ENVIRONMENT=.venv-docs uv run --no-sync mkdocs build --strict`.

## Run what CI runs

The checks above cover lint, types and unit tests. Before a pull request, also run the package smoke test and the dependency audit:

```bash
# build the wheel and sdist, and check their metadata
uv build && uvx twine check --strict dist/*

# install the wheel in a fresh venv and drive the CLI
W=$(mktemp -d) && uv venv "$W/venv" && uv pip install --python "$W/venv" dist/*.whl
mkdir "$W/p" && cp examples/quickstart/main.py "$W/p/" && cd "$W/p"
"$W/venv/bin/aeon" doctor && "$W/venv/bin/aeon" init && "$W/venv/bin/python" main.py \
  && "$W/venv/bin/aeon" audit verify
cd -

# known vulnerabilities in the locked dependencies, all extras
uv export --frozen --all-extras --no-emit-project --no-hashes -o /tmp/requirements-audit.txt
uvx pip-audit --strict -r /tmp/requirements-audit.txt
```

CI also runs [gitleaks](https://github.com/gitleaks/gitleaks) for secrets. Locally: `gitleaks git .` if you have it installed.

## Benchmarks

See [`benchmarks/README.md`](benchmarks/README.md). `python benchmarks/run_all.py --quick` is a smoke check. A full run overwrites the committed files in `benchmarks/results/` and `docs/claims.yaml`: commit them only when you mean to publish new numbers, otherwise restore them with `git checkout benchmarks/results docs/claims.yaml`.

## Run the runtime and the control plane

```bash
uv run --no-sync aeon init                # once, in a scratch directory
uv run --no-sync aeon ui                  # runtime on http://127.0.0.1:8787, opens /ui/
```

See [Runtime, control plane and Docker](docs/guides/runtime.md) for the token, remote access and the container.

## Branches and commits

- Branch names: `feature/<topic>` or `fix/<topic>`.
- Commits follow Conventional Commits: `feat(audit): ...`, `fix(gate): ...`, `docs: ...`, `ci: ...`.
- Keep commits small and focused. Do not rewrite shared history.

## Claims and evidence

Every claim in the docs, README or release notes needs an entry in `docs/claims.yaml` that points to the test, benchmark or campaign that supports it. If you cannot measure it, do not claim it.

Unfavourable results must be published. A failed hypothesis, a fault the gate did not contain or a benchmark that got slower goes into the report and into `docs/known-limits.md`. Do not delete or soften it.

## Pull requests

Fill in the pull request template. A new dependency needs a written justification.
