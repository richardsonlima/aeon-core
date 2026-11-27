"""Detection quality: run every pre-registered campaign in campaigns/ and collect results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import RESULTS, write

from aeon.chaos import Campaign, render_markdown, run_campaign

CAMPAIGNS = Path(__file__).parents[1] / "campaigns"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    rows = []
    out_dir = RESULTS / "campaigns"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(CAMPAIGNS.glob("*.toml")):
        c = Campaign.load(f)
        if a.only and c.id not in a.only:
            continue
        doc = run_campaign(c)
        (out_dir / f"{c.id}.json").write_text(json.dumps(doc, indent=2, default=str), "utf-8")
        (out_dir / f"{c.id}.md").write_text(render_markdown(doc), "utf-8")
        s = doc["summary"]
        rows.append(
            {
                "id": c.id,
                "fault": c.fault,
                "mode": c.mode,
                "detect_level": c.detect_level,
                "runs": c.runs,
                "controls": c.controls,
                "detection_rate": s["detection_rate"],
                "detection_ci95": s["detection_ci95"],
                "false_positive_rate": s["false_positive_rate"],
                "false_positive_ci95": s["false_positive_ci95"],
                "safe_state_rate": s["safe_state_rate"],
                "harmful_actions_executed": s["harmful_actions_executed"],
                "ttd_steps": s["time_to_detect_steps"],
                "ttd_ms": s["time_to_detect_ms"],
                "tts_ms": s["time_to_safe_state_ms"],
                "checks": doc["checks"],
                "hypothesis_supported": doc["hypothesis_supported"],
                "unfavourable": doc["unfavourable"],
            }
        )
        print(
            f"{c.id:<26} detect={s['detection_rate']:.2f} fp={s['false_positive_rate']:.2f} "
            f"safe={s['safe_state_rate']:.2f} harm={s['harmful_actions_executed']} "
            f"supported={doc['hypothesis_supported']}"
        )
    path = write(
        "detection",
        {
            "description": "Pre-registered campaigns on the simulated ops-assistant scenario.",
            "agent_model": "simulated, seeded, scripted agent (not an LLM)",
            "rows": rows,
        },
    )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
