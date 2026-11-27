# Configuration

Æon reads `aeon.toml` (or `.aeon.toml`), or a `[tool.aeon]` table in `pyproject.toml`, then applies `AEON_*` environment variables, which win. Unknown keys are rejected with the file name, so a typo fails loudly.

## Where the file is found

1. `AEON_CONFIG`, if set (a path).
2. Otherwise, starting at the current directory and walking up: `aeon.toml`, `.aeon.toml`, then a `pyproject.toml` that has `[tool.aeon]`. The walk stops at the directory that holds `.git`.
3. Otherwise, defaults. Relative paths in the file (axiom files, audit path) resolve against the file's directory. `--config <path>` on the CLI selects a file explicitly.

## `aeon.toml`

```toml
[aeon]
mode = "shadow"                  # "shadow" (default) or "enforce"
axioms = ["aeon_axioms.py"]      # a path or a list of paths; Python files that declare axioms
include_args = false             # true records raw tool arguments in the audit log

[aeon.audit]
path = ".aeon/audit.jsonl"       # or "sqlite:.aeon/audit.db", "memory", or "off"
fsync = false                    # true makes each batch durable before the writer continues

[aeon.budget]                    # every key of Budget, see below
baseline_n = 50
alert_at = 5.0
limit_at = 10.0
block_at = 20.0
# p99_ms = 300
# error_rate = 0.02

[aeon.chaos]
environment = "dev"
max_blast_radius = "staging"     # ceiling: "dev", "staging" or "prod-shadow"
```

`audit` may also be a string: `audit = ".aeon/audit.jsonl"`. The values `off`, `none`, `false`, `0` or an empty string disable the log. `[aeon.runtime]` is accepted and stored, and nothing reads it yet. `environment` is recorded in the config object and does not change any decision yet.

In `pyproject.toml`, write the same tables under `[tool.aeon]`, for example `[tool.aeon.budget]`.

## Budget keys

All keys are optional. The math is on [Budget and deviation](../concepts/budget.md).

| Key | Default | Meaning |
|---|---|---|
| `p99_ms` | none | envelope: p99 latency over the window |
| `error_rate` | none | envelope: error fraction over the window |
| `max_cost` | none | envelope: cumulative cost |
| `max_tokens` | none | envelope: cumulative tokens |
| `on_breach` | `LIMIT` | level raised by an envelope breach (`ALERT`, `LIMIT` or `BLOCK`) |
| `baseline_n` | 50 | results used to calibrate each agent (at least 2) |
| `window` | 50 | rolling window size |
| `min_samples` | 20 | results in the window before drift, p99 and error rate are evaluated |
| `slack` | 1.0 | CUSUM allowance `k` |
| `alert_at` | 5.0 | accumulated deviation for `ALERT` |
| `limit_at` | 10.0 | accumulated deviation for `LIMIT` |
| `block_at` | 20.0 | accumulated deviation for `BLOCK` |
| `z_max` | 10.0 | clip for each z-score |
| `repeat_lookback` | 3 | how many recent actions define a repeat |
| `drift_scale` | 0.1 | Jensen-Shannon divergence that counts as a z of 1 |
| `weights` | all 1.0 | per-term weights: `latency`, `error`, `repeat`, `tokens`, `drift` |

## Environment variables

| Variable | Effect |
|---|---|
| `AEON_CONFIG` | path of the config file to use |
| `AEON_MODE` | overrides `mode` (`shadow` or `enforce`) |
| `AEON_AUDIT` | overrides the audit location (`off` disables it) |
| `AEON_AXIOMS` | overrides the axiom files, separated by the OS path separator (`:` on Linux and macOS) |
| `AEON_ENVIRONMENT` | overrides `[aeon.chaos] environment` |
| `AEON_MAX_BLAST_RADIUS` | overrides the blast radius ceiling |
| `AEON_RUNTIME_TOKEN` | bearer token for the [runtime](../guides/runtime.md); otherwise `.aeon/runtime.token` is used and created |
| `AEON_RUNTIME_ALLOWED_HOSTS` | comma-separated Host header allowlist for the runtime. Default on a loopback bind: `localhost`, `127.0.0.1`, `[::1]`. Works on any bind and in containers (`compose.yaml` sets `localhost,127.0.0.1`). On a non-loopback bind without it, no Host check is made |
| `AEON_RUNTIME_ALLOW_REMOTE` | set to `1` to allow binding a non-loopback address. Read [Security](../security.md) first |
| `AEON_DEBUG` | set to anything to get a Python traceback instead of a one-line error from the CLI |

`AEON_TELEMETRY` does nothing: Æon sends no telemetry, and `aeon doctor` says so if the variable is set.

`aeon run <script> --mode enforce` sets `AEON_MODE` for that run. Without `--mode`, `aeon run` uses the configured mode (`aeon.toml`, else shadow).

## Check it

```bash
aeon doctor      # reports the config file in use, the mode, the axioms and the audit location
```
