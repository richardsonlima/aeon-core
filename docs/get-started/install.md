# Install

Requires Python 3.10 or newer. The core has no third-party dependencies (on 3.10 only, `tomli`).

## From PyPI

```bash
pip install aeon-core
pip install "aeon-core[runtime]"      # plus the HTTP runtime
uv add aeon-core                      # in a project
uvx --from aeon-core aeon version     # no install
pipx install aeon-core                # as a command-line tool
```

The 0.3.0 and 0.4.0 releases on PyPI are the old code line. 0.5.0 is a rewrite with a different API: read the [changelog](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md) before you upgrade.

## From a checkout

```bash
cd aeon-core
pip install .                  # or: uv pip install . / pipx install .
```

From git: `pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@main"`.

## Extras

| Extra | Adds | Needed for |
|---|---|---|
| `runtime` | `fastapi`, `uvicorn` | `aeon runtime start`, `aeon serve`, `aeon ui` |
| `openai` | `openai` | only if you use the OpenAI SDK yourself; the adapter does not import it |
| `anthropic` | `anthropic` | same, for the Anthropic SDK |
| `langgraph` | `langgraph`, `langchain-core` | same, for LangGraph |
| `all` | all of the above | |

`aeon-core[runtime]` example: `pip install ".[runtime]"`.

## Check it

```bash
aeon version
aeon doctor
```

`aeon doctor` checks the Python version, the config, the axiom files, that the audit location is writable, verifies an existing audit chain, and runs a gate self-test (block, Safe State, shadow, fail-safe, kill-switch and audit chain).

## Develop on Æon itself

```bash
uv sync --group dev --extra runtime
uv run --no-sync pytest
```

See `CONTRIBUTING.md` in the repository. To build these docs: `uv sync --group docs --extra runtime && uv run --no-sync python scripts/gen_reference.py && uv run --no-sync mkdocs build --strict`.
