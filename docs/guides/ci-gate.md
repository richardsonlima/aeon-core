# CI resilience gate

`aeon chaos run ... --strict` exits 1 when a campaign's hypothesis is not supported. That makes a campaign a CI check: "with this fault injected, the gate still catches it and no harmful action runs".

```yaml
# .github/workflows/resilience.yml
name: Resilience
on: [pull_request]
jobs:
  chaos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      # Until the first PyPI release, install from git; afterwards: pip install aeon-core
      - run: pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@main"
      - run: aeon doctor
      - run: aeon chaos run campaigns/our-poisoned-output.toml --strict
      - if: always()
        run: aeon report our-poisoned-output -o chaos-report
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: chaos-report, path: chaos-report.* }
```

## Read this before you add it

- **The shipped campaigns do not pass `--strict`.** On the committed run, eight of the nine shipped campaigns (all eight enforce ones) had a hypothesis that was not supported, mostly because the default budget raises false positives on clean traffic of the simulated agent ([numbers](../evidence/benchmarks.md)). Do not point CI at them as they are. Write your own campaign with thresholds you have reached on your own runs, and set `max_false_positive_rate` honestly.
- **Exit codes.** `0` supported, `1` not supported (only with `--strict`), `2` usage error such as an unknown fault or a blast radius above the ceiling.
- **Determinism.** Seeds are fixed, but the simulated agent sleeps for a few milliseconds per call and the faults add delays, so latency-based results can move from run to run. Leave margin between your threshold and what you measured, and use enough runs (30 is the shipped size, and its 95% interval is wide).
- **Cost.** Each shipped campaign took about 8 to 10 seconds on the reference machine for 30 fault runs and 30 controls.
- **Scope.** The campaign exercises the gate and your axioms against a simulated agent. It does not test your real agent or model. See [Known limits](../known-limits.md).

## A gate you can trust

Pin the campaign file in the repository, change it only in a reviewed commit, and keep the unfavourable results in the report. A threshold that is quietly raised until CI is green is not evidence.
