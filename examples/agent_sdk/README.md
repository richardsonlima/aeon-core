# Agent SDK example

An `Agent` with two plain-function tools, a `require_approval` rule on `delete_file`, and a session in SQLite. The run pauses when the model asks to delete, then `continue_run(approve=True)` resumes it; every call is in the audit log.

```bash
python main.py                                         # offline, scripted model
export OPENROUTER_API_KEY=...
AEON_LLM_MODEL=openrouter:openai/gpt-4o-mini python main.py   # a real model
```
