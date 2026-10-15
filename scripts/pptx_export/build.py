"""Build an editable .pptx from a slide model.

Text records become native text boxes; figure records become SVG pictures
(PNG fallback + an ``asvg:svgBlip`` extension) so PowerPoint shows the SVG and
can ungroup it into native, individually-movable shapes.
"""

import base64
import io
import os
import re

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from . import convert

_ACCENT = "3B82F6"

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"

_MONO_FONT = "Consolas"  # installed monospace; JetBrains Mono isn't embedded
_HORIZONTAL_WS = re.compile(r"[^\S\n]+")
_AROUND_NEWLINE = re.compile(r" *\n *")

_NS_P15 = "http://schemas.microsoft.com/office/powerpoint/2012/main"
_WEB_VIDEO_EXT_URI = "{C809E66F-F1BF-436E-B5F7-EEA9579F0CBA}"
_VIDEO_RT = ("http://schemas.openxmlformats.org/officeDocument"
             "/2006/relationships/video")
_FONT_RT = ("http://schemas.openxmlformats.org/officeDocument"
            "/2006/relationships/font")
_FONTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts"))


def _first_font(family: str) -> str:
    """First family name from a CSS font-family list, quotes stripped."""
    first = (family or "").split(",")[0].strip()
    return first.strip("'\"") or "Inter"


def _emu(px: float) -> Emu:
    return Emu(convert.px_to_emu(px))


def _line_height_px(rec: dict):
    """Computed line-height in px, or None when not a px value ('normal')."""
    lh_raw = (rec.get("line_height") or "").strip()
    if lh_raw.endswith("px"):
        try:
            return float(lh_raw[:-2])
        except ValueError:
            return None
    return None


def _is_single_line(rec: dict) -> bool:
    """True if the element rendered on one line.

    Such boxes get word-wrap OFF so a substituted (wider) font can't force a
    spurious rewrap that overflows the box. Multi-line blocks keep wrap so their
    intended line breaks survive.
    """
    line_h = _line_height_px(rec) or rec.get("size_px", 16.0) * 1.2
    return rec["bbox"][3] < line_h * 1.5


def _set_number_indent(para, pad_left_px: float):
    """Hanging indent for an ordered-list item; the number is explicit run text
    (auto-numbering would restart at 1 in each separate text box)."""
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", str(convert.px_to_emu(pad_left_px)))
    pPr.set("indent", str(-convert.px_to_emu(pad_left_px)))
    pPr.append(pPr.makeelement(qn("a:buNone"), {}))


def _set_green_bullet(para, pad_left_px: float):
    """Native bullet styled as the theme's small green dot, hanging-indented so
    the text aligns where the CSS padding-left put it."""
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", str(convert.px_to_emu(pad_left_px)))
    pPr.set("indent", str(-convert.px_to_emu(pad_left_px)))
    buClr = pPr.makeelement(qn("a:buClr"), {})
    buClr.append(buClr.makeelement(qn("a:srgbClr"), {"val": _ACCENT}))
    buSz = pPr.makeelement(qn("a:buSzPct"), {"val": "40000"})
    buFont = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
    buChar = pPr.makeelement(qn("a:buChar"), {"char": "●"})
    for el in (buClr, buSz, buFont, buChar):  # schema order
        pPr.append(el)


