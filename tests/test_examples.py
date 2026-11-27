from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

EXPECTED: dict[str, list[str]] = {
    "quickstart": ["-- shadow mode", "-- enforce mode", "denied=1"],
    "openai_agent": ["Æon blocked this action:", "decisions: 2 denied: 1"],
    "anthropic_agent": ["is_error=True", "decisions: 2 denied: 1"],
    "langgraph_agent": ["Æon blocked 'delete_file'", "decisions: 2 denied: 1"],
    "chaos_campaign": ["# Campaign `poisoned-output-small`", "hypothesis supported"],
}


def _env(audit: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AEON_")}
    env["AEON_AUDIT"] = str(audit)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), env.get("PYTHONPATH", "")])
    return env


def _run(args: list[str], cwd: Path, audit: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=_env(audit),
        capture_output=True,
        text=True,
        encoding="utf-8",  # the child writes UTF-8; the parent's locale may be cp1252
        timeout=120,
        check=False,
    )


def test_every_example_is_covered() -> None:
    found = {p.parent.name for p in EXAMPLES.glob("*/main.py")}
    assert found == set(EXPECTED)
    for name in found:
        assert (EXAMPLES / name / "README.md").is_file()


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_example_runs(name: str, tmp_path: Path) -> None:
    work = tmp_path / name
    shutil.copytree(EXAMPLES / name, work)
    audit = tmp_path / "audit.jsonl"
    proc = _run([str(work / "main.py")], work, audit)
    assert proc.returncode == 0, proc.stderr
    for line in EXPECTED[name]:
        assert line in proc.stdout, proc.stdout
    if name != "chaos_campaign":
        assert audit.is_file()
        verify = _run(["-m", "aeon", "audit", "verify", "--file", str(audit)], work, audit)
        assert verify.returncode == 0, verify.stdout + verify.stderr


def test_quickstart_cli_flow(tmp_path: Path) -> None:
    work = tmp_path / "quickstart"
    shutil.copytree(EXAMPLES / "quickstart", work)
    audit = work / ".aeon" / "audit.jsonl"
    env_audit = audit  # AEON_AUDIT points inside the copy, the same file `aeon audit` reads
    run = _run(["-m", "aeon", "run", "main.py", "--mode", "enforce"], work, env_audit)
    assert run.returncode == 0, run.stderr
    assert "mode=enforce" in run.stderr
    assert "delete_file -> Æon blocked" in run.stdout
    verify = _run(["-m", "aeon", "audit", "verify"], work, env_audit)
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "chain intact" in verify.stdout
