"""Builder tests — assert the produced .pptx has native, editable objects."""

import zipfile

import pytest
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu, Pt

from scripts.pptx_export import build, convert


def _text_rec(text, tag="p", x=72, y=80, w=600, h=40, **kw):
    rec = {
        "kind": "text", "tag": tag, "bbox": [x, y, w, h],
        "runs": [{"text": text, "bold": False, "italic": False,
                  "code": False, "href": None, "color": "rgb(255,255,255)"}],
        "font": "Inter, sans-serif", "size_px": 20.0,
        "color": "rgb(255,255,255)", "align": "left",
        "weight": "400", "line_height": "32px", "bullet": tag == "li",
        "pad_left": 20.8 if tag == "li" else 0.0,
    }
    rec.update(kw)
    return rec


def _model(slides):
    return {"slide_px": [1280, 720], "slides": slides}


def _build(tmp_path, model):
    out = tmp_path / "out.pptx"
    build.build_pptx(model, str(out))
    return str(out)


def test_slide_count(tmp_path):
    model = _model([{"index": 0, "bg": "rgb(17,17,17)", "elements": []},
                    {"index": 1, "bg": "rgb(17,17,17)", "elements": []}])
    prs = Presentation(_build(tmp_path, model))
    assert len(prs.slides) == 2


def test_slide_dimensions_are_16x9(tmp_path):
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": []}])))
    assert prs.slide_width == Emu(12192000)
    assert prs.slide_height == Emu(6858000)


def test_text_box_holds_text_at_position(tmp_path):
    rec = _text_rec("Hello world", x=72, y=80)
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    shapes = list(prs.slides[0].shapes)
    box = next(s for s in shapes if s.has_text_frame)
    assert box.text_frame.text == "Hello world"
    # 72 px * 9525 = 685800 EMU
    assert box.left == pytest.approx(685800, abs=9525)


def test_text_run_newline_becomes_powerpoint_line_break(tmp_path):
    # a real <a:br/> element — a literal \n inside <a:t> renders as a
    # paragraph break and repeats the bullet
    rec = _text_rec("First line\nSecond line", h=70)
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    para = box.text_frame.paragraphs[0]
    assert "<a:br" in para._p.xml
    assert [r.text for r in para.runs] == ["First line", "Second line"]
    assert "\n" not in box.text_frame.text.replace("\v", "")  # no raw newline


def test_bold_and_hyperlink_runs(tmp_path):
    rec = _text_rec("x")
    rec["runs"] = [
        {"text": "bold", "bold": True, "italic": False, "code": False,
         "href": None, "color": "rgb(255,255,255)"},
        {"text": "link", "bold": False, "italic": False, "code": False,
         "href": "https://example.com", "color": "rgb(59,130,246)"},
    ]
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    runs = box.text_frame.paragraphs[0].runs
    assert runs[0].text == "bold" and runs[0].font.bold is True
    # link text is a real hyperlink that keeps its colour, no underline
    assert str(runs[1].font.color.rgb) == "3B82F6"
    assert runs[1].hyperlink.address == "https://example.com"
    assert runs[1].font.underline is False


def test_list_item_uses_green_dot_bullet(tmp_path):
    rec = _text_rec("first item", tag="li")
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    assert box.text_frame.text == "first item"  # no literal glyph in the text
    pPr = box.text_frame.paragraphs[0]._pPr
    xml = pPr.xml
    assert "buChar" in xml
    assert "3B82F6" in xml  # accent bullet color


def test_uppercase_text_transform_uses_caps(tmp_path):
    rec = _text_rec("submit_job", text_transform="uppercase")
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert run._r.get_or_add_rPr().get("cap") == "all"  # displays uppercase
    assert run.text == "submit_job"  # underlying text stays editable


def test_ordered_list_renders_number_not_dot(tmp_path):
    rec = _text_rec("alpha", tag="li", ordered=True, number=3, bullet=False)
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    assert box.text_frame.text == "3. alpha"
    assert "buChar" not in box.text_frame.paragraphs[0]._pPr.xml  # no dot


def test_paragraph_line_spacing_from_line_height(tmp_path):
    rec = _text_rec("hi", line_height="32px", size_px=20.0)
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    # 32 px -> 24 pt exact line height
    assert box.text_frame.paragraphs[0].line_spacing == Pt(24)