def build_pptx(model: dict, out_path: str) -> None:
    prs = Presentation()
    prs.slide_width = _emu(model["slide_px"][0])
    prs.slide_height = _emu(model["slide_px"][1])
    blank = prs.slide_layouts[6]
    svg_counter = [0]
    slide_w, slide_h = model["slide_px"]
    pending_links = []      # (shape, slug) for #internal-link overlays
    pending_run_links = []  # (slide, run, slug) for #internal run hyperlinks
    slides = []

    # Slide chrome (top bar, logo, page number) shared by most slides moves to
    # a slide layout — one editable master copy, and the page number becomes a
    # real slidenum field that renumbers itself.
    chrome_decos = _find_standard_chrome(model)
    chrome_layout = None
    chrome_sig = None
    if chrome_decos:
        chrome_layout = prs.slide_layouts[5]
        _prepare_chrome_layout(prs, chrome_layout, chrome_decos)
        chrome_sig = {_deco_signature(d) for d in chrome_decos}

    for slide_rec in model["slides"]:
        decos = [e for e in slide_rec["elements"]
                 if e["kind"].startswith("deco_")]
        has_backdrop = bool(slide_rec.get("backdrop"))
        use_chrome = (chrome_layout is not None and not has_backdrop and
                      {_deco_signature(d) for d in decos} == chrome_sig)
        slide = prs.slides.add_slide(chrome_layout if use_chrome else blank)
        slides.append(slide)
        _set_background(slide, slide_rec.get("bg"))
        if has_backdrop:
            slide.shapes.add_picture(slide_rec["backdrop"], 0, 0,
                                     prs.slide_width, prs.slide_height)
        elif not use_chrome:
            for el in decos:  # logo, page number, bars
                _add_deco(slide, el)
        for el in slide_rec["elements"]:  # container boxes / chips / media
            if el["kind"] == "box" and not has_backdrop:
                _add_box(slide, el)
            elif el["kind"] == "chip":
                _add_chip(slide, el)
            elif el["kind"] == "media":  # blank in a backdrop too — always draw
                _add_media(slide, el)
        for el in _merge_lists(slide_rec["elements"]):
            if el["kind"] == "text":
                _add_text(slide, el, pending_run_links)
            elif el["kind"] == "text_list":
                _add_text_list(slide, el, pending_run_links)
            elif el["kind"] == "figure":
                _add_figure(slide, el, svg_counter, slide_w, slide_h)
        for el in slide_rec["elements"]:  # click overlays on top
            if el["kind"] == "link":
                _add_link_overlay(slide, el, pending_links)
        _add_notes(slide, slide_rec.get("notes"))

    anchors = model.get("anchors", {})
    _wire_internal_links(pending_links, slides, anchors)
    _wire_internal_run_links(pending_run_links, slides, anchors)
    _set_theme_link_colors(prs)
    _embed_fonts(prs)
    cp = prs.core_properties  # python-pptx's template ships its own author/editor names
    cp.author = cp.last_modified_by = "agentic-slides"
    cp.comments = cp.keywords = cp.subject = ""
    cp.title = os.path.basename(out_path).split(".")[0]
    prs.save(out_path)


def _set_theme_link_colors(prs):
    """Theme hlink/folHlink -> deck green. Runs carry explicit fills, which
    modern PowerPoint honours on hyperlink text; the theme colour is the
    fallback for viewers that force theme link colours (and kills the purple
    followed-link tint)."""
    try:
        theme = prs.slide_masters[0].part.part_related_by(RT.THEME)
    except (KeyError, ValueError):
        return
    root = etree.fromstring(theme.blob)
    changed = False
    for tag in ("hlink", "folHlink"):
        el = root.find(f".//{{{_NS_A}}}clrScheme/{{{_NS_A}}}{tag}")
        if el is None:
            continue
        for child in list(el):
            el.remove(child)
        etree.SubElement(el, qn("a:srgbClr")).set("val", _ACCENT)
        changed = True
    if changed:
        theme._blob = etree.tostring(root, xml_declaration=True,
                                     encoding="UTF-8", standalone=True)


def _deco_signature(rec):
    """Identity of a chrome element across slides (page-number text and the
    logo's pixels excluded — geometry and styling carry the identity)."""
    x, y, w, h = (round(v) for v in rec["bbox"])
    return (rec["kind"], x, y, w, h, rec.get("fill"), rec.get("color"),
            round(rec.get("size_px") or 0))


