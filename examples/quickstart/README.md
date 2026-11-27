# Quickstart

A plain Python agent with two tools. One axiom blocks destructive tools unless a human
approved them. The script runs the same plan twice: in shadow mode the axiom only records
what it would have done, in enforce mode it stops the call.

```bash
cd examples/quickstart
python main.py                       # shadow, then enforce, in one process
aeon run main.py --mode enforce      # the same script under the CLI
aeon audit verify                    # checks the hash chain of .aeon/audit.jsonl
aeon audit tail
```

Files:

- `aeon_axioms.py`: the rule, declared with `@axiom(on_violation="BLOCK")`.
- `aeon.toml`: loads the axiom file and writes the audit log to `.aeon/audit.jsonl`.
- `main.py`: wraps the agent's executor with `enforce(...)` and uses the default gate
  built from that config. `AEON_AUDIT` overrides the audit path.
