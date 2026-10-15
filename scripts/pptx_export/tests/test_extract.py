"""Geometry extraction tests — run a real headless Chrome over a fixture.

These exercise the actual browser path (no mocks), which is the only honest
way to test rendered geometry.
"""

import os

import pytest

from scripts.pptx_export import extract

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "mini.html")


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    png_dir = tmp_path_factory.mktemp("png")
    return extract.extract_html(FIXTURE, png_dir=str(png_dir)), str(png_dir)


def _texts(slide):
    return [e for e in slide["elements"] if e["kind"] == "text"]


def _figs(slide):
    return [e for e in slide["elements"] if e["kind"] == "figure"]


def test_slide_size_and_count(model):
    m, _ = model
    assert m["slide_px"] == [1280, 720]
    assert len(m["slides"]) == 1


def test_h1_runs_with_inline_bold(model):
    m, _ = model
    slide = m["slides"][0]
    h1 = next(t for t in _texts(slide) if t["tag"] == "h1")
    assert "".join(r["text"] for r in h1["runs"]) == "Hello World"
    world = next(r for r in h1["runs"] if r["text"].strip() == "World")
    assert world["bold"] is True


def test_paragraph_link_and_code_runs(model):
    m, _ = model
    slide = m["slides"][0]
    p = next(t for t in _texts(slide) if t["tag"] == "p")
    link = next(r for r in p["runs"] if r["text"] == "the site")
    assert link["href"] == "https://example.com"
    code = next(r for r in p["runs"] if r["text"] == "make")
    assert code["code"] is True


def test_standalone_html_text_is_extracted_once(model):
    m, _ = model
    matches = [t for t in _texts(m["slides"][0])
               if "First line" in "".join(r["text"] for r in t["runs"])]
    assert len(matches) == 1


def test_br_is_preserved_as_newline(model):
    m, _ = model
    rec = next(t for t in _texts(m["slides"][0])
               if "First line" in "".join(r["text"] for r in t["runs"]))
    assert "".join(r["text"] for r in rec["runs"]) == "First line\nSecond line"


def test_link_overlay_record_emitted_for_image_anchor(model):
    # Text anchors ride along as run hyperlinks; only image-only anchors
    # still get a click-overlay record.
    m, _ = model
    links = [e for e in m["slides"][0]["elements"] if e["kind"] == "link"]
    overlay = next(l for l in links
                   if l["href"] == "https://example.com/imglink")
    assert overlay["bbox"][2] > 0 and overlay["bbox"][3] > 0


def test_list_items_become_separate_bulleted_records(model):
    m, _ = model
    slide = m["slides"][0]
    lis = [t for t in _texts(slide)
           if t["tag"] == "li" and not t.get("ordered")]
    assert [("".join(r["text"] for r in t["runs"])) for t in lis] == [
        "first item",
        "second item",
    ]
    assert all(t["bullet"] for t in lis)


def test_ordered_list_items_carry_numbers(model):
    m, _ = model
    ol = [t for t in _texts(m["slides"][0]) if t.get("ordered")]
    # <ol start="3"> -> 3, 4 ; not green-dot bulleted
    assert [t["number"] for t in ol] == [3, 4]
    assert all(not t["bullet"] for t in ol)


def test_block_level_font_weight_makes_runs_bold(model):
    # h1 is bold by default weight (no <strong> needed); its plain text is bold
    m, _ = model
    h1 = next(t for t in _texts(m["slides"][0]) if t["tag"] == "h1")
    hello = next(r for r in h1["runs"] if r["text"].strip() == "Hello")
    assert hello["bold"] is True


def test_figure_record_has_svg_and_png(model):
    m, png_dir = model
    slide = m["slides"][0]
    figs = _figs(slide)
    assert len(figs) == 1
    fig = figs[0]
    assert "<rect" in fig["svg"]
    # rendered at 200x100 css px
    assert fig["bbox"][2] == pytest.approx(200, abs=2)
    assert fig["bbox"][3] == pytest.approx(100, abs=2)
    assert os.path.isfile(fig["png"])
    assert os.path.getsize(fig["png"]) > 0


