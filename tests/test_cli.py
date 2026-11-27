from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aeon.cli.main import build_parser, main

AGENT = """
from aeon.axioms import enforce, ActionBlocked

@enforce
def delete_file(path):
    return "deleted"

@enforce
def read_file(path):
    return "data"

read_file("a")
try:
    delete_file("/etc")
    print("RESULT ran")
except ActionBlocked:
    print("RESULT blocked")
"""


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    o = capsys.readouterr()
    return code, o.out, o.err


@pytest.fixture
def project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Path:
    monkeypatch.delenv("AEON_AUDIT", raising=False)
    assert run(capsys, "init")[0] == 0
    (tmp_path / "agent.py").write_text(AGENT)
    return tmp_path


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "version", "--json")
    assert code == 0 and json.loads(out)["aeon"]


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys)
    assert code == 2 and "usage: aeon" in out


def test_doctor_without_config_warns_but_passes(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "doctor", "--json")
    data = json.loads(out)
    assert code == 0 and data["ok"]
    by = {c["name"]: c for c in data["checks"]}
    assert by["config"]["status"] == "warn" and by["gate self-test"]["status"] == "ok"


def test_doctor_reports_bad_config_with_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "aeon.toml").write_text("[aeon]\nmode = 'yolo'\n")
    code, out, _ = run(capsys, "doctor")
    assert code == 1 and "FAIL" in out and "fix:" in out and "Traceback" not in out


def test_doctor_detects_broken_chain(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "run", "agent.py")[0] == 0
    log = project / ".aeon" / "audit.jsonl"
    lines = log.read_text().splitlines()
    lines[1] = lines[1].replace('"ok":true', '"ok":false')
    log.write_text("\n".join(lines) + "\n")
    code, out, _ = run(capsys, "doctor")
    assert code == 1 and "audit chain" in out and "broken at line 2" in out