def test_translucent_box_fill_keeps_alpha(tmp_path):
    box = {"kind": "box", "bbox": [60, 60, 80, 26],
           "fill": "rgba(59,130,246, 0.15)", "stroke": None, "stroke_w": 0,
           "radius": 13.0}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [box]}])))
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    xml = shp._element.spPr.xml
    assert "3B82F6" in xml
    assert "<a:alpha" in xml and 'val="15000"' in xml  # 0.15 -> 15000


def test_external_link_overlay_shape(tmp_path):
    link = {"kind": "link", "bbox": [72, 80, 100, 24],
            "href": "https://example.com"}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [link]}])))
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert shp.click_action.hyperlink.address == "https://example.com"
    assert "<a:alpha" in shp._element.spPr.xml  # invisible overlay


def test_single_line_heading_disables_wrap(tmp_path):
    # one-line-tall box -> wrap off, so font substitution can't force a rewrap
    rec = _text_rec("Agentic", tag="h1", w=300, h=62, size_px=56.0,
                    line_height="61px")
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    assert box.text_frame.word_wrap is False


def test_multiline_paragraph_keeps_wrap(tmp_path):
    # ~3 lines tall -> keep wrap to preserve intended line breaks
    rec = _text_rec("long wrapped paragraph text", tag="p", w=300, h=100,
                    size_px=20.0, line_height="32px")
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    assert box.text_frame.word_wrap is True


def test_figure_becomes_svg_picture(tmp_path):
    png = tmp_path / "fig.png"
    Image.new("RGBA", (200, 100), (34, 34, 34, 255)).save(png)
    fig = {"kind": "figure", "bbox": [100, 50, 200, 100],
           "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
                  '<rect width="200" height="100" fill="#222"/></svg>',
           "fig_id": "0-0", "png": str(png)}
    out = _build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [fig]}]))
    z = zipfile.ZipFile(out)
    svgs = [n for n in z.namelist() if n.startswith("ppt/media/") and n.endswith(".svg")]
    assert len(svgs) == 1
    slide_xml = z.read("ppt/slides/slide1.xml").decode()
    assert "svgBlip" in slide_xml


def test_overflowing_figure_scaled_to_fit_slide(tmp_path):
    png = tmp_path / "fig.png"
    Image.new("RGBA", (980, 507), (34, 34, 34, 255)).save(png)
    fig = {"kind": "figure", "bbox": [150, 240, 980, 507],  # bottom = 747 > 720
           "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 507">'
                  '<rect width="980" height="507" fill="#222"/></svg>',
           "fig_id": "0-0", "png": str(png)}
    out = _build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [fig]}]))
    prs = Presentation(out)
    pic = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
    # fully on-slide now
    assert pic.top + pic.height <= prs.slide_height + 1
    # aspect ratio preserved
    assert pic.width / pic.height == pytest.approx(980 / 507, rel=0.01)


def test_in_bounds_figure_not_scaled(tmp_path):
    png = tmp_path / "fig.png"
    Image.new("RGBA", (200, 100), (34, 34, 34, 255)).save(png)
    fig = {"kind": "figure", "bbox": [100, 50, 200, 100],
           "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
                  '<rect width="200" height="100" fill="#222"/></svg>',
           "fig_id": "0-0", "png": str(png)}
    out = _build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [fig]}]))
    prs = Presentation(out)
    pic = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
    assert pic.width == Emu(convert.px_to_emu(200))  # untouched


def test_internal_link_overlay_targets_slide(tmp_path):
    link = {"kind": "link", "bbox": [72, 80, 100, 24], "href": "#sec"}
    model = {"slide_px": [1280, 720], "anchors": {"sec": 1}, "slides": [
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [link]},
        {"index": 1, "bg": "rgb(17,17,17)", "elements": []}]}
    out = _build(tmp_path, model)
    prs = Presentation(out)
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert "hlinksldjump" in shp._element.xml      # slide-jump action
    rels = zipfile.ZipFile(out).read("ppt/slides/_rels/slide1.xml.rels").decode()
    assert "slide2.xml" in rels                    # relationship to target slide