def test_browser_visual_creates_backdrop(model):
    m, _ = model
    backdrop = m["slides"][0].get("backdrop")
    assert backdrop and os.path.isfile(backdrop)
    assert os.path.getsize(backdrop) > 0


def test_remote_resource_is_rejected(tmp_path):
    html = tmp_path / "remote.html"
    html.write_text(
        '<html><body><svg data-marpit-svg><foreignObject>'
        '<section><img src="https://example.com/image.png"></section>'
        '</foreignObject></svg></body></html>')
    with pytest.raises(RuntimeError, match="Remote resources are not supported"):
        extract.extract_html(str(html), png_dir=str(tmp_path / "png"))


def test_remote_stylesheet_is_blocked_with_local_fallback(tmp_path, capsys):
    html = tmp_path / "remote-font.html"
    html.write_text(
        '<html><head><link rel="stylesheet" href="https://fonts.example/font.css">'
        '</head><body><svg data-marpit-svg><foreignObject width="1280" height="720">'
        '<section style="width:1280px;height:720px">local text</section>'
        '</foreignObject></svg></body></html>')
    model = extract.extract_html(str(html), png_dir=str(tmp_path / "png"))
    captured = capsys.readouterr()
    assert len(model["slides"]) == 1
    assert "blocked remote stylesheet" in captured.out


def test_nudge_text_clear_of_bars():
    # an H2 subtitle at x=96 overlapping a green bar at x=96 w=8 is shifted right
    m = {"slides": [{"elements": [
        {"kind": "deco_rect", "bbox": [96, 298, 8, 128], "fill": "rgb(59,130,246)"},
        {"kind": "text", "tag": "h2", "bbox": [96, 348, 900, 40], "runs": []},
        {"kind": "text", "tag": "h1", "bbox": [136, 225, 800, 90], "runs": []},
    ]}]}
    extract._nudge_text_clear_of_bars(m)
    h2 = next(e for e in m["slides"][0]["elements"] if e.get("tag") == "h2")
    h1 = next(e for e in m["slides"][0]["elements"] if e.get("tag") == "h1")
    assert h2["bbox"][0] == 136          # shifted to clear the bar (~2.5rem)
    assert h1["bbox"][0] == 136          # already clear -> untouched


def test_anchor_map_links_id_to_slide_index(model):
    m, _ = model
    assert m["anchors"]["hello"] == 0


def test_inline_chip_becomes_chip_record(model):
    m, _ = model
    chips = [e for e in m["slides"][0]["elements"] if e["kind"] == "chip"]
    chip = next(c for c in chips if c["text"] == "VLM")
    assert "59, 130, 246" in chip["fill"]
    # the chip text must NOT also appear as a separate paragraph run
    texts = ["".join(r["text"] for r in t["runs"])
             for t in _texts(m["slides"][0])]
    assert not any(t.strip() == "VLM" for t in texts)


def test_styled_container_becomes_box(model):
    m, _ = model
    boxes = [e for e in m["slides"][0]["elements"] if e["kind"] == "box"]
    assert boxes
    b = boxes[0]
    assert "26, 26, 26" in b["fill"]          # dark fill
    assert "59, 130, 246" in (b.get("accent") or "")  # green left accent
    assert b["radius"] == pytest.approx(8, abs=1)


def _decos(slide, kind):
    return [e for e in slide["elements"] if e["kind"] == kind]


def test_top_accent_extracted_as_deco_rect(model):
    m, _ = model
    rects = _decos(m["slides"][0], "deco_rect")
    top = next(r for r in rects if r["bbox"][1] < 4)  # at the top edge
    assert top["bbox"][2] == pytest.approx(1280, abs=2)  # full width
    assert "59, 130, 246" in top["fill"]


def test_page_number_extracted_as_deco_text(model):
    m, _ = model
    txt = _decos(m["slides"][0], "deco_text")
    assert any(t["text"] == "9" for t in txt)


