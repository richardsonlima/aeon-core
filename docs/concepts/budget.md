# Budget and deviation

This page is the math in `aeon.baseline`. Nothing here is tuned to flatter a result: the defaults produce high false-positive rates on the simulated agent (see [How to read an unfavourable result](../kb/unfavourable-result.md)).

A **budget** answers "how far may this agent drift from its own normal behaviour?" It has two independent parts: a deviation score measured against a calibrated baseline, and an absolute envelope that needs no calibration.

## 1. Calibration

For each agent, the first `baseline_n` results (default 50) are not scored. From them Æon computes:

| Symbol | Meaning |
|---|---|
| `m_L`, `s_L` | mean and sample standard deviation (n-1) of latency in ms |
| `p_e` | fraction of results that were errors |
| `p_r` | fraction that were repeats (same tool and same argument digest as one of the last `repeat_lookback` actions, default 3) |
| `m_T`, `s_T` | mean and standard deviation of tokens, if at least 2 results reported tokens |
| `q` | count of calls per tool (the tool distribution) |

While calibrating, the score is 0 and no deviation level is raised. A baseline can also be set directly (`Monitor.set_baseline`) or passed in at construction.

## 2. Deviation score per result

Each later result `t` gets terms, each a one-sided z-score clipped to `[0, z_max]` with `z_max=10`:

```text
clip(z)=max(0,min(z_max,z))
```

- Latency, with a floor on the spread so a very steady baseline does not make every blip look huge:
  `sigma_L=max(s_L, 0.1 m_L, 1 ms)`, `z_lat=clip((x_t-m_L)/sigma_L)`.
- Error and repeat are binary. With `b_t in {0,1}` and baseline rate `p`:
  `z=clip((b_t-p)/sqrt(max(p(1-p), 0.01)))`.
- Tokens (only if the result and the baseline both have them):
  `sigma_T=max(s_T, 0.1 m_T, 1)`, `z_tok=clip((T_t-m_T)/sigma_T)`.
- Drift, once the rolling window (last `window`, default 50) holds at least `min_samples` results (default 20): the Jensen-Shannon divergence (base 2, so in [0, 1]) between the baseline tool distribution and the window's, scaled:
  `z_drift=clip(JS(q_base,q_window)/drift_scale)`, `drift_scale` default 0.1.

Only upward deviation counts. Faster than normal, fewer errors than normal: zero.

The step score is the weighted sum, with weights `w_k` (default 1 each):

```text
d_t = sum over k of (w_k * z_k)
```

## 3. Accumulation: CUSUM

The step score is not compared to a threshold directly. It feeds a one-sided CUSUM with slack `k` (`slack`, default 1.0):

```text
S_t = max(0, S_(t-1) + d_t - k)
```

`S_t` grows when behaviour stays above normal and drains by `k` per step when it does not. The level is the highest threshold crossed:

| Condition | Level |
|---|---|
| `S_t >=` `block_at` (default 20) | `BLOCK` |
| `S_t >=` `limit_at` (default 10) | `LIMIT` |
| `S_t >=` `alert_at` (default 5) | `ALERT` |
| otherwise | `GO` |

Thresholds must satisfy `0 <= alert_at <= limit_at <= block_at`. A threshold of 0 is disabled.

A worked consequence of the formulas: with `p_e=0`, one error gives `z=1/sqrt(0.01)=10`, the clip, so `d_t >= 10` and `S` jumps by at least 9. One error alone crosses `alert_at`, two in a row cross `limit_at`, three cross `block_at`. That is intended for agents that never fail. It is also why a baseline with zero errors is touchy.

## 4. The absolute envelope

Independent of calibration, over the same rolling window:

| Field | Breach when | Needs |
|---|---|---|
| `p99_ms` | nearest-rank p99 of window latencies `>` value (sorted, index `ceil(0.99 n)-1`) | `min_samples` results in the window |
| `error_rate` | error fraction in the window `>` value | `min_samples` results in the window |
| `max_cost` | cumulative cost `>` value | nothing |
| `max_tokens` | cumulative tokens `>` value (includes `record_usage`) | nothing |

A breach raises the level to `on_breach` (default `LIMIT`) if that is higher than the deviation level. Fields left as `None` are not checked. Reasons are recorded in the finding, for example `p99 latency 12.0 ms > 10 ms`.

## 5. Decision path and observation path

`Monitor.record` (observation path) does all of the above and stores the resulting level. `Monitor.finding` (decision path) only reads that stored level, so a decision never computes a z-score.

## 6. Reset semantics

`Monitor.reset_accumulated(agent)` sets `S` to 0, clears the rolling window and zeroes the cost and token totals. The calibrated baseline is kept. `Gate.reset(agent)` calls it when it releases an agent from [Safe State](safe-state.md). After a reset the envelope fields that need `min_samples` stay silent until the window refills.

## Configuration

```toml
[aeon.budget]
baseline_n = 50
alert_at = 5.0
limit_at = 10.0
block_at = 20.0
p99_ms = 300       # optional envelope
error_rate = 0.02
```

All keys are listed in [Configuration](../reference/config.md). To pick values, read [How to calibrate a budget](../kb/calibrate-budget.md).