def _find_standard_chrome(model):
    """The deco set shared by the majority of slides (≥2 slides), as the deco
    records of the first slide carrying it — or None."""
    counts = {}
    first = {}
    for slide in model["slides"]:
        if slide.get("backdrop"):
            continue  # chrome is baked into the screenshot there
        decos = [e for e in slide["elements"] if e["kind"].startswith("deco_")]
        if not decos:
            continue
        sig = frozenset(_deco_signature(d) for d in decos)
        counts[sig] = counts.get(sig, 0) + 1
        first.setdefault(sig, decos)
    if not counts:
        return None
    sig, n = max(counts.items(), key=lambda kv: kv[1])
    return first[sig] if n >= 2 else None


def _prepare_chrome_layout(prs, layout, decos):
    """Strip the layout's placeholders, then move the chrome shapes onto it.

    Shapes are built with the normal slide API on a scratch slide and their
    XML is reparented into the layout (python-pptx has no layout.add_*);
    picture relationships are re-created on the layout part, and the page
    number becomes a ``slidenum`` field so it renumbers automatically."""
    from copy import deepcopy
    spTree = layout.shapes._spTree
    for sp in list(spTree):
        if sp.find(".//" + qn("p:ph")) is not None:
            spTree.remove(sp)

    scratch = prs.slides.add_slide(prs.slide_layouts[6])
    for rec in decos:
        shp = _add_deco(scratch, rec)
        if shp is None:
            continue
        el = shp._element
        if rec["kind"] == "deco_text":  # page number -> auto slidenum field
            r_el = el.find(".//" + qn("a:r"))
            fld = r_el.makeelement(qn("a:fld"), {
                "id": "{5F7B2A19-1B4E-4E52-8E5C-2A9C7D0B41F6}",
                "type": "slidenum"})
            rPr = r_el.find(qn("a:rPr"))
            if rPr is not None:
                fld.append(deepcopy(rPr))
            t = etree.SubElement(fld, qn("a:t"))
            t.text = "1"
            r_el.getparent().replace(r_el, fld)
        elif rec["kind"] == "deco_image":  # re-relate the image to the layout
            blip = el.find(".//" + qn("a:blip"))
            old_rid = blip.get(qn("r:embed"))
            image_part = scratch.part.rels[old_rid].target_part
            blip.set(qn("r:embed"), layout.part.relate_to(image_part,
                                                          RT.IMAGE))
        spTree.append(el)

    sldIdLst = prs.slides._sldIdLst  # drop the scratch slide again
    sldId = sldIdLst[-1]
    prs.part.drop_rel(sldId.get(qn("r:id")))
    sldIdLst.remove(sldId)


def _merge_lists(elements):
    """Consecutive items of the same list -> one ``text_list`` record, so the
    builder emits a single text frame with one paragraph per item."""
    out, i = [], 0
    while i < len(elements):
        el = elements[i]
        if el["kind"] == "text" and el.get("list_id"):
            items = []
            j = i
            while (j < len(elements) and elements[j]["kind"] == "text"
                   and elements[j].get("list_id") == el["list_id"]):
                items.append(elements[j])
                j += 1
            if len(items) > 1:
                x0 = min(b["bbox"][0] for b in items)
                y0 = min(b["bbox"][1] for b in items)
                x1 = max(b["bbox"][0] + b["bbox"][2] for b in items)
                y1 = max(b["bbox"][1] + b["bbox"][3] for b in items)
                out.append({"kind": "text_list",
                            "bbox": [x0, y0, x1 - x0, y1 - y0],
                            "items": items})
            else:
                out.append(el)
            i = j
        else:
            out.append(el)
            i += 1
    return out


def _add_notes(slide, notes):
    """Hover-tooltip texts (HTML-only affordances) as speaker notes,
    one paragraph per tip with the explained term in bold."""
    seen, entries = set(), []
    for n in notes or []:
        key = (n["head"], n["tip"])
        if key in seen:
            continue
        seen.add(key)
        entries.append(n)
    if not entries:
        return
    tf = slide.notes_slide.notes_text_frame
    for i, n in enumerate(entries):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        head = p.add_run()
        head.text = f"{n['head']}: "
        head.font.bold = True
        tip = p.add_run()
        tip.text = n["tip"]


