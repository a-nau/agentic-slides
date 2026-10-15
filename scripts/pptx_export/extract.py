"""Render-geometry extraction.

Loads a Quarto/reveal.js deck via reveal's ``?print-pdf`` view, which lays
every slide out unscaled in its own 1280x720 ``.pdf-page`` (or a plain page of
``svg[data-marpit-svg]``-wrapped slides, Marp's bare layout, which the unit-test
fixtures use) in headless Chrome, normalizes each slide to its
natural 1280x720 size, and reads back every text block's rendered
bounding box + computed style and every author SVG figure (outer markup + a
high-DPI PNG screenshot). Produces the slide-model dict consumed by ``build``.
"""

import os

from playwright.sync_api import sync_playwright

from . import svg_arrows

# Walks the DOM and returns the slide model (geometry in CSS px). Runs in-page.
_EXTRACT_JS = r"""
() => {
  const PXW = 1280, PXH = 720;
  // Marp: one svg[data-marpit-svg] per slide; reveal.js print view: .pdf-page.
  const marpWraps = [...document.querySelectorAll('svg[data-marpit-svg]')];
  const wrappers = marpWraps.length ? marpWraps
    : [...document.querySelectorAll('.reveal .pdf-page')]
        .filter(p => p.querySelector('section.slide'));
  wrappers.forEach(s => {
    s.style.width = PXW + 'px';
    s.style.height = PXH + 'px';
    s.style.display = 'block';
  });

  const BLOCK_SEL = 'h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,td,th,figcaption';
  const STOP = new Set(['H1','H2','H3','H4','H5','H6','P','LI','BLOCKQUOTE',
                        'PRE','UL','OL','TABLE','THEAD','TBODY','TR','DIV']);
  const inAuthorSvg = el => el.closest('svg:not([data-marpit-svg])') !== null;
  // A "chip": inline-block element with its own background + text (e.g. tags).
  // Handled as a self-contained shape, not split into a box + parent-flow text.
  // A chip's fill: solid background-color, or the first stop of a gradient
  // (e.g. .badge uses a linear-gradient, so backgroundColor is transparent).
  const chipFill = el => {
    const cs = getComputedStyle(el);
    const bc = cs.backgroundColor || '';
    if (!/rgba\(0, 0, 0, 0\)|transparent|^$/.test(bc)) return bc;
    const bi = cs.backgroundImage || '';
    if (bi.indexOf('gradient') >= 0) {
      const m = bi.match(/rgba?\([^)]*\)/);
      if (m) return m[0];
    }
    return null;
  };
  const isChip = el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'inline' || cs.display === 'none') return false;
    if (!chipFill(el)) return false;
    if (!el.textContent.trim()) return false;
    const r = el.getBoundingClientRect();
    if (r.height > 44 || r.width > 460) return false;   // small pill/badge only
    for (const c of el.children) {                      // not a card/container
      if (chipFill(c)) return false;
    }
    return true;
  };
  // A chip is rendered as its own shape only when it's the sole content of its
  // parent. Chips sitting inside running text stay inline (a shape there would
  // make the surrounding text reflow under it).
  const isStandaloneChip = el => {
    const p = el.parentElement;
    return p && [...p.childNodes].every(n =>
      (n.nodeType === 3 && !n.textContent.trim()) ||
      (n.nodeType === 1 && (n.tagName === 'BR' || isChip(n))));
  };
  const applyTransform = (t, tt) =>
    tt === 'uppercase' ? t.toUpperCase() :
    tt === 'lowercase' ? t.toLowerCase() :
    tt === 'capitalize' ? t.replace(/\b\w/g, c => c.toUpperCase()) : t;

  function buildRuns(el) {
    const out = [];
    function walk(node, ctx) {
      node.childNodes.forEach(ch => {
        if (ch.nodeType === 3) {
          if (ch.textContent) out.push({
            text: applyTransform(ch.textContent, ctx.transform),
            bold: ctx.bold, italic: ctx.italic,
            code: ctx.code, href: ctx.href, color: ctx.color,
            size: ctx.size });
        } else if (ch.nodeType === 1) {
          if (ch.tagName === 'BR') {
            out.push({
              text: '\n', bold: ctx.bold, italic: ctx.italic,
              code: ctx.code, href: ctx.href, color: ctx.color,
              size: ctx.size,
            });
            return;
          }
          if (STOP.has(ch.tagName)) return;  // nested block -> its own record
          if (ch.tagName === 'MJX-ASSISTIVE-MML') return;  // MathJax's hidden a11y copy
          if (isStandaloneChip(ch)) return;  // standalone chip -> its own shape
          if (ch.hasAttribute('data-pptx-hover-affordance')) return;  // notes only
          const cs = getComputedStyle(ch);
          const next = {
            bold: ctx.bold || parseInt(cs.fontWeight, 10) >= 600
                  || ch.tagName === 'STRONG' || ch.tagName === 'B',
            italic: ctx.italic || cs.fontStyle === 'italic'
                    || ch.tagName === 'EM' || ch.tagName === 'I',
            code: ctx.code || ch.tagName === 'CODE',
            href: ch.tagName === 'A' ? ch.getAttribute('href') : ctx.href,
            color: cs.color || ctx.color,
            size: parseFloat(cs.fontSize) || ctx.size,
            transform: cs.textTransform !== 'none' ? cs.textTransform : ctx.transform,
          };
          walk(ch, next);
        }
      });
    }
    // Seed from the block's own computed style so CSS-applied weight/style
    // (e.g. h1 { font-weight: 800 }) is honoured, not just <strong>/<em>.
    const bcs = getComputedStyle(el);
    walk(el, {
      bold: parseInt(bcs.fontWeight, 10) >= 600,
      italic: bcs.fontStyle === 'italic',
      code: false,
      href: el.tagName === 'A' ? el.getAttribute('href') : null,
      color: bcs.color,
      size: parseFloat(bcs.fontSize), transform: 'none',
    });
    return out;
  }

  const slides = [];
  const anchors = {};
  wrappers.forEach((wrap, si) => {
    const section = wrap.querySelector('section');
    if (!section) return;
    section.setAttribute('data-pptx-slide-index', String(si));
    section.querySelectorAll('[id]').forEach(e => {
      if (e.id) anchors[e.id] = si;  // slug -> slide index, for slide-jumps
    });
    const orig = wrap.getBoundingClientRect();
    const rel = r => [r.left - orig.left, r.top - orig.top, r.width, r.height];
    const elements = [];

    // Hover tooltips are an HTML-only affordance. Their texts become speaker
    // notes; non-inline carriers (forensics pills, overlay regions) are marked
    // so they are skipped as slide content and hidden in backdrop screenshots.
    const notes = [];
    [...section.querySelectorAll('[data-tip]')].forEach(el => {
      const tip = el.getAttribute('data-tip');
      if (tip) notes.push({
        head: el.getAttribute('data-tiphead') || 'Note', tip });
      if (!inAuthorSvg(el) && getComputedStyle(el).display !== 'inline')
        el.setAttribute('data-pptx-hover-affordance', '');
    });

    // Figures: top-level author SVGs (skip ones nested inside another figure).
    const authorSvgs = [...section.querySelectorAll('svg')].filter(s => {
      const par = s.parentElement &&
        s.parentElement.closest('svg:not([data-marpit-svg])');
      return !par;
    });
    authorSvgs.forEach((svg, fi) => {
      const figId = si + '-' + fi;
      svg.setAttribute('data-fig-id', figId);
      // XMLSerializer (not .outerHTML): emits well-formed XML — declares
      // namespaces and writes literal chars instead of HTML named entities
      // like &nbsp;, which would break SVG importers (PowerPoint/Inkscape).
      elements.push({
        kind: 'figure', bbox: rel(svg.getBoundingClientRect()),
        svg: new XMLSerializer().serializeToString(svg), fig_id: figId });
    });

    // Text blocks plus standalone HTML labels/links that are not owned by a
    // normal block. Nested DIVs remain separate because buildRuns stops at
    // nested blocks; inline candidates defer to an eligible ancestor.
    const hasDirectText = el => [...el.childNodes].some(n =>
      (n.nodeType === 3 && n.textContent.trim()) ||
      (n.nodeType === 1 && n.tagName === 'BR'));
    const standaloneCandidates = [...section.querySelectorAll('div,span,a')]
      .filter(el => hasDirectText(el) && !el.closest(BLOCK_SEL) &&
                    !inAuthorSvg(el) && !isStandaloneChip(el) &&
                    !el.hasAttribute('data-pptx-hover-affordance'));
    const standaloneSet = new Set(standaloneCandidates);
    const standaloneText = standaloneCandidates.filter(el => {
      if (el.tagName === 'DIV') return true;
      for (let p = el.parentElement; p && p !== section; p = p.parentElement) {
        if (standaloneSet.has(p)) return false;
      }
      return true;
    });
    const textElements = [...section.querySelectorAll(BLOCK_SEL), ...standaloneText];
    const listIds = new Map();  // <ul>/<ol> element -> stable per-slide id
    textElements.forEach(el => {
      if (inAuthorSvg(el)) return;
      const runs = buildRuns(el);
      if (!runs.some(r => r.text.trim())) return;
      el.setAttribute('data-pptx-native-text', '');
      const cs = getComputedStyle(el);
      const ol = el.tagName === 'LI' ? el.closest('ol') : null;
      let number = null;
      if (ol) {
        const items = [...ol.querySelectorAll(':scope > li')];
        number = (parseInt(ol.getAttribute('start'), 10) || 1) + items.indexOf(el);
      }
      // Items of the same list share a list_id so the builder can merge them
      // into one text frame (one paragraph per item). Items with nested block
      // content keep their own frame — their bbox spans the nested blocks,
      // which would scramble a merged frame's vertical layout.
      let listId = null, marginBottom = 0;
      if (el.tagName === 'LI') {
        if (!el.querySelector('ul,ol,p,pre,blockquote,table,div')) {
          const list = el.parentElement;
          if (!listIds.has(list)) listIds.set(list, si + '-' + listIds.size);
          listId = listIds.get(list);
        }
        marginBottom = parseFloat(cs.marginBottom) || 0;
      }
      elements.push({
        kind: 'text', tag: el.tagName.toLowerCase(),
        bbox: rel(el.getBoundingClientRect()), runs,
        font: cs.fontFamily, size_px: parseFloat(cs.fontSize),
        color: cs.color, align: cs.textAlign,
        weight: cs.fontWeight, line_height: cs.lineHeight,
        bullet: el.tagName === 'LI' && !ol,  // green dot for <ul> only
        ordered: !!ol, number,
        list_id: listId, margin_bottom: marginBottom,
        pad_left: parseFloat(cs.paddingLeft) || 0,
        pad: [parseFloat(cs.paddingTop) || 0, parseFloat(cs.paddingRight) || 0,
              parseFloat(cs.paddingBottom) || 0, parseFloat(cs.paddingLeft) || 0],
        text_transform: cs.textTransform,
      });
    });

    // Slide chrome as native objects: top accent line, logo (picture), page
    // number (text), invert divider bar (rect). Pseudo-element geometry comes
    // back fully resolved from getComputedStyle; offset by the section border
    // and any transform translate to land in slide coordinates.
    const secCs = getComputedStyle(section);
    const bL = parseFloat(secCs.borderLeftWidth) || 0;
    const bT = parseFloat(secCs.borderTopWidth) || 0;
    if (bT > 0) elements.push(
      { kind: 'deco_rect', bbox: [0, 0, PXW, bT], fill: secCs.borderTopColor, radius: 0 });
    ['::before', '::after'].forEach(pe => {
      const cs = getComputedStyle(section, pe);
      if (cs.content === 'none') return;
      const w = parseFloat(cs.width) || 0, h = parseFloat(cs.height) || 0;
      let x = (parseFloat(cs.left) || 0) + bL, y = (parseFloat(cs.top) || 0) + bT;
      if (cs.transform && cs.transform !== 'none') {
        const m = cs.transform.match(/matrix\(([^)]+)\)/);
        if (m) { const p = m[1].split(',').map(parseFloat); x += p[4] || 0; y += p[5] || 0; }
      }
      const bgImg = cs.backgroundImage || '';
      const txt = cs.content && cs.content !== 'none'
        ? cs.content.replace(/^"|"$/g, '') : '';
      if (bgImg.startsWith('url(')) {
        const m = bgImg.match(/url\("?(data:[^"')]+)"?\)/);
        if (m && w > 1 && h > 1)
          elements.push({ kind: 'deco_image', bbox: [x, y, w, h], data_uri: m[1] });
      } else if (txt) {
        elements.push({ kind: 'deco_text',
          bbox: [x, y, Math.max(w, 40), Math.max(h, 18)],
          text: txt, color: cs.color, size_px: parseFloat(cs.fontSize) });
      } else {
        const bc = cs.backgroundColor;
        if (bc && !/rgba\(0, 0, 0, 0\)|transparent/.test(bc) && w > 1 && h > 1)
          elements.push({ kind: 'deco_rect', bbox: [x, y, w, h],
            fill: bc, radius: parseFloat(cs.borderTopLeftRadius) || 0 });
      }
    });

    // Styled containers (callouts, cards, code blocks) -> box records behind
    // the text. Their backgrounds aren't in the chrome layer (content is hidden
    // there) and aren't DOM text, so they need their own shapes.
    [...section.querySelectorAll('*')].forEach(el => {
      if (inAuthorSvg(el)) return;
      if (el.hasAttribute('data-pptx-hover-affordance')) return;
      const cs = getComputedStyle(el);
      if (isChip(el)) {
        if (isStandaloneChip(el)) {
          el.setAttribute('data-pptx-native-chip', '');
          const r = el.getBoundingClientRect();
          elements.push({ kind: 'chip', bbox: rel(r), fill: chipFill(el),
            radius: parseFloat(cs.borderTopLeftRadius) || 0,
            text: el.textContent.trim(), color: cs.color,
            size_px: parseFloat(cs.fontSize),
            bold: parseInt(cs.fontWeight, 10) >= 600,
            text_transform: cs.textTransform });
        }
        return;  // inline chips stay in the text flow (no box/shape)
      }
      if (cs.display === 'inline') return;
      if (el.tagName === 'CODE' &&
          (!el.parentElement || el.parentElement.tagName !== 'PRE')) return;
      const bw = parseFloat(cs.borderTopWidth) || 0;
      const lw = parseFloat(cs.borderLeftWidth) || 0;
      const maxB = Math.max(bw, lw, parseFloat(cs.borderRightWidth) || 0,
                            parseFloat(cs.borderBottomWidth) || 0);
      const bg = cs.backgroundColor;
      const hasBg = bg && bg !== 'transparent' &&
                    !/^rgba\(0,\s*0,\s*0,\s*0\)/.test(bg);
      if (!hasBg && maxB === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const box = { kind: 'box', bbox: rel(r), fill: hasBg ? bg : null,
        stroke: bw > 0 ? cs.borderTopColor : null, stroke_w: bw,
        radius: parseFloat(cs.borderTopLeftRadius) || 0 };
      if (lw > bw) { box.accent = cs.borderLeftColor; box.accent_w = lw; }
      elements.push(box);
    });

    // Anchors whose text lives in an extracted text block become real run
    // hyperlinks (explicit colour + no underline survive in PowerPoint).
    // Anchors with no text of their own (image links, figure crops) still
    // need a transparent click-overlay shape.
    const nativeTextSet = new Set(
      [...section.querySelectorAll('[data-pptx-native-text]')]);
    [...section.querySelectorAll('a[href]')].forEach(a => {
      if (inAuthorSvg(a)) return;
      const href = a.getAttribute('href');
      if (!href) return;
      const r = a.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return;
      const inNativeText =
        nativeTextSet.has(a) || !!a.closest('[data-pptx-native-text]');
      if (a.textContent.trim() && inNativeText) return;  // run hyperlink
      elements.push({ kind: 'link', bbox: rel(r), href });
    });

    // Remote <video>/<iframe> embeds: their fetches are blocked (nothing to
    // screenshot, and a .pptx can't play them anyway) — emit a linked
    // placeholder tile over the reserved layout box instead.
    [...section.querySelectorAll('video,iframe')].forEach(el => {
      const src = el.currentSrc || el.getAttribute('src') || '';
      if (!/^https?:/.test(src)) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      el.setAttribute('data-pptx-media', '');
      let label = src;
      try { label = new URL(src).hostname; } catch (e) {}
      elements.push({ kind: 'media', bbox: rel(r), href: src, label });
    });

    // The section itself counts too: lead/quote slides paint their pattern on
    // the section's own background-image (shorthand leaves bgColor transparent).
    const secBgImage = getComputedStyle(section).backgroundImage;
    const hasBrowserVisual =
      !!section.querySelector('img,iframe:not([data-pptx-media])') ||
      (secBgImage && secBgImage !== 'none') ||
      [...section.querySelectorAll('*')].some(el => {
        if (inAuthorSvg(el) || isStandaloneChip(el)) return false;
        const bg = getComputedStyle(el).backgroundImage;
        return bg && bg !== 'none';
      });
    if (hasBrowserVisual) section.setAttribute('data-pptx-backdrop', '');

    slides.push({ index: si, bg: getComputedStyle(section).backgroundColor,
                  elements, notes });
  });
  return { slide_px: [PXW, PXH], slides, anchors };
}
"""