def test_chip_is_shape_with_centered_text(tmp_path):
    chip = {"kind": "chip", "bbox": [72, 180, 51, 26],
            "fill": "rgba(59,130,246,0.15)", "radius": 13.0, "text": "VLM",
            "color": "rgb(59,130,246)", "size_px": 13.0, "bold": False}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [chip]}])))
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert shp.text_frame.text == "VLM"          # text lives in the chip shape
    assert "<a:alpha" in shp._element.spPr.xml    # translucent fill


def test_styled_box_is_rounded_rect_behind_text(tmp_path):
    box = {"kind": "box", "bbox": [60, 60, 400, 80], "fill": "rgb(26,26,26)",
           "stroke": "rgb(42,42,42)", "stroke_w": 1.0, "radius": 8.0,
           "accent": "rgb(59,130,246)", "accent_w": 3.0}
    txt = _text_rec("hi", x=70, y=70)
    model = _model([{"index": 0, "bg": "rgb(17,17,17)",
                     "elements": [box, txt]}])
    prs = Presentation(_build(tmp_path, model))
    shapes = list(prs.slides[0].shapes)
    autoshapes = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]
    fill_box = next(s for s in autoshapes
                    if str(s.fill.fore_color.rgb) == "1A1A1A")
    txt_box = next(s for s in shapes
                   if s.has_text_frame and s.text_frame.text == "hi")
    # box drawn before (behind) the text
    assert shapes.index(fill_box) < shapes.index(txt_box)


def test_deco_rect_renders_as_filled_shape(tmp_path):
    deco = {"kind": "deco_rect", "bbox": [0, 0, 1280, 3],
            "fill": "rgb(59,130,246)", "radius": 0}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [deco]}])))
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert str(shp.fill.fore_color.rgb) == "3B82F6"
    assert shp.width == Emu(convert.px_to_emu(1280))


def test_deco_text_renders_page_number(tmp_path):
    deco = {"kind": "deco_text", "bbox": [48, 690, 40, 18], "text": "9",
            "color": "rgb(102,102,102)", "size_px": 13.6}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [deco]}])))
    box = next(s for s in prs.slides[0].shapes
               if s.has_text_frame and s.text_frame.text == "9")
    assert box.left == Emu(convert.px_to_emu(48))


def test_deco_image_renders_picture(tmp_path):
    import base64 as _b64
    import io as _io
    buf = _io.BytesIO()
    Image.new("RGBA", (132, 26), (59, 130, 246, 255)).save(buf, "PNG")
    uri = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
    deco = {"kind": "deco_image", "bbox": [1100, 662, 132, 26], "data_uri": uri}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [deco]}])))
    pic = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
    assert pic.left == Emu(convert.px_to_emu(1100))


def test_backdrop_is_full_slide_below_text_without_duplicate_boxes(tmp_path):
    backdrop = tmp_path / "backdrop.png"
    Image.new("RGB", (1280, 720), (17, 17, 17)).save(backdrop)
    deco = {"kind": "deco_rect", "bbox": [0, 0, 1280, 3],
            "fill": "rgb(59,130,246)", "radius": 0}
    box = {"kind": "box", "bbox": [60, 60, 400, 80],
           "fill": "rgb(26,26,26)", "stroke": None, "stroke_w": 0}
    txt = _text_rec("editable", x=70, y=70)
    slide = {"index": 0, "bg": "rgb(17,17,17)",
             "backdrop": str(backdrop), "elements": [deco, box, txt]}
    prs = Presentation(_build(tmp_path, _model([slide])))
    shapes = list(prs.slides[0].shapes)

    assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE
    assert shapes[0].left == 0 and shapes[0].top == 0
    assert shapes[0].width == prs.slide_width
    assert shapes[0].height == prs.slide_height
    assert any(s.has_text_frame and s.text == "editable" for s in shapes)
    assert not any(s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE for s in shapes)


def test_background_color_set(tmp_path):
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": []}])))
    fill = prs.slides[0].background.fill
    assert str(fill.fore_color.rgb) == "111111"