_STYLE_BITS = {  # slot -> (fsSelection bits to set, to clear, macStyle)
    "regular":    (0x0040, 0x0021, 0b00),
    "bold":       (0x0020, 0x0041, 0b01),
    "italic":     (0x0001, 0x0060, 0b10),
    "boldItalic": (0x0021, 0x0040, 0b11),
}


def _font_bytes(path: str, slot: str) -> bytes:
    """Font file bytes with OS/2.fsSelection / head.macStyle matching *slot*.

    The vendored Inter faces are static instances cut from the variable font
    and ship regular-style bits on every face; PowerPoint then sees two fonts
    claiming regular "Inter" and refuses to import the bold/italic slots."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        with open(path, "rb") as fh:  # degraded: bits stay as shipped
            return fh.read()
    f = TTFont(path)
    set_bits, clear_bits, mac = _STYLE_BITS[slot]
    f["OS/2"].fsSelection = (f["OS/2"].fsSelection & ~clear_bits) | set_bits
    f["head"].macStyle = mac
    buf = io.BytesIO()
    f.save(buf)
    return buf.getvalue()


def _embed_fonts(prs):
    """Embed the vendored Inter faces (fntdata parts + ``p:embeddedFontLst``)
    so PowerPoint without Inter doesn't substitute a wider font and reflow or
    autofit-shrink every text box differently."""
    slots = [("regular", "Inter-Regular.ttf"), ("bold", "Inter-Bold.ttf"),
             ("italic", "Inter-Italic.ttf"),
             ("boldItalic", "Inter-BoldItalic.ttf")]
    pres_part = prs.part
    entries = []
    for i, (slot, fname) in enumerate(slots, start=1):
        path = os.path.join(_FONTS_DIR, fname)
        if not os.path.isfile(path):
            continue
        part = Part(PackURI(f"/ppt/fonts/font{i}.fntdata"),
                    "application/x-fontdata", pres_part.package,
                    _font_bytes(path, slot))
        entries.append((slot, pres_part.relate_to(part, _FONT_RT)))
    if not entries:
        return
    pres_el = pres_part._element
    pres_el.set("embedTrueTypeFonts", "1")
    lst = pres_el.makeelement(qn("p:embeddedFontLst"), {})
    ef = etree.SubElement(lst, qn("p:embeddedFont"))
    font = etree.SubElement(ef, qn("p:font"))
    font.set("typeface", "Inter")
    for slot, rId in entries:
        el = etree.SubElement(ef, qn(f"p:{slot}"))
        el.set(qn("r:id"), rId)
    # schema position: directly after p:notesSz
    pres_el.find(qn("p:notesSz")).addnext(lst)


def _add_link_overlay(slide, rec, pending_links):
    x, y, w, h = rec["bbox"]
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                 _emu(x), _emu(y), _emu(w), _emu(h))
    shp.shadow.inherit = False
    shp.fill.solid()  # fully transparent but still clickable across its area
    shp.fill.fore_color.rgb = RGBColor.from_string("FFFFFF")
    srgb = shp._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    srgb.append(srgb.makeelement(qn("a:alpha"), {"val": "0"}))
    shp.line.fill.background()
    href = rec["href"]
    if href.startswith("#"):
        pending_links.append((shp, href[1:]))
    else:
        shp.click_action.hyperlink.address = href


def _resolve_anchor(slug, slides, anchors):
    idx = anchors.get(slug)
    if idx is None and slug.isdigit():
        idx = int(slug) - 1  # Marp-style #N slide-number link (1-based)
    return idx if idx is not None and 0 <= idx < len(slides) else None


def _wire_internal_links(pending_links, slides, anchors):
    for shp, slug in pending_links:
        idx = _resolve_anchor(slug, slides, anchors)
        if idx is None:
            continue  # dangling anchor — overlay stays inert
        shp.click_action.target_slide = slides[idx]


def _wire_internal_run_links(pending_run_links, slides, anchors):
    """#slug run hyperlinks -> slide-jump actions (needs all slides built)."""
    for slide, run, slug in pending_run_links:
        idx = _resolve_anchor(slug, slides, anchors)
        if idx is None:
            continue  # dangling anchor — run stays plain text
        rId = slide.part.relate_to(slides[idx].part, RT.SLIDE)
        rPr = run._r.get_or_add_rPr()
        hl = rPr.makeelement(qn("a:hlinkClick"), {})
        hl.set(qn("r:id"), rId)
        hl.set("action", "ppaction://hlinksldjump")
        rPr.append(hl)


