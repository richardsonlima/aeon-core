# Prompt for a coding agent

If a coding agent (anything that can run shell commands) is wiring Æon into your project, give it the prompt below. It only uses documented commands, and it keeps the agent in shadow mode until you decide otherwise.

```text
You are adding Æon (aeon-core) to this Python project to gate the actions of an LLM agent.
Work in small steps and show me the output of each command.

Rules:
- Do not set the mode to "enforce" and do not remove "mode = shadow". I decide when to enforce.
- Do not edit or delete anything under .aeon/ by hand. Never put secrets in axioms or config.
- Only use these commands: aeon version, aeon doctor, aeon init, aeon axioms list,
  aeon axioms check <file>, aeon run <script> [--mode shadow|enforce], aeon audit tail,
  aeon audit verify, aeon chaos list, aeon chaos run <fault-or-campaign>, aeon report.

Steps:
1. Run `aeon version` and `aeon doctor`. If aeon is missing, stop and tell me.
2. Find the single function through which the agent executes tools. If there are several,
   list them and ask me.
3. Run `aeon init` in the project root. It writes aeon.toml (shadow mode) and aeon_axioms.py.
4. Edit aeon_axioms.py so the axioms match the tools this agent really has: destructive tools
   must need `action.approved`. Use @axiom(on_violation="BLOCK") or the helpers in
   aeon.axioms.builtin. Then run `aeon axioms check aeon_axioms.py`.
5. Wrap the executor with `aeon.axioms.enforce` (decorator or `enforce(fn)`). Give the agent a
   stable name with enforce(..., agent="<name>").
6. Run the agent once with `aeon run <script>` (shadow mode). Then run `aeon audit tail` and
   `aeon audit verify` and summarise which axioms fired and what they would have blocked.
7. Run `aeon chaos run "poisoned output" --runs 10 --controls 10` and paste the result,
   including false positives. Do not hide an unfavourable result.
8. Report: files changed, commands run, the audit summary, and what the gate does not cover
   (actions that bypass the wrapped executor, and the meaning of free text).

Docs for this project: run `aeon docs mcp` to read them over MCP, or see
https://www.richardsonlima.com.br/aeon/docs/ and the llms.txt there.
```

## Give the agent the docs

`aeon docs mcp` serves these pages to a coding agent over MCP (stdio), with `search_docs` and `read_doc`, and every page as a resource `aeon-docs://<path>`. Add it as an MCP server in your agent's config:

```json
{ "mcpServers": { "aeon-docs": { "command": "aeon", "args": ["docs", "mcp"] } } }
```

It reads the `docs/` directory of a source checkout, or the copy bundled in the package. The site also publishes [llms.txt](https://www.richardsonlima.com.br/aeon/docs/llms.txt).