def _nudge_text_clear_of_bars(model: dict) -> None:
    """Shift divider text that overlaps the green section bar so it clears it.

    On ``_class: invert`` dividers the theme indents h1/p by 2.5rem to clear the
    bar but has no rule for an ``## H2`` subtitle, so the subtitle overlaps the
    bar. Align any overlapping text to the same 2.5rem-past-bar indent.
    """
    INDENT = 40  # ~2.5rem, matching the indented h1
    for slide in model["slides"]:
        bars = [e for e in slide["elements"] if e["kind"] == "deco_rect"
                and e["bbox"][3] > 40 and e["bbox"][2] < 20]  # tall, thin
        for bx, by, bw, bh in (b["bbox"] for b in bars):
            for e in slide["elements"]:
                if e["kind"] != "text":
                    continue
                x, y, w, h = e["bbox"]
                overlaps = x < bx + bw + 2 and y < by + bh and y + h > by
                if overlaps and (bx + INDENT) > x:
                    shift = bx + INDENT - x
                    e["bbox"] = [bx + INDENT, y, max(20, w - shift), h]


_FONTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts"))

_FONT_FACES = [
    ("Inter", "Inter-Regular.ttf", "normal", 400),
    ("Inter", "Inter-Bold.ttf", "normal", 700),
    ("Inter", "Inter-Italic.ttf", "italic", 400),
    ("Inter", "Inter-BoldItalic.ttf", "italic", 700),
    ("JetBrains Mono", "JetBrainsMono-Regular.ttf", "normal", 400),
    ("JetBrains Mono", "JetBrainsMono-Bold.ttf", "normal", 700),
]