def _set_background(slide, bg_css):
    # A transparent section composites over the browser's white page — never
    # leave the slide on the presentation default (renders black in some
    # viewers), always set an explicit fill.
    hexv = convert.parse_color(bg_css) or "FFFFFF"
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(hexv)


def _add_deco(slide, rec):
    """Native slide chrome: top accent / divider bar (rect), logo (picture),
    page number (text box)."""
    x, y, w, h = rec["bbox"]
    kind = rec["kind"]
    if kind == "deco_rect":
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                     _emu(x), _emu(y), _emu(w), _emu(h))
        shp.shadow.inherit = False
        radius = rec.get("radius", 0)
        if min(w, h):
            shp.adjustments[0] = max(0.0, min(0.5, radius / min(w, h)))
        hexv = convert.parse_color(rec.get("fill"))
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(hexv or "FFFFFF")
        shp.line.fill.background()
        return shp
    elif kind == "deco_image":
        from PIL import Image
        data = base64.b64decode(rec["data_uri"].split(",", 1)[1])
        iw, ih = Image.open(io.BytesIO(data)).size
        # CSS background-size:contain + background-position:right center —
        # fit inside the box preserving aspect, right-aligned, vertically centered
        if iw / ih > w / h:
            nw, nh = w, w * ih / iw
        else:
            nw, nh = h * iw / ih, h
        nx, ny = x + (w - nw), y + (h - nh) / 2
        return slide.shapes.add_picture(io.BytesIO(data),
                                        _emu(nx), _emu(ny), _emu(nw), _emu(nh))
    elif kind == "deco_text":
        box = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
        tf = box.text_frame
        tf.word_wrap = False
        for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, side, Emu(0))
        r = tf.paragraphs[0].add_run()
        r.text = rec["text"]
        r.font.size = Pt(convert.px_to_pt(rec["size_px"]))
        r.font.name = "Inter"
        color = convert.parse_color(rec.get("color"))
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        return box
    return None


def _add_chip(slide, rec):
    """Inline tag/pill: a rounded rect with centered text, fill kept translucent."""
    from pptx.enum.text import MSO_ANCHOR
    x, y, w, h = rec["bbox"]
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 _emu(x), _emu(y), _emu(w), _emu(h))
    shp.shadow.inherit = False
    if min(w, h):
        shp.adjustments[0] = max(0.0, min(0.5, rec.get("radius", 0) / min(w, h)))
    fill = convert.parse_color(rec.get("fill"))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(fill)
        alpha = convert.parse_alpha(rec.get("fill"))
        if alpha < 1.0:
            srgb = shp._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
            srgb.append(srgb.makeelement(
                qn("a:alpha"), {"val": str(int(round(alpha * 100000)))}))
    else:
        shp.fill.background()
    shp.line.fill.background()
    tf = shp.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Emu(0))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    transform = (rec.get("text_transform") or "none").lower()
    text = rec["text"]
    if transform == "lowercase":
        text = text.lower()
    elif transform == "capitalize":
        text = text.title()
    r.text = text
    if transform == "uppercase":
        r._r.get_or_add_rPr().set("cap", "all")
    r.font.size = Pt(convert.px_to_pt(rec["size_px"]))
    r.font.name = "Inter"
    r.font.bold = bool(rec.get("bold"))
    color = convert.parse_color(rec.get("color"))
    if color:
        r.font.color.rgb = RGBColor.from_string(color)


