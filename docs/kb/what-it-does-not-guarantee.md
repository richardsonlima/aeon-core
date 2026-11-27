# What it does not guarantee

- **Coverage.** Only actions that pass through the wrapped executor are gated. A second code path that calls the tool directly, a tool the agent reaches through another library, or an agent that never asks the runtime is invisible to the gate.
- **Meaning.** Axioms see tool names and argument values. They cannot tell whether a string is a lie, a leak or a prompt injection that is spelled differently from your pattern. A model that answers with harmful text and calls no tool is not stopped.
- **Completeness of the log.** The audit queue is bounded. In a burst test, 2,081 of 50,000 events were dropped (recorded as `audit.gap`). Paced at 1,000 events/s none were. A process that dies loses what is still queued.
- **Integrity against a writer.** The chain detects an edit, a removal in the middle, a reorder and a corrupted line. Removing records from the end is detected only with `--expect-head`. Someone with write access to the file can rebuild the whole chain; there is no signing or external anchor yet (roadmap).
- **Calibration without data.** A budget needs a baseline period. Before `baseline_n` results the deviation score is 0.
- **Statistics on LLMs.** LLM behaviour is non-deterministic, so any metric over it is statistical. The campaigns here use a scripted simulated agent, not an LLM, so even the detection rates do not transfer to a real model.
- **Low false positives.** The default budget raised false positives in up to 70% of clean control runs on the simulated agent.
- **A safety case.** Chaos injection finds problems. It is not evidence that a system is safe, and Æon carries no certification.
- **Past actions.** Safe State and `BLOCK` stop the next action. They do not undo the previous one.
- **Multiple writers.** One audit writer process per log file.

The full list, with the evidence for each, is on [Known limits](../known-limits.md).