def _font_face_css() -> str:
    """@font-face rules for the vendored deck fonts (extraction-side only).

    Remote fonts are blocked during extraction, so without these the page lays
    out in a fallback sans and every measured box/wrap deviates from the real
    deck. Missing files are skipped (layout falls back with a warning upstream).
    """
    rules = []
    for family, fname, style, weight in _FONT_FACES:
        path = os.path.join(_FONTS_DIR, fname)
        if os.path.isfile(path):
            rules.append(
                f"@font-face {{ font-family: '{family}'; src: url('file://{path}');"
                f" font-style: {style}; font-weight: {weight}; }}")
    return "\n".join(rules)


def extract_html(html_path: str, png_dir: str | None = None,
                 device_scale_factor: int = 2) -> dict:
    """Extract the slide model from a rendered Quarto/reveal.js deck (or a
    Marp-bare-layout page, as in the test fixtures).

    If ``png_dir`` is given, each figure is screenshotted there and its record
    gets a ``png`` key with the file path.
    """
    url = "file://" + os.path.abspath(html_path)
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        reveal = "Reveal.initialize" in fh.read()
    if reveal:
        url += "?print-pdf"  # every slide laid out unscaled, one .pdf-page each
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True,
            args=["--allow-file-access-from-files"])  # file:// @font-face
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=device_scale_factor,
        )
        page = context.new_page()
        blocked_remote = []

        def route_request(route):
            request_url = route.request.url
            if request_url.startswith(("http://", "https://")):
                blocked_remote.append((request_url, route.request.resource_type))
                route.abort(error_code="blockedbyclient")
            else:
                route.continue_()

        page.route("**/*", route_request)
        page.goto(url, wait_until="networkidle")
        if reveal:  # print layout + MathJax are asynchronous
            page.wait_for_function(
                "() => document.querySelectorAll('.reveal .pdf-page').length > 0")
            page.evaluate("() => window.MathJax && MathJax.startup"
                          " ? MathJax.startup.promise : null")
        # Stylesheets/fonts have local fallbacks; remote video/audio ("media")
        # and remote iframes ("document" — the page itself is file://, so any
        # remote document is an embed) become linked placeholder tiles instead
        # of aborting the export.
        fatal_remote = {url for url, kind in blocked_remote
                        if kind not in ("stylesheet", "font", "media", "document")}
        if fatal_remote:
            remote = ", ".join(sorted(fatal_remote))
            browser.close()
            raise RuntimeError(f"Remote resources are not supported: {remote}")
        for remote, kind in sorted(set(blocked_remote)):
            print(f"  [warn] blocked remote {kind}: {remote}; using local fallback")

        font_css = _font_face_css()
        if font_css:
            page.add_style_tag(content=font_css)
            page.evaluate("() => document.fonts.ready")
            if not page.evaluate("() => document.fonts.check('16px Inter')"):
                print("  [warn] local Inter did not load; geometry uses fallback font")

        model = page.evaluate(_EXTRACT_JS)
        _nudge_text_clear_of_bars(model)

        # Bake <marker> arrowheads into geometry (PowerPoint ignores markers).
        for slide in model["slides"]:
            for el in slide["elements"]:
                if el["kind"] == "figure":
                    el["svg"] = svg_arrows.bake_markers(el["svg"])

        if png_dir:
            os.makedirs(png_dir, exist_ok=True)
            for handle in page.query_selector_all("[data-fig-id]"):
                fig_id = handle.get_attribute("data-fig-id")
                path = os.path.join(png_dir, f"fig-{fig_id}.png")
                handle.screenshot(path=path, omit_background=True)
                for slide in model["slides"]:
                    for el in slide["elements"]:
                        if el.get("fig_id") == fig_id:
                            el["png"] = path
            style = page.add_style_tag(content="""
                section[data-pptx-backdrop] [data-pptx-native-text],
                section[data-pptx-backdrop] [data-pptx-native-text] * {
                    color: transparent !important;
                    -webkit-text-fill-color: transparent !important;
                    text-shadow: none !important;
                }
                section[data-pptx-backdrop] svg:not([data-marpit-svg]),
                section[data-pptx-backdrop] [data-pptx-native-chip] {
                    visibility: hidden !important;
                }
                /* the build adds native bullets — the theme's CSS bullet
                   (li::before dot / ::marker) must not also be in the shot */
                section[data-pptx-backdrop] [data-pptx-native-text]::before,
                section[data-pptx-backdrop] [data-pptx-native-text]::after {
                    content: none !important;
                }
                section[data-pptx-backdrop] [data-pptx-native-text]::marker {
                    color: transparent !important;
                }
                /* hover affordances are HTML-only: no dashed term underlines
                   in the shot, no forensics pills / overlay regions at all */
                section[data-pptx-backdrop] [data-tip] {
                    border-color: transparent !important;
                }
                section[data-pptx-backdrop] [data-pptx-hover-affordance] {
                    visibility: hidden !important;
                }
            """)
            slides_by_index = {str(s["index"]): s for s in model["slides"]}
            for handle in page.query_selector_all("section[data-pptx-backdrop]"):
                slide_index = handle.get_attribute("data-pptx-slide-index")
                path = os.path.join(png_dir, f"backdrop-{slide_index}.png")
                handle.screenshot(path=path)
                slides_by_index[slide_index]["backdrop"] = path
            style.evaluate("node => node.remove()")
        browser.close()
    return model
