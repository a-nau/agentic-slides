"""Tests for the deck server's re-render loop (quarto/scripts/serve.py), no quarto needed."""

import importlib.util
import os
import subprocess
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("serve", REPO / "quarto/scripts/serve.py")
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


def test_edit_during_render_is_rendered_next_scan(tmp_path, monkeypatch):
    deck = tmp_path / "decks/tools/demo"
    deck.mkdir(parents=True)
    qmd = deck / "slides.qmd"
    qmd.write_text("v1")
    os.utime(qmd, (1000, 1000))
    renders = []

    def fake_render(cmd, **kw):
        renders.append(qmd.read_text())
        if len(renders) == 1:  # the source is saved again while the render runs
            qmd.write_text("v2")
            os.utime(qmd, (2000, 2000))
        (deck / "slides.html").write_text("rendered " + renders[-1])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(serve, "REPO", tmp_path)
    monkeypatch.setattr(serve, "DECKS", tmp_path / "decks")
    monkeypatch.setattr(serve.subprocess, "run", fake_render)
    serve.scan()
    serve.scan()
    assert renders == ["v1", "v2"]
    serve.scan()  # up to date now: no further render
    assert renders == ["v1", "v2"]


def test_render_output_is_held_while_its_deck_renders(tmp_path, monkeypatch):
    monkeypatch.setattr(serve, "DECKS", tmp_path)
    deck = tmp_path / "tools/demo"
    serve.RENDERING.add(deck)
    try:
        done = threading.Event()
        threading.Thread(target=lambda: (serve.hold("/tools/demo/slides.md"), done.set()), daemon=True).start()
        serve.hold("/tools/other/slides.md")  # another deck: not held
        serve.hold("/tools/demo/images/fig.svg")  # a source file: not held
        assert not done.wait(0.2)
    finally:
        with serve.RENDER_DONE:
            serve.RENDERING.discard(deck)
            serve.RENDER_DONE.notify_all()
    assert done.wait(2)


def test_static_get_refuses_foreign_host_on_loopback():
    """A rebound DNS name (Host: evil.example) gets no deck files, comments, or PDFs."""
    seen = []

    class Fake(serve.Handler):
        def __init__(self, host):  # no socket: just what _host_bad reads
            self.headers = {"Host": host}
            self.server = type("S", (), {"bind_host": "127.0.0.1"})()

        def send_error(self, code, msg=None):
            seen.append(code)

    assert Fake("evil.example:8093")._host_bad() is True
    assert Fake("localhost:8093")._host_bad() is False
    assert seen == [403]


def test_token_login_cookie_then_access(monkeypatch):
    monkeypatch.setattr(serve.export_server, "TOKEN", "s3cret")
    sent = []

    class Fake(serve.Handler):
        def __init__(self, headers):
            self.headers = headers
            self.server = type("S", (), {"bind_host": "0.0.0.0", "server_address": ("", 8093)})()

        def _send(self, code, body, ctype):
            sent.append(code)

        def send_response(self, code):
            sent.append(code)

        def send_header(self, k, v):
            sent.append((k, v))

        def end_headers(self):
            pass

    assert Fake({"Host": "h:8093"})._host_bad() is True and sent == [401]
    assert Fake({"Host": "h:8093", "Cookie": "deck_token_8093=s3cret"})._host_bad() is False
    sent.clear()
    u = serve.urllib.parse.urlsplit("/tools/demo/slides.md?token=s3cret#x")
    assert Fake({"Host": "h:8093"})._login(u) is True
    assert sent[0] == 302 and ("Location", "/tools/demo/slides.md") in sent
    assert any(k == "Set-Cookie" and v.startswith("deck_token_8093=s3cret;") and "HttpOnly" in v for k, v in sent[1:])
    assert Fake({"Host": "h:8093"})._login(serve.urllib.parse.urlsplit("/?token=wrong")) is False

