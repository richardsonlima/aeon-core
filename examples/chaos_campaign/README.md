# Chaos campaign

Runs a small campaign against the built-in simulated ops assistant: a tool starts
returning poisoned output halfway through, and the report states whether the gate detected
it and whether any harmful action ran. Five fault runs and five controls, so it finishes in
about a second. Real campaigns need more runs; see `aeon chaos list` for the fault catalog.

```bash
python examples/chaos_campaign/main.py
```

The output is Markdown: hypothesis, fault, detection rate with a 95% Wilson interval,
and the unfavourable outcomes. To keep the result, call `save_result(result)` or use
`aeon chaos run`.
