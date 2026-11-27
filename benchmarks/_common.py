"""Shared helpers: machine description, percentiles, result writing."""

from __future__ import annotations

import contextlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

RESULTS = Path(__file__).parent / "results"


def machine() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }
    if sys.platform == "darwin":
        with contextlib.suppress(OSError):
            info["cpu"] = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
    elif Path("/proc/cpuinfo").exists():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                info["cpu"] = line.split(":", 1)[1].strip()
                break
    return info


def pct(sorted_xs: list[float], p: float) -> float:
    return sorted_xs[max(0, math.ceil(p * len(sorted_xs)) - 1)]


def summarize(xs: list[float]) -> dict[str, float | int]:
    s = sorted(xs)
    return {
        "n": len(s),
        "p50": pct(s, 0.5),
        "p90": pct(s, 0.9),
        "p99": pct(s, 0.99),
        "max": s[-1],
        "mean": sum(s) / len(s),
        "min": s[0],
    }


def write(name: str, doc: dict[str, Any]) -> Path:
    from aeon import __version__

    RESULTS.mkdir(parents=True, exist_ok=True)
    doc = {
        "benchmark": name,
        "aeon_version": __version__,
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machine": machine(),
        **doc,
    }
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(doc, indent=2), "utf-8")
    return path
