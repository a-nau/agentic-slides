#!/usr/bin/env python3
"""Detect overflow and overlap in deck figures and slides.

Two scopes, because content goes missing at two levels:
  * figures — a <text> spills past its box, or runs off the 1160x600 canvas,
              or two boxes overlap.
  * slides  — content runs past the 1280x720 slide and is clipped (invisible)
              in the export.

Quarto/reveal.js variant: slides are rendered with the slides repo's Quarto
project (`quarto/bin/quarto render`), then screenshotted slide by slide in
headless Chromium through the reveal.js API.

Layered by design (see the slide-deck skill):
  * default  — figures are checked DETERMINISTICALLY with `inkscape --query-all`
               (no browser, exact geometry). Slides are rendered to one PNG each
               via quarto + Chromium so they can be inspected by eye/vision.
  * --strict — additionally measures slides AND figures in headless Chromium
               (getBoundingClientRect / getBBox) for an exact pass/fail gate.
               Requires Python `playwright`; skipped with a hint if absent.

Usage:
  check_layout.py figs   <a.svg> [b.svg ...]        # deterministic figure check
  check_layout.py figs   --dir <deck>               # all <deck>/images/*.svg
  check_layout.py slides <deck-dir> [--strict]      # render PNGs (+ strict measure)
  check_layout.py all    <deck-dir> [--strict]      # figs + slides

Exit code is non-zero if any deterministic check fails.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CANVAS_W, CANVAS_H = 1160, 600          # the figure SVG canvas (see svg-figures.md)
SLIDE_W, SLIDE_H = 1280, 720            # _quarto.yml width/height
EDGE_TOL = 2.0                          # px slack at canvas/slide edge
BOX_PAD = 4.0                           # px a label should sit inside its box
OVERLAP_TOL = 4.0                       # px overlap on BOTH axes before it's "real"


# ─────────────────────────── figures (deterministic) ───────────────────────────
import tempfile
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
GEOM_TAGS = {"rect", "text", "path", "image", "circle", "ellipse"}


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_structure(svg: Path):
    """Assign an id to every geometry element (if missing) and record
    id -> (tag, parent_id). Returns (tmp_svg_path, info dict). inkscape is
    snap-confined and resolves relative paths against $HOME, so the temp file
    is written with an absolute path and queried that way."""
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(svg)
    root = tree.getroot()
    info: dict[str, dict] = {}
    n = 0
    # parent map (ElementTree has no getparent)
    parent_of = {c: p for p in root.iter() for c in p}
    for el in root.iter():
        if _localname(el.tag) not in GEOM_TAGS:
            continue
        if "id" not in el.attrib:
            el.set("id", f"chk{n}"); n += 1
        parent = parent_of.get(el)
        pid = parent.get("id") if parent is not None else None
        ptag = _localname(parent.tag) if parent is not None else None
        if parent is not None and "id" not in parent.attrib:
            parent.set("id", f"chkp{n}"); n += 1
            pid = parent.get("id")
        info[el.get("id")] = {"tag": _localname(el.tag),
                              "parent": pid, "ptag": ptag}
    # write beside the source: snap-confined inkscape can't read /tmp, only $HOME
    fd, name = tempfile.mkstemp(suffix=".svg", prefix=".chklayout_", dir=svg.parent)
    os.close(fd)
    tmp = Path(name).resolve()
    tree.write(tmp, xml_declaration=True, encoding="utf-8")
    return tmp, info


def query_geometry(svg_abs: Path) -> dict[str, tuple[float, float, float, float]]:
    """id -> (x, y, w, h) from `inkscape --query-all` (absolute path required)."""
    out = subprocess.run(
        ["inkscape", "--query-all", str(svg_abs)],
        capture_output=True, text=True,
    ).stdout
    geo: dict[str, tuple[float, float, float, float]] = {}
    for line in out.splitlines():
        parts = line.split(",")
        if len(parts) != 5:
            continue
        try:
            x, y, w, h = (float(p) for p in parts[1:])
        except ValueError:
            continue
        geo[parts[0]] = (x, y, w, h)
    return geo


def is_background(b) -> bool:
    _, x, y, w, h = b
    return abs(x) < 2 and abs(y) < 2 and w >= CANVAS_W - 2 and h >= CANVAS_H - 2


def contains(outer, inner, pad=0.0) -> bool:
    _, ox, oy, ow, oh = outer
    _, ix, iy, iw, ih = inner
    return (ix >= ox + pad and iy >= oy + pad
            and ix + iw <= ox + ow - pad and iy + ih <= oy + oh - pad)


def overlap_xy(a, b) -> tuple[float, float]:
    _, ax, ay, aw, ah = a
    _, bx, by, bw, bh = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    return ox, oy


def _holds_anchor(r, tx, ty) -> bool:
    _, rx, ry, rw, rh = r
    return rx <= tx <= rx + rw and ry <= ty <= ry + rh


def check_figure(svg: Path) -> list[str]:
    tmp, info = parse_structure(svg)
    try:
        geo = query_geometry(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    if not geo:
        return [f"inkscape returned no geometry for {svg.name} "
                f"(failed to open or empty file)"]

    # records: (id, x, y, w, h); plus tag/parent lookup from `info`
    recs = {eid: (eid, *geo[eid]) for eid in info if eid in geo}
    tag = {eid: info[eid]["tag"] for eid in recs}
    parent = {eid: info[eid]["parent"] for eid in recs}
    ptag = {eid: info[eid]["ptag"] for eid in recs}
    rects = [r for eid, r in recs.items()
             if tag[eid] == "rect" and not is_background(r)]
    texts = [r for eid, r in recs.items() if tag[eid] == "text"]
    problems: list[str] = []

    # 1) anything clipped by the canvas edge (figure-level "not visible")
    for eid, b in recs.items():
        if tag[eid] not in ("text", "rect", "path", "image"):
            continue
        _, x, y, w, h = b
        if (x < -EDGE_TOL or y < -EDGE_TOL
                or x + w > CANVAS_W + EDGE_TOL or y + h > CANVAS_H + EDGE_TOL):
            problems.append(
                f"off-canvas: {eid} at ({x:.0f},{y:.0f},{w:.0f}x{h:.0f}) "
                f"exceeds {CANVAS_W}x{CANVAS_H}")

    # 2) text spilling past its box. Prefer the rect that shares the text's
    #    parent (the <a><rect/><text/></a> clickable-box pattern); else the
    #    smallest rect whose box contains the text's anchor (top-left) corner.
    by_id = {r[0]: r for r in rects}
    for t in texts:
        tid, tx, ty, tw, th = t
        box = None
        # sibling rect under a shared <a>/<g> group = the clickable-box pattern
        grouped = ptag.get(tid) in ("a", "g")
        siblings = [by_id[e] for e in by_id
                    if grouped and parent.get(e) == parent.get(tid)]
        if siblings:
            box = min(siblings, key=lambda r: r[3] * r[4])
        else:
            holders = [r for r in rects if _holds_anchor(r, tx, ty)]
            if holders:
                box = min(holders, key=lambda r: r[3] * r[4])
        if box is None:
            continue  # free label / caption — no box constraint
        if not contains(box, t, pad=BOX_PAD):
            problems.append(
                f"text overflow: {tid} (x={tx:.0f},w={tw:.0f}) spills past box "
                f"{box[0]} (x={box[1]:.0f},w={box[3]:.0f}) — shorten the label "
                f"or widen the box")

    # 3) partial overlap between boxes (full nesting is intentional; partial isn't)
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            ox, oy = overlap_xy(a, b)
            if ox > OVERLAP_TOL and oy > OVERLAP_TOL \
                    and not contains(a, b) and not contains(b, a):
                problems.append(
                    f"box overlap: {a[0]} and {b[0]} overlap by "
                    f"{ox:.0f}x{oy:.0f}px")
    return problems


def run_figs(svgs: list[Path]) -> int:
    if not svgs:
        print("no SVGs to check", file=sys.stderr)
        return 0
    failed = False
    for svg in svgs:
        probs = check_figure(svg)
        if probs:
            failed = True
            print(f"✗ {svg.name}")
            for p in probs:
                print(f"    {p}")
        else:
            print(f"✓ {svg.name}")
    print("\nNote: text-overflow uses inkscape's font metrics; if Inter is not "
          "installed there, widths are approximate. Use --strict for the exact "
          "(Chromium) measurement.", file=sys.stderr)
    return 1 if failed else 0


# ─────────────────────────── slides (render for vision) ─────────────────────────
def quarto_root(deck_dir: Path) -> Path:
    for p in [deck_dir, *deck_dir.parents]:
        if (p / "_quarto.yml").exists() and (p / "quarto" / "bin" / "quarto").exists():
            return p
    raise SystemExit(f"error: {deck_dir} is not inside the slides repo")


def render_html(deck_dir: Path) -> Path | None:
    """`quarto render` the deck; return the HTML it builds next to slides.qmd."""
    deck_dir = deck_dir.resolve()
    qmd = deck_dir / "slides.qmd"
    if not qmd.exists():
        print(f"error: {qmd} not found (run build_deck.py first)", file=sys.stderr)
        return None
    root = quarto_root(deck_dir)
    subprocess.run([str(root / "quarto" / "bin" / "quarto"), "render", str(qmd), "--quiet"],
                   cwd=root, check=True)
    return deck_dir / "slides.html"


def _open_deck(pw, html: Path):
    try:  # system Chrome, like the repo's exporters; bundled Chromium if absent
        browser = pw.chromium.launch(channel="chrome")
    except Exception:  # noqa: BLE001 — playwright raises a plain Error
        browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
    page.goto(html.as_uri())
    page.wait_for_function("window.Reveal && Reveal.isReady()")
    page.wait_for_timeout(800)  # webfonts + MathJax
    return browser, page


def render_slide_pngs(deck_dir: Path) -> list[Path]:
    """Render one PNG per slide: quarto render + Chromium via the reveal.js API."""
    html = render_html(deck_dir)
    if html is None:
        return []
    from playwright.sync_api import sync_playwright
    out_dir = deck_dir.resolve() / "export"
    out_dir.mkdir(exist_ok=True)
    pngs = []
    with sync_playwright() as pw:
        browser, page = _open_deck(pw, html)
        for i in range(page.evaluate("Reveal.getTotalSlides()")):
            page.evaluate(f"Reveal.slide({i}); Reveal.getCurrentSlide().querySelectorAll('.fragment').forEach(f => f.classList.add('visible'))")
            page.wait_for_timeout(150)
            png = out_dir / f"{deck_dir.resolve().name}.{i + 1:03d}.png"
            page.screenshot(path=str(png))
            pngs.append(png)
        browser.close()
    print(f"Built HTML: {html}")
    return pngs


def run_slides(deck_dir: Path) -> int:
    pngs = render_slide_pngs(deck_dir)
    if not pngs:
        return 1
    print(f"Rendered {len(pngs)} slide PNG(s) to {deck_dir / 'export'} (all fragments shown):")
    for p in pngs:
        print(f"    {p}")
    print("\nInspect each: content clipped at the bottom/right edge means it "
          "overflows the slide and is INVISIBLE in the export. Trim bullets, "
          "split the slide, or shrink the figure.")
    return 0


# ─────────────────────────── strict (Chromium) ──────────────────────────────────
def run_strict(deck_dir: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("--strict needs Python playwright. Skipping strict measurement.", file=sys.stderr)
        return 0
    html = render_html(deck_dir)
    if html is None:
        return 1
    js = """(n) => {
      const sec = Reveal.getCurrentSlide();
      sec.querySelectorAll('.fragment').forEach(f => f.classList.add('visible'));
      const sb = sec.getBoundingClientRect();
      for (const el of sec.querySelectorAll('*')) {
        if (el.closest('aside.notes')) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.bottom > sb.bottom + 1 || r.right > sb.right + 1
            || r.top < sb.top - 1 || r.left < sb.left - 1)
          return `slide ${n}: <${el.tagName.toLowerCase()}> "${(el.textContent||'').trim().slice(0,40)}" overflows the slide`;
      }
      return null;
    }"""
    bad = []
    with sync_playwright() as pw:
        browser, page = _open_deck(pw, html)
        for i in range(page.evaluate("Reveal.getTotalSlides()")):
            page.evaluate(f"Reveal.slide({i})")
            page.wait_for_timeout(100)
            msg = page.evaluate(js, i + 1)
            if msg:
                bad.append(msg)
        browser.close()
    if bad:
        print("✗ slide overflow (Chromium-measured):")
        for b in bad:
            print(f"    {b}")
        return 1
    print("✓ no slide overflow (Chromium-measured)")
    return 0


# ─────────────────────────── cli ────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scope", choices=["figs", "slides", "all"])
    ap.add_argument("paths", nargs="*", help="SVGs (figs) or a deck dir (slides/all)")
    ap.add_argument("--dir", help="deck dir for figs mode (checks <dir>/images/*.svg)")
    ap.add_argument("--strict", action="store_true",
                    help="also measure in headless Chromium (needs playwright)")
    args = ap.parse_args()

    rc = 0
    if args.scope in ("figs", "all"):
        if args.scope == "all":
            deck = Path(args.paths[0]); svgs = sorted((deck / "images").glob("*.svg"))
        elif args.dir:
            svgs = sorted((Path(args.dir) / "images").glob("*.svg"))
        else:
            svgs = [Path(p) for p in args.paths]
        rc |= run_figs(svgs)
    if args.scope in ("slides", "all"):
        deck = Path(args.paths[0]).resolve()
        rc |= run_slides(deck)
        if args.strict:
            rc |= run_strict(deck)
    return rc


if __name__ == "__main__":
    sys.exit(main())
