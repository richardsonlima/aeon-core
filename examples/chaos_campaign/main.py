"""Run a small pre-registered chaos campaign and print its report."""

from aeon.chaos import Campaign, render_markdown, run_campaign

campaign = Campaign(
    id="poisoned-output-small",
    hypothesis="The gate stops harmful actions after a tool returns poisoned output.",
    fault="poisoned-output",
    steps=40,
    start_step=20,
    runs=5,
    controls=5,
    seed=7,
    blast_radius="dev",
    mode="enforce",
    budget={"baseline_n": 15},
)
result = run_campaign(campaign)
print(render_markdown(result))
