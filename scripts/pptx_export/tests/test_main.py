import importlib
from pathlib import Path


cli = importlib.import_module("scripts.pptx_export.__main__")


def _fake_pipeline(monkeypatch, seen):
    def fake_extract(_html, png_dir):
        path = Path(png_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "sentinel").write_text("kept only when caller-owned")
        seen["png_dir"] = path
        return {"slide_px": [1280, 720], "slides": []}

    def fake_build(_model, out):
        Path(out).touch()

    monkeypatch.setattr(cli.extract, "extract_html", fake_extract)
    monkeypatch.setattr(cli.build, "build_pptx", fake_build)


def test_implicit_screenshot_directory_is_removed(tmp_path, monkeypatch):
    html = tmp_path / "deck.html"
    html.write_text("<html></html>")
    seen = {}
    _fake_pipeline(monkeypatch, seen)

    cli.main([str(html), str(tmp_path / "deck.pptx")])

    assert not seen["png_dir"].exists()


def test_explicit_screenshot_directory_is_preserved(tmp_path, monkeypatch):
    html = tmp_path / "deck.html"
    html.write_text("<html></html>")
    png_dir = tmp_path / "screens"
    seen = {}
    _fake_pipeline(monkeypatch, seen)

    cli.main([str(html), str(tmp_path / "deck.pptx"),
              "--png-dir", str(png_dir)])

    assert seen["png_dir"] == png_dir
    assert (png_dir / "sentinel").read_text() == "kept only when caller-owned"