def _media_poster(rec) -> io.BytesIO:
    """Poster PNG for a web-video shape: dark tile, play glyph, host label."""
    from PIL import Image, ImageDraw, ImageFont
    _, _, w, h = rec["bbox"]
    W, H = max(64, int(w * 2)), max(36, int(h * 2))  # 2x for sharpness
    img = Image.new("RGB", (W, H), (10, 14, 23))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=(30, 58, 102), width=2)
    cx, cy, s = W // 2, H // 2 - H // 12, min(W, H) // 6
    d.polygon([(cx - s // 2, cy - s), (cx - s // 2, cy + s), (cx + s, cy)],
              fill=(59, 130, 246))
    label = rec.get("label") or "video"
    try:
        fnt = ImageFont.truetype(
            os.path.join(_FONTS_DIR, "Inter-Regular.ttf"),
            max(16, min(W, H) // 10))
    except OSError:
        fnt = ImageFont.load_default()
    tw = d.textlength(label, font=fnt)
    d.text(((W - tw) / 2, cy + s + H // 20), label, font=fnt,
           fill=(214, 217, 220))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def _add_media(slide, rec):
    """Remote video/iframe embed as a PowerPoint online video: a poster
    picture carrying ``a:videoFile`` (external URL relationship) plus the
    ``p15:webVideoPr`` extension, so slideshow mode plays it in place.
    Viewers without web-video support show the poster tile."""
    x, y, w, h = rec["bbox"]
    pic = slide.shapes.add_picture(_media_poster(rec),
                                   _emu(x), _emu(y), _emu(w), _emu(h))
    rId = slide.part.relate_to(rec["href"], _VIDEO_RT, is_external=True)
    nvPr = pic._element.nvPicPr.nvPr
    vf = nvPr.makeelement(qn("a:videoFile"), {})
    vf.set(qn("r:link"), rId)
    nvPr.insert(0, vf)
    extLst = etree.SubElement(nvPr, qn("p:extLst"))
    ext = etree.SubElement(extLst, qn("p:ext"))
    ext.set("uri", _WEB_VIDEO_EXT_URI)
    wv = etree.SubElement(ext, f"{{{_NS_P15}}}webVideoPr",
                          nsmap={"p15": _NS_P15})
    wv.set("embeddedHtml",
           f'<iframe src="{rec["href"]}" width="{int(w)}" height="{int(h)}" '
           'frameborder="0" allowfullscreen="1"></iframe>')


def _add_box(slide, rec):
    x, y, w, h = rec["bbox"]
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 _emu(x), _emu(y), _emu(w), _emu(h))
    shp.shadow.inherit = False
    minside = min(w, h)
    if minside:
        shp.adjustments[0] = max(0.0, min(0.5, rec.get("radius", 0) / minside))
    fill = convert.parse_color(rec.get("fill"))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(fill)
        alpha = convert.parse_alpha(rec.get("fill"))
        if alpha < 1.0:  # translucent tint (e.g. chips) — keep transparency
            srgb = shp._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
            srgb.append(srgb.makeelement(
                qn("a:alpha"), {"val": str(int(round(alpha * 100000)))}))
    else:
        shp.fill.background()
    stroke = convert.parse_color(rec.get("stroke"))
    if stroke and rec.get("stroke_w", 0) > 0:
        shp.line.color.rgb = RGBColor.from_string(stroke)
        shp.line.width = Pt(convert.px_to_pt(rec["stroke_w"]))
    else:
        shp.line.fill.background()

    accent = convert.parse_color(rec.get("accent"))
    if accent and rec.get("accent_w", 0) > 0:
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, _emu(x), _emu(y),
                                     _emu(rec["accent_w"]), _emu(h))
        bar.shadow.inherit = False
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor.from_string(accent)
        bar.line.fill.background()


def _fill_list_paragraph(para, rec, slide, pending_run_links):
    """One list item as a paragraph: alignment, spacing, bullet/number, runs."""
    para.alignment = convert.map_align(rec.get("align"))
    line_h = _line_height_px(rec)
    if line_h:
        para.line_spacing = Pt(convert.px_to_pt(line_h))
    mb = rec.get("margin_bottom") or 0
    if mb:
        para.space_after = Pt(convert.px_to_pt(mb))
    if rec.get("ordered"):
        _set_number_indent(para, rec.get("pad_left", 0.0))
    elif rec.get("bullet"):
        _set_green_bullet(para, rec.get("pad_left", 0.0))
    _add_runs(para, rec, slide, pending_run_links)


def _add_text_list(slide, rec, pending_run_links):
    """A whole <ul>/<ol> as ONE text frame, one paragraph per item — so the
    list edits/reflows as a unit and any autofit scales it uniformly."""
    x, y, w, h = rec["bbox"]
    box = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
    tf = box.text_frame
    tf.word_wrap = True
    # No autofit: geometry is browser-exact and fonts are embedded. Viewers
    # recompute autofit with their own metrics and mis-shrink whole frames.
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Emu(0))
    items = rec["items"]
    for i, item in enumerate(items):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _fill_list_paragraph(para, item, slide, pending_run_links)


def _add_text(slide, rec, pending_run_links):
    x, y, w, h = rec["bbox"]
    box = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
    tf = box.text_frame
    tf.word_wrap = not _is_single_line(rec)
    # No autofit: geometry is browser-exact and fonts are embedded. Viewers
    # recompute autofit with their own metrics and mis-shrink whole frames.
    tf.auto_size = MSO_AUTO_SIZE.NONE
    # Inset text by the element's CSS padding for padded containers (code blocks,
    # callouts, table cells); others have no padding so this is a no-op.
    pad = rec.get("pad") or [0, 0, 0, 0]  # top, right, bottom, left
    inset = rec.get("tag") in ("pre", "blockquote", "td", "th")
    tf.margin_top = Emu(convert.px_to_emu(pad[0] if inset else 0))
    tf.margin_right = Emu(convert.px_to_emu(pad[1] if inset else 0))
    tf.margin_bottom = Emu(convert.px_to_emu(pad[2] if inset else 0))
    tf.margin_left = Emu(convert.px_to_emu(pad[3] if inset else 0))

    para = tf.paragraphs[0]
    para.alignment = convert.map_align(rec.get("align"))
    line_h = _line_height_px(rec)
    if line_h:
        para.line_spacing = Pt(convert.px_to_pt(line_h))
    if rec.get("ordered"):
        _set_number_indent(para, rec.get("pad_left", 0.0))
    elif rec.get("bullet"):
        _set_green_bullet(para, rec.get("pad_left", 0.0))

    if rec.get("tag") == "pre":
        # code block: one paragraph per line, monospace, indentation kept
        size = Pt(convert.px_to_pt(rec["size_px"]))
        runs = list(rec["runs"])
        code_color = (convert.parse_color(runs[0].get("color")) if runs
                      else None) or convert.parse_color(rec.get("color"))
        full = "".join(r["text"] for r in runs).rstrip("\n")
        for li, line in enumerate(full.split("\n")):
            p = para if li == 0 else tf.add_paragraph()
            if line_h:
                p.line_spacing = Pt(convert.px_to_pt(line_h))
            rr = p.add_run()
            rr.text = line
            rr._r.find(qn("a:t")).set(
                "{http://www.w3.org/XML/1998/namespace}space", "preserve")
            rr.font.size = size
            rr.font.name = _MONO_FONT
            if code_color:
                rr.font.color.rgb = RGBColor.from_string(code_color)
        return

    _add_runs(para, rec, slide, pending_run_links)


def _add_runs(para, rec, slide, pending_run_links):
    """The record's runs into *para*: styling, per-run size, hyperlinks."""
    font_name = _first_font(rec.get("font"))
    size = Pt(convert.px_to_pt(rec["size_px"]))
    transform = (rec.get("text_transform") or "none").lower()
    base_color = convert.parse_color(rec.get("color"))
    if rec.get("ordered") and rec.get("number"):  # list number as its own run
        mr = para.add_run()
        mr.text = f'{rec["number"]}. '
        mr.font.size = size
        mr.font.name = font_name
        if base_color:
            mr.font.color.rgb = RGBColor.from_string(base_color)

    last_char = None
    for i, run in enumerate(rec["runs"]):
        text = _HORIZONTAL_WS.sub(" ", run["text"])
        text = _AROUND_NEWLINE.sub("\n", text)
        if i == 0 or last_char in (" ", "\n"):
            text = text.lstrip(" ")
        if transform == "lowercase":
            text = text.lower()
        elif transform == "capitalize":
            text = text.title()
        # A literal newline inside <a:t> renders as a paragraph break (with a
        # duplicate bullet) — line breaks must be real <a:br/> elements.
        for j, seg in enumerate(text.split("\n")):
            if j:
                para._p.append(para._p.makeelement(qn("a:br"), {}))
            if not seg:
                continue
            r = para.add_run()
            r.text = seg
            if transform == "uppercase":  # display caps, keep text editable
                r._r.get_or_add_rPr().set("cap", "all")
            f = r.font
            # Inline elements can carry their own font-size (chips like the
            # forensics pill, footnote markers) — honour it over the block size.
            f.size = (Pt(convert.px_to_pt(run["size"]))
                      if run.get("size") else size)
            f.name = _MONO_FONT if run.get("code") else font_name
            f.bold = bool(run.get("bold"))
            f.italic = bool(run.get("italic"))
            color = convert.parse_color(run.get("color")) or base_color
            if color:
                f.color.rgb = RGBColor.from_string(color)
            # Real text hyperlink; explicit colour + underline-off keep the
            # deck's styling (modern PowerPoint honours both on link runs).
            href = run.get("href")
            if href:
                f.underline = False
                if href.startswith("#"):
                    pending_run_links.append((slide, r, href[1:]))
                else:
                    r.hyperlink.address = href
        if text:
            last_char = text[-1]


def _add_figure(slide, rec, svg_counter, slide_w, slide_h):
    x, y, w, h = rec["bbox"]
    # Scale (preserving aspect, top-left anchored) so a figure that overflows
    # the canvas stays fully on-slide. Some renderers drop off-slide pictures,
    # and fitting is more faithful than the original's bottom-clip.
    scale = min(1.0, (slide_w - x) / w if w else 1.0,
                (slide_h - y) / h if h else 1.0)
    if scale < 1.0:
        w, h = w * scale, h * scale
    pic = slide.shapes.add_picture(rec["png"], _emu(x), _emu(y), _emu(w), _emu(h))
    try:
        _attach_svg(slide, pic, rec["svg"], svg_counter)
    except Exception as exc:  # fall back to PNG-only picture, keep going
        print(f"  [warn] figure {rec.get('fig_id')}: SVG embed failed "
              f"({exc}); using PNG fallback only")


def _attach_svg(slide, pic, svg_markup: str, svg_counter):
    svg_counter[0] += 1
    partname = PackURI(f"/ppt/media/image_svg{svg_counter[0]}.svg")
    pkg = slide.part.package
    svg_part = Part(partname, "image/svg+xml", pkg, svg_markup.encode("utf-8"))
    rId = slide.part.relate_to(svg_part, RT.IMAGE)

    blip = pic._element.blipFill.find(f"{{{_NS_A}}}blip")
    extLst = etree.SubElement(blip, f"{{{_NS_A}}}extLst")
    ext = etree.SubElement(extLst, f"{{{_NS_A}}}ext")
    ext.set("uri", _SVG_EXT_URI)
    svgblip = etree.SubElement(ext, f"{{{_NS_ASVG}}}svgBlip")
    svgblip.set(f"{{{_NS_R}}}embed", rId)