def test_figure_svg_is_wellformed_xml(model):
    # outerHTML emits HTML named entities (e.g. &nbsp;) that are invalid XML and
    # break SVG importers (Inkscape, LibreOffice, PowerPoint). Must be valid XML.
    import xml.etree.ElementTree as ET
    m, _ = model
    fig = _figs(m["slides"][0])[0]
    ET.fromstring(fig["svg"])  # raises if malformed


def test_all_bboxes_inside_slide(model):
    m, _ = model
    for slide in m["slides"]:
        for e in slide["elements"]:
            x, y, w, h = e["bbox"]
            assert x >= -1 and y >= -1
            assert x + w <= 1281 and y <= 721


def test_remote_media_become_placeholder_records(model):
    # Remote <video>/<iframe> can't be embedded (and must not abort the
    # export); each becomes a linked 'media' placeholder record instead.
    m, _ = model
    media = [e for e in m["slides"][0]["elements"] if e["kind"] == "media"]
    hrefs = {e["href"] for e in media}
    assert hrefs == {"https://example.com/demo.mp4",
                     "https://example.com/embed"}
    for e in media:
        assert e["label"] == "example.com"
        assert e["bbox"][2] > 100 and e["bbox"][3] > 50


def test_inline_font_size_is_captured_per_run(model):
    # Inline elements with their own font-size (chips, footnote markers) must
    # not inherit the block's size in the .pptx.
    m, _ = model
    p = next(t for t in _texts(m["slides"][0])
             if "tinynote" in "".join(r["text"] for r in t["runs"]))
    tiny = next(r for r in p["runs"] if r["text"] == "tinynote")
    assert tiny["size"] == pytest.approx(13, abs=0.5)
    body = next(r for r in p["runs"] if r["text"].startswith("Body"))
    assert body["size"] == pytest.approx(20, abs=0.5)


def test_hover_affordance_chip_excluded_from_text(model):
    # The forensics pill is an HTML hover affordance — its text must not leak
    # into the heading's runs (it used to render at full heading size).
    m, _ = model
    h2 = next(t for t in _texts(m["slides"][0]) if t["tag"] == "h2")
    assert "forensics" not in "".join(r["text"] for r in h2["runs"])
    # .term-style spans are real sentence content and stay in the runs
    p = next(t for t in _texts(m["slides"][0])
             if "jargon" in "".join(r["text"] for r in t["runs"]))
    assert p is not None


def test_data_tips_collected_as_speaker_notes(model):
    m, _ = model
    notes = m["slides"][0].get("notes") or []
    by_head = {n["head"]: n["tip"] for n in notes}
    assert by_head.get("Figure forensics") == "No error bars anywhere."
    assert by_head.get("Jargon") == "A plain-language definition."
    assert by_head.get("Overlay region") == "Explains this part of the figure."


def test_text_anchor_covered_by_run_image_anchor_gets_overlay(model):
    # Anchors with text inside an extracted block become run hyperlinks (no
    # overlay); anchors wrapping only an image still need the overlay shape.
    m, _ = model
    hrefs = {e["href"] for e in m["slides"][0]["elements"]
             if e["kind"] == "link"}
    assert "https://example.com/imglink" in hrefs
    assert "https://example.com" not in hrefs
    p = next(t for t in _texts(m["slides"][0])
             if "the site" in "".join(r["text"] for r in t["runs"]))
    link_run = next(r for r in p["runs"] if r["text"] == "the site")
    assert link_run["href"] == "https://example.com"


def test_list_items_share_list_id_with_spacing(model):
    m, _ = model
    lis = [t for t in _texts(m["slides"][0]) if t["tag"] == "li"
           and not t["ordered"]]
    assert len(lis) == 2
    assert lis[0]["list_id"] and lis[0]["list_id"] == lis[1]["list_id"]
    ols = [t for t in _texts(m["slides"][0]) if t["ordered"]]
    assert ols[0]["list_id"] == ols[1]["list_id"]
    assert ols[0]["list_id"] != lis[0]["list_id"]
