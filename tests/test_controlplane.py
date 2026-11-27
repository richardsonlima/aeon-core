from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from aeon.axioms import Gate
from aeon.config import Config
from aeon.runtime.app import controlplane_dir, create_app

UI = Path(__file__).resolve().parents[1] / "controlplane"
HTML = (UI / "index.html").read_text("utf-8")
APP_JS = (UI / "app.js").read_text("utf-8")
I18N_JS = (UI / "i18n.js").read_text("utf-8")


def _dictionary(name: str) -> set[str]:
    m = re.search(rf"export const {name} = \{{(.*?)\n\}};", I18N_JS, re.S)
    assert m, f"dictionary {name} not found"
    return set(re.findall(r'^\s*"([a-z0-9_]+)":', m.group(1), re.M))


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    cfg = Config(root=tmp_path)
    return TestClient(create_app(Gate(), config=cfg, token="t"))


def test_runtime_serves_the_ui(client: TestClient) -> None:
    assert controlplane_dir() is not None
    for path in ("/ui/", "/ui/app.js", "/ui/app.css", "/ui/i18n.js"):
        res = client.get(path)
        assert res.status_code == 200, path
    assert "Content-Security-Policy" in client.get("/ui/").text


def test_index_references_only_local_assets() -> None:
    refs = re.findall(r'\b(?:src|href)\s*=\s*"([^"]*)"', HTML)
    assert refs
    for ref in refs:
        assert not re.match(r"(?i)(https?:)?//", ref), ref
    assert not re.search(r"https?://", HTML)
    assert "default-src 'self'" in HTML and "connect-src 'self'" in HTML
    assert not re.search(r"<script(?![^>]*\bsrc=)", HTML), "inline script"
    assert " style=" not in HTML and "<style" not in HTML, "inline style"
    assert not re.search(r"\son[a-z]+=", HTML), "inline event handler"


def test_no_third_party_urls_in_sources() -> None:
    for name in ("app.js", "app.css", "i18n.js"):
        text = (UI / name).read_text("utf-8")
        assert not re.search(r"https?://", text), name
        assert "@import" not in text, name


def test_no_innerhtml_with_data() -> None:
    for name in ("app.js", "i18n.js"):
        text = (UI / name).read_text("utf-8")
        assert "innerHTML" not in text, name
        assert "outerHTML" not in text, name
        assert "insertAdjacentHTML" not in text, name
        assert "document.write" not in text, name
        assert "eval(" not in text, name


def test_i18n_dictionaries_match() -> None:
    en, pt = _dictionary("EN"), _dictionary("PT")
    assert en and en == pt, sorted(en ^ pt)


def test_every_used_key_exists_in_both_languages() -> None:
    en, pt = _dictionary("EN"), _dictionary("PT")
    used = set(re.findall(r'\bt\("([a-z0-9_]+)"\)', APP_JS))
    used |= set(re.findall(r'data-i18n(?:-label)?="([a-z0-9_]+)"', HTML))
    # keys built from a status name, such as t(`cl_${status}`)
    for status in ("specified", "implemented", "measured"):
        used |= {f"cl_{status}", f"cl_{status}_desc"}
    assert len(used) > 50
    assert not used - en, sorted(used - en)
    assert not used - pt, sorted(used - pt)


def test_dynamic_i18n_keys_are_only_the_claim_ladder() -> None:
    dynamic = set(re.findall(r"\bt\(`([^`]*)`\)", APP_JS))
    assert dynamic <= {"cl_${s}", "cl_${s}_desc", "cl_${status}"}, dynamic


def test_pages_and_landmarks_present() -> None:
    for route in ("overview", "decisions", "campaigns", "audit", "claims"):
        assert f'data-route="{route}"' in HTML
        assert f"pages.{route} =" in APP_JS
    for needle in ('class="skip"', "<main", "<nav", 'role="banner"', 'aria-live="assertive"'):
        assert needle in HTML, needle
    assert "prefers-reduced-motion" in (UI / "app.css").read_text("utf-8")
