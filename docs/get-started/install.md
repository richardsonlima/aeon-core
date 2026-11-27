# Install

!!! warning "Not on PyPI yet"
    No release has been published. The commands marked "after the first release" will not work today. Until then, install from a checkout or from git. The remote `main` branch is still the old v0.4 line and `feature/v0.5.0` is not pushed yet, so install from a local checkout of the v0.5.0 work.

Requires Python 3.10 or newer. The core has no third-party dependencies (on 3.10 only, `tomli`).

## From a checkout (works today)

```bash
cd aeon-core                       # your checkout of the v0.5.0 work
```

=== "pip"

    ```bash
    python -m venv .venv && . .venv/bin/activate
    pip install .                  # core only
    pip install ".[runtime]"       # plus the HTTP runtime
    aeon version
    ```

=== "uv"

    ```bash
    uv venv && uv pip install .
    uv run aeon version
    ```

=== "uvx"

    ```bash
    uvx --from /path/to/aeon-core aeon version
    ```

=== "pipx"

    ```bash
    pipx install /path/to/aeon-core
    aeon version
    ```

Once the branch is on GitHub, the same works straight from git: `pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@<branch>"`, `uvx --from "git+https://github.com/richardsonlima/aeon-core@<branch>" aeon version`, `pipx install "git+https://github.com/richardsonlima/aeon-core@<branch>"`.

## After the first release

```bash
pip install aeon-core
uv add aeon-core                      # in a project
uvx --from aeon-core aeon version     # no install
pipx install aeon-core                # as a command-line tool
```

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