def test_media_becomes_playable_web_video(tmp_path):
    rec = {"kind": "media", "bbox": [100, 100, 320, 180],
           "href": "https://example.com/demo.mp4", "label": "example.com"}
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    slide = prs.slides[0]
    # the videoFile element makes python-pptx classify the shape as MEDIA
    pic = next(s for s in slide.shapes
               if s.shape_type == MSO_SHAPE_TYPE.MEDIA)
    assert pic.left == Emu(convert.px_to_emu(100))
    xml = pic._element.xml
    assert "videoFile" in xml
    assert "webVideoPr" in xml and "example.com/demo.mp4" in xml
    # the video URL is an external relationship of the slide part
    assert any(r.target_ref == "https://example.com/demo.mp4" and r.is_external
               for r in slide.part.rels.values())


def test_speaker_notes_written_from_hover_tips(tmp_path):
    slide_rec = {"index": 0, "bg": "rgb(17,17,17)", "elements": [],
                 "notes": [{"head": "Figure forensics",
                            "tip": "No error bars anywhere."},
                           {"head": "Jargon", "tip": "A definition."}]}
    prs = Presentation(_build(tmp_path, _model([slide_rec])))
    text = prs.slides[0].notes_slide.notes_text_frame.text
    assert "Figure forensics: No error bars anywhere." in text
    assert "Jargon: A definition." in text


def test_inter_fonts_are_embedded(tmp_path):
    out = _build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": []}]))
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert any(n.startswith("ppt/fonts/") and n.endswith(".fntdata")
                   for n in names)
        pres = z.read("ppt/presentation.xml").decode()
    assert "embeddedFontLst" in pres and 'typeface="Inter"' in pres
    assert 'embedTrueTypeFonts="1"' in pres


def test_run_level_font_size_overrides_block_size(tmp_path):
    rec = _text_rec("x")
    rec["runs"] = [
        {"text": "big ", "bold": False, "italic": False, "code": False,
         "href": None, "color": "rgb(255,255,255)"},
        {"text": "small", "bold": False, "italic": False, "code": False,
         "href": None, "color": "rgb(255,255,255)", "size": 10.0},
    ]
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    runs = box.text_frame.paragraphs[0].runs
    assert runs[0].font.size == Pt(convert.px_to_pt(20.0))  # block default
    assert runs[1].font.size == Pt(convert.px_to_pt(10.0))  # run override


def test_embedded_fonts_have_correct_style_bits(tmp_path):
    # The vendored Inter faces are static instances with regular-style bits;
    # PowerPoint refuses to import a "Bold" face whose OS/2/head bits say
    # regular. The embedder must normalize the bits per slot.
    from fontTools.ttLib import TTFont
    out = _build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": []}]))
    import io as _io
    with zipfile.ZipFile(out) as z:
        pres = z.read("ppt/presentation.xml").decode()
        # font2 is the bold slot (see _embed_fonts slot order)
        bold = TTFont(_io.BytesIO(z.read("ppt/fonts/font2.fntdata")))
        italic = TTFont(_io.BytesIO(z.read("ppt/fonts/font3.fntdata")))
        regular = TTFont(_io.BytesIO(z.read("ppt/fonts/font1.fntdata")))
    assert bold["OS/2"].fsSelection & 0x20          # BOLD set
    assert not bold["OS/2"].fsSelection & 0x40      # REGULAR clear
    assert bold["head"].macStyle & 0b01
    assert italic["OS/2"].fsSelection & 0x01        # ITALIC set
    assert italic["head"].macStyle & 0b10
    assert regular["OS/2"].fsSelection & 0x40       # REGULAR set
    assert not regular["OS/2"].fsSelection & 0x21


def test_numeric_internal_link_targets_slide_number(tmp_path):
    # Marp decks link slide jumps as #N (1-based slide number); the bare
    # render has no element with that id, so resolve numerically.
    link = {"kind": "link", "bbox": [72, 80, 100, 24], "href": "#3"}
    model = {"slide_px": [1280, 720], "anchors": {}, "slides": [
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [link]},
        {"index": 1, "bg": "rgb(17,17,17)", "elements": []},
        {"index": 2, "bg": "rgb(17,17,17)", "elements": []}]}
    prs = Presentation(_build(tmp_path, model))
    shp = next(s for s in prs.slides[0].shapes
               if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert "jump" in shp._element.xml  # ppaction://hlinksldjump
    rid = shp._element.nvSpPr.cNvPr.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}hlinkClick"
    ).get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    target = prs.slides[0].part.rels[rid].target_part
    assert target is prs.slides[2].part


