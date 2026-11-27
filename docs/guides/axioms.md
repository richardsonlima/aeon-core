# Write an axiom

An axiom is a function over an `Action` that says whether the action is acceptable.

```python
from aeon.axioms import axiom, Violation, ALERT


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """Destructive tools need explicit approval."""
    return action.tool not in {"delete_file", "drop_table"} or action.approved


@axiom(on_violation="ALERT", tools=["http_get"])
def flag_external_urls(action):
    url = str(action.args.get("url", ""))
    return not url or url.startswith("https://internal.example.com")


@axiom(on_violation="LIMIT")
def big_transfers_need_approval(action):
    if action.tool == "transfer_funds" and action.args.get("amount", 0) > 100:
        return Violation("transfer above 100", level=ALERT if action.approved else None)
    return True
```

## What the function may return

| Return | Meaning |
|---|---|
| `True` or `None` | passes |
| `False` | objects at the declared level; the reason is the docstring's first line, or `<name> returned False` |
| a `str` | objects at the declared level, with that text as the reason |
| a `Violation(reason, level=None)` | objects, and may pick the level per call |
| an exception | the axiom is treated as a `BLOCK` finding (fail-safe) |
| anything else | `TypeError`, also treated as a fail-safe `BLOCK` |

The `Action` carries `tool`, `args`, `agent`, `approved` and `context` (anything you attach: the user's request, the step number, the environment). `tools=[...]` limits the rule to those tool names.

## Keep axioms small and syntactic

They run on the decision path, in the caller's thread. Do not do I/O or call a model in an axiom. They look at tool names and argument values; they cannot judge whether free text is correct or safe. See [Known limits](../known-limits.md).

## Built-in factories

`aeon.axioms.builtin` returns ready-made rules. Assign them at module level in an axiom file so `aeon axioms list` finds them:

```python
from aeon.axioms.builtin import allow_tools, deny_arg_pattern, deny_tools, rate_limit, require_approval

no_delete = deny_tools(["delete_file"], unless_approved=True)       # BLOCK
only_these = allow_tools(["read_file", "search_docs"])              # BLOCK for any other tool
no_secrets = deny_arg_pattern(r"AKIA[0-9A-Z]{16}", level="BLOCK")   # regex over string args
deploys = require_approval(["deploy"])                               # LIMIT unless approved
slow_down = rate_limit(30, 60, tools=["send_email"])                 # LIMIT after 30 calls in 60 s
```

`rate_limit` uses wall-clock time and counts decisions, so a denied call still counts. It is unsuitable for a fast simulated agent: the campaigns leave it out on purpose.

## Load from a file

Point `axioms = ["aeon_axioms.py"]` in `aeon.toml` at the file. Check it before you rely on it:

```bash
aeon axioms list aeon_axioms.py
aeon axioms check aeon_axioms.py    # imports the file and self-tests it on a probe action
```

To unit-test an axiom, call it with an `Action`; the decorator returns your function unchanged.
