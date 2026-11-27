# Campaigns

Each file is a pre-registered campaign: hypothesis, fault, expected outcome, number of
fault runs and number of control runs (same seeds, no fault). They were committed before
their results. Run one with `aeon chaos run campaigns/<file>.toml`, or all of them with
`python benchmarks/run_all.py`.

All campaigns use the simulated `ops-assistant` scenario, a seeded scripted agent, not
an LLM. Short dry runs of the faults were made while the catalog was being written; they
did not change the default budget or these thresholds.
