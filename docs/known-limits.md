# Known limits

Read this before you rely on Æon. The first five are structural. The rest are things I found in the code and the committed measurements.

1. **The gate only covers actions that pass through the wrapped executor.** A call that reaches a tool by any other route is not gated.
2. **Axioms do not judge the semantic correctness of free text.** They look at tool names and argument values. A paraphrased prompt injection, a lie or a leak that matches no pattern passes.
3. **Budget calibration needs a baseline period.** Until `baseline_n` results have been seen for an agent (default 50), the deviation score is 0. The absolute envelope for cost and tokens needs no baseline, but `p99_ms` and `error_rate` need `min_samples` results (default 20).
4. **LLM metrics are statistical because of non-determinism.** Any rate you measure on a real model is an estimate with an interval, and it moves between runs.
5. **Chaos injection is not a substitute for a safety case.** It finds problems. It does not show a system is safe, and Æon has no certification of any kind. IEC 61508 and DO-178C are inspiration and roadmap at most.

## Found in the code and the measurements

6. **The audit queue drops events in bursts.** The queue holds 10,000 events. In the committed burst test (50,000 events, no pause) 2,081 were dropped, 4.2%. Each drop is reported by an `audit.gap` record with the running total, so the gap is visible, but the dropped events are gone. Paced at 1,000 events/s none were dropped. A process that exits with events still queued loses them (`AuditLog.close` counts them as dropped).
7. **Latency spikes from the writer thread.** The emit call is about 2.3 µs at the median, but the maximum in the burst run was 76.7 ms, most likely GIL contention with the writer thread. With audit on, `Gate.decide` had a p99 of 438 µs and a worst call of 3.4 ms in the committed run, against a p99 of 12.4 µs and a worst call of 65 µs with it off. Spikes are rare and not reproducible to the digit, but they exist. Look at p99 and max, not only the median.
8. **Truncation is detected only with `--expect-head`.** Removing records from the end leaves a valid chain. You need a head hash recorded somewhere the log's writer cannot reach.
9. **Someone with write access can rebuild the whole chain.** The chain is tamper-evident against edits, not tamper-proof against a writer who recomputes every hash. There is no signing and no external anchor yet. They are on the roadmap and not built.
10. **One writer process per log file.** Two processes appending to the same file will fork the chain and break verification.
11. **Campaign results come from a scripted simulated agent, not an LLM.** The detection and false-positive rates are properties of the gate against that model.
12. **The default budget produces high false-positive rates on the simulated agent.** On clean control runs (committed results of 2026-11-27, `benchmarks/results/summary.md`): `broken-schema` 70.0% (21 of 30), `gateway-latency` 66.7% (20 of 30), `partial-output` 50.0% (15 of 30), `stale-context` 26.7% (8 of 30), `rate-limit` 26.7% (8 of 30), `tool-timeout` 20.0% (6 of 30). Target was at most 10%. Eight of the nine pre-registered hypotheses were not supported (all eight enforce campaigns: six on false positives, two on the Safe State check). See [How to read an unfavourable result](kb/unfavourable-result.md).
13. **Campaign outcomes shift slightly between reruns with the same seeds.** The simulated tools sleep for a few milliseconds, so latency-dependent results are not bit-identical. `broken-schema` gave 22, 21 and 20 of 30 false positives in three runs, and the latest rerun of `poisoned-output` shows 3 runs that did not reach Safe State, all of them with no destructive attempt (an earlier run showed 2 undetected fault runs instead).
14. **A wall-clock `rate_limit` is unsuitable for fast simulated agents.** It counts calls per real second, and the simulated agent makes hundreds per second, so it fires on clean traffic. The campaigns leave it out on purpose. It also counts denied calls.
15. **The runtime never executes tools.** It decides and records. A caller that ignores `allowed: false` is not stopped by it.
16. **No Postgres backend.** The audit backends are JSONL, SQLite and in-memory.
17. **The gate is per process.** Safe State, the kill-switch and the budget live in memory in one process. The runtime serves one gate, and a campaign started over HTTP runs one at a time.
18. **No field data.** Nobody has reported running Æon on a production agent in shadow mode. Everything measured here is from the repository's own benchmarks and simulated campaigns.
19. **`[aeon.runtime]` in the config and `environment` are accepted but unused.** They do not change any behaviour today.
20. **The runtime token is an operator credential.** It can change the mode, policies, kill-switch and Safe State, and there are no roles. An agent that holds it can switch its own gate to shadow, so never give it to an agent ([ADR 003](decisions/003-operator-token-and-axiom-trust.md)). A decision-only token is on the roadmap, not built.
21. **Axiom files are trusted Python.** `aeon.toml` axiom files are imported and run. Starting `aeon runtime start` or `aeon runtime mcp` in an untrusted checkout runs that checkout's code. Both print the axiom file paths at startup, and there is no trust prompt for configs found by walking up from the working directory yet.
22. **The runtime only sees its own decisions.** Its decisions page, stream and counters cover decisions made through that runtime process. Decisions made in other processes (an agent using the library directly, say) appear only in the audit log.
23. **The public site's earlier claims were wrong.** See [Site changes](site-changes.md).

Measurements are from one machine (Apple M1, Python 3.10.21, 2026-11-27) and describe that machine only. See [Benchmarks](evidence/benchmarks.md).