def test_note_head_is_bold(tmp_path):
    slide_rec = {"index": 0, "bg": "rgb(17,17,17)", "elements": [],
                 "notes": [{"head": "Jargon", "tip": "A definition."}]}
    prs = Presentation(_build(tmp_path, _model([slide_rec])))
    para = prs.slides[0].notes_slide.notes_text_frame.paragraphs[0]
    assert para.runs[0].text == "Jargon: " and para.runs[0].font.bold is True
    assert para.runs[1].text == "A definition."


def test_list_items_merge_into_one_frame(tmp_path):
    li1 = _text_rec("first", tag="li", y=100, list_id="0-0", margin_bottom=8.0)
    li2 = _text_rec("second", tag="li", y=140, list_id="0-0", margin_bottom=8.0)
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [li1, li2]}])))
    boxes = [s for s in prs.slides[0].shapes if s.has_text_frame]
    assert len(boxes) == 1
    tf = boxes[0].text_frame
    assert [p.text for p in tf.paragraphs] == ["first", "second"]
    assert tf.paragraphs[0].space_after == Pt(convert.px_to_pt(8.0))
    for p in tf.paragraphs:
        assert "buChar" in p._pPr.xml  # both keep the green dot
    assert boxes[0].top == Emu(convert.px_to_emu(100))


def test_text_run_external_hyperlink_kept_styled(tmp_path):
    rec = _text_rec("x")
    rec["runs"] = [{"text": "link", "bold": False, "italic": False,
                    "code": False, "href": "https://example.com",
                    "color": "rgb(59,130,246)"}]
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]}])))
    box = next(s for s in prs.slides[0].shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert run.hyperlink.address == "https://example.com"
    assert str(run.font.color.rgb) == "3B82F6"   # explicit colour kept
    assert run.font.underline is False           # no forced underline


def test_text_run_internal_link_jumps_to_slide(tmp_path):
    rec = _text_rec("x")
    rec["runs"] = [{"text": "s2", "bold": False, "italic": False,
                    "code": False, "href": "#2",
                    "color": "rgb(59,130,246)"}]
    prs = Presentation(_build(tmp_path, _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": [rec]},
        {"index": 1, "bg": "rgb(17,17,17)", "elements": []}])))
    slide = prs.slides[0]
    box = next(s for s in slide.shapes if s.has_text_frame)
    r = box.text_frame.paragraphs[0].runs[0]._r
    hl = r.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}hlinkClick")
    assert hl is not None and hl.get("action") == "ppaction://hlinksldjump"
    rid = hl.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    assert slide.part.rels[rid].target_part is prs.slides[1].part


def test_shared_chrome_moves_to_slide_layout(tmp_path):
    def decos():
        return [
            {"kind": "deco_rect", "bbox": [0, 0, 1280, 3],
             "fill": "rgb(59,130,246)", "radius": 0},
            {"kind": "deco_text", "bbox": [48, 690, 40, 18], "text": "2",
             "color": "rgb(102,102,102)", "size_px": 13.6},
        ]
    model = _model([
        {"index": 0, "bg": "rgb(17,17,17)", "elements": decos()},
        {"index": 1, "bg": "rgb(17,17,17)", "elements": decos()},
        {"index": 2, "bg": "rgb(17,17,17)", "elements": []},  # lead-style
    ])
    prs = Presentation(_build(tmp_path, model))
    assert len(prs.slides) == 3  # the scratch slide is gone again
    s0 = prs.slides[0]
    # chrome lives on the layout, not the slide
    assert not any(s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
                   for s in s0.shapes)
    layout = s0.slide_layout
    assert any(s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
               for s in layout.shapes)
    assert 'type="slidenum"' in layout._element.xml  # auto page number
    assert len(list(layout.placeholders)) == 0       # stripped
    # the deco-less slide is NOT on the chrome layout
    assert prs.slides[2].slide_layout is not layout