def test_init_is_shadow_and_does_not_overwrite(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert 'mode = "shadow"' in (project / "aeon.toml").read_text()
    code, out, _ = run(capsys, "init")
    assert code == 0 and "kept" in out
    assert run(capsys, "init", "--force")[0] == 0


def test_axioms_list_and_check(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "axioms", "list", "--json")
    names = {r["name"] for r in json.loads(out)}
    assert code == 0 and {"no_destructive_tool_call", "require_approval"} <= names
    assert run(capsys, "axioms", "check", "aeon_axioms.py")[0] == 0
    (project / "bad.py").write_text("raise RuntimeError('x')\n")
    code, _, err = run(capsys, "axioms", "check", "bad.py")
    assert code == 1 and "error while importing" in err
    (project / "empty.py").write_text("x = 1\n")
    assert run(capsys, "axioms", "check", "empty.py")[0] == 1
    (project / "raises.py").write_text(
        "from aeon.axioms import axiom\n@axiom\ndef r(a):\n    raise ValueError('no')\n"
    )
    code, out, _ = run(capsys, "axioms", "check", "raises.py")
    assert code == 1 and "raised" in out


def test_run_shadow_then_enforce_then_verify(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run(capsys, "run", "agent.py", "--mode", "shadow")
    assert code == 0 and "RESULT ran" in out and "mode=shadow" in err
    code, out, err = run(capsys, "run", "agent.py", "--mode", "enforce")
    assert code == 0 and "RESULT blocked" in out and "denied=1" in err
    code, out, _ = run(capsys, "audit", "verify", "--json")
    v = json.loads(out)
    assert code == 0 and v["ok"] and v["records"] >= 8
    code, out, _ = run(capsys, "audit", "tail", "--type", "decision")
    assert "DENIED (enforce)" in out and "allowed (shadow)" in out
    code, out, _ = run(capsys, "audit", "verify", "--expect-head", "0" * 64)
    assert code == 1 and "head mismatch" in out


def test_audit_verify_pinpoints_tampering(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run(capsys, "run", "agent.py", "--mode", "enforce")
    log = project / ".aeon" / "audit.jsonl"
    lines = log.read_text().splitlines()
    lines[2] = lines[2].replace("BLOCK", "GO")
    log.write_text("\n".join(lines) + "\n")
    code, out, _ = run(capsys, "audit", "verify")
    assert code == 1 and "BROKEN at line 3" in out


def test_audit_export(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run(capsys, "run", "agent.py")
    code, out, _ = run(capsys, "audit", "export", "--format", "csv")
    assert code == 0 and out.splitlines()[0].startswith("seq,ts,type")
    assert run(capsys, "audit", "export", "-o", "x.jsonl")[0] == 0
    assert (project / "x.jsonl").read_text().count("\n") >= 4


def test_audit_errors_without_log(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, "audit", "verify")
    assert code == 1 and "fix:" in err


def test_run_missing_script(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, "run", "nope.py")
    assert code == 1 and "script not found" in err


def test_chaos_list_and_run_and_report(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "chaos", "list", "--json")
    assert code == 0 and len(json.loads(out)) == 8
    code, out, _ = run(
        capsys,
        "chaos",
        "run",
        "degrade gateway latency",
        "--blast-radius=staging",
        "--runs",
        "2",
        "--controls",
        "2",
        "--seed",
        "3",
    )
    assert code == 0 and "fault gateway-latency injected" in out and "report: aeon report" in out
    code, out, _ = run(capsys, "report", "adhoc-gateway-latency")
    assert code == 0 and "## Unfavourable results" in out
    code, out, _ = run(capsys, "report", "--json")
    assert json.loads(out)[0]["id"] == "adhoc-gateway-latency"
    assert run(capsys, "report", "adhoc-gateway-latency", "-o", "out/r")[0] == 0
    assert (project / "out" / "r.md").is_file() and (project / "out" / "r.json").is_file()


def test_chaos_run_guards(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, "chaos", "run", "poison", "--blast-radius", "prod-shadow")
    assert code == 2 and "ceiling" in err and "fix:" in err
    code, _, err = run(capsys, "chaos", "run", "meteor strike")
    assert code == 2 and "aeon chaos list" in err
    code, _, err = run(capsys, "report", "missing")
    assert code == 1 and "no results" in err


def test_chaos_run_campaign_file_strict(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "campaigns").mkdir()
    (project / "campaigns" / "impossible.toml").write_text(
        'id="impossible"\nhypothesis="never detected"\nfault="gateway-latency"\nruns=2\n'
        "controls=2\nsteps=45\nstart_step=40\n[expected]\nmax_false_positive_rate=0.0\n"
        'min_detection_rate=1.0\nlevel="BLOCK"\n'
    )
    code, out, _ = run(capsys, "chaos", "run", "impossible", "--strict")
    assert code == 1 and "NOT supported" in out


def test_runtime_commands_explain_missing_extra(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import builtins

    real = builtins.__import__

    def fake(name: str, *a: object, **k: object) -> object:
        if name in {"fastapi", "uvicorn"}:
            raise ImportError(name)
        return real(name, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake)
    for cmd in (["runtime", "start"], ["serve"], ["ui", "--no-browser"]):
        code, _, err = run(capsys, *cmd)
        assert code == 1 and "aeon-core[runtime]" in err


def test_every_data_command_has_json() -> None:
    parser = build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    no_json = {"run", "serve", "ui", "export", "start", "mcp"}

    def walk(p: object, name: str) -> None:
        acts = p._actions  # type: ignore[attr-defined]
        subs = [a for a in acts if a.__class__.__name__ == "_SubParsersAction"]
        if subs:
            for n, sp in subs[0].choices.items():
                walk(sp, n)
            return
        opts = {o for a in acts for o in a.option_strings}
        assert ("--json" in opts) or name in no_json, name

    for n, sp in sub.choices.items():  # type: ignore[attr-defined]
        walk(sp, n)


def test_python_dash_m_entry_point(tmp_path: Path) -> None:
    r = subprocess.run(
        [sys.executable, "-m", "aeon", "version"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert r.returncode == 0 and r.stdout.startswith("aeon ")


def test_unexpected_errors_have_no_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import aeon.cli.main as m

    def boom(args: object) -> int:
        raise RuntimeError("kaput")

    monkeypatch.setattr(m, "cmd_version", boom)
    code, _, err = run(capsys, "version")
    assert code == 1 and "unexpected error" in err and "Traceback" not in err
