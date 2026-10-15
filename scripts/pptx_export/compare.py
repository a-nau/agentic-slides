"""Dev tool: render a deck's original (reveal.js print view) and editable-pptx
slides to PNGs and stitch them side-by-side for visual diffing.

    .venv/bin/python -m scripts.pptx_export.compare <deck> [slide ...]

Writes exports/compare/<deck>/cmp-NN.png (left = deck, right = pptx).
Needs the system Chrome (playwright), soffice, and pdftoppm on PATH.
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def render_deck_pngs(deck: str, outdir: str) -> list[str]:
    """One PNG per slide: the rendered deck's reveal.js print view."""
    from playwright.sync_api import sync_playwright

    os.makedirs(outdir, exist_ok=True)
    _run([os.path.join(REPO, "quarto", "bin", "quarto"), "render",
          f"decks/{deck}/slides.qmd", "--quiet"], cwd=REPO)
    html = os.path.join(REPO, "decks", deck, "slides.html")
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        p = b.new_page(viewport={"width": 1280, "height": 720})
        p.goto("file://" + html + "?print-pdf", wait_until="networkidle")
        p.wait_for_function("() => document.querySelectorAll('.reveal .pdf-page').length > 0")
        p.evaluate("() => window.MathJax && MathJax.startup ? MathJax.startup.promise : null")
        for i, page in enumerate(p.query_selector_all(".reveal .pdf-page"), 1):
            page.screenshot(path=os.path.join(outdir, f"orig-{i:03d}.png"))
        b.close()
    return sorted(f for f in os.listdir(outdir) if f.startswith("orig-"))


def render_pptx_pngs(pptx: str, outdir: str) -> list[str]:
    """One PNG per slide: pptx -> pdf (soffice) -> png (pdftoppm)."""
    os.makedirs(outdir, exist_ok=True)
    env = dict(os.environ, HOME=tempfile.mkdtemp(prefix="pptx-soffice-"))  # fresh LibreOffice profile
    _run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir,
          pptx], env=env)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    _run(["pdftoppm", "-png", "-r", "96", pdf, os.path.join(outdir, "pptx")])
    return sorted(f for f in os.listdir(outdir) if f.startswith("pptx-"))


def stitch(orig_png: str, pptx_png: str, out_png: str):
    a = Image.open(orig_png).convert("RGB")
    b = Image.open(pptx_png).convert("RGB")
    h = 540
    a = a.resize((int(a.width * h / a.height), h))
    b = b.resize((int(b.width * h / b.height), h))
    gap = 12
    canvas = Image.new("RGB", (a.width + gap + b.width, h + 24), (40, 40, 40))
    canvas.paste(a, (0, 24))
    canvas.paste(b, (a.width + gap, 24))
    d = ImageDraw.Draw(canvas)
    d.text((4, 6), "ORIGINAL (deck)", fill=(255, 255, 255))
    d.text((a.width + gap + 4, 6), "PPTX (editable)", fill=(59, 130, 246))
    canvas.save(out_png)


def main(argv=None):
    argv = argv or sys.argv[1:]
    deck = argv[0]
    wanted = [int(x) for x in argv[1:]]
    base = os.path.join(REPO, "exports", "compare", deck.replace("/", "_"))
    om, pm = os.path.join(base, "deck"), os.path.join(base, "pptx")

    orig = render_deck_pngs(deck, om)
    pptx_path = os.path.join(REPO, "exports", f"{deck}.editable.pptx")
    if not os.path.isfile(pptx_path):
        sys.exit(f"missing {pptx_path}; run scripts/export.sh {deck} pptx first")
    pptx = render_pptx_pngs(pptx_path, pm)

    n = min(len(orig), len(pptx))
    for i in range(n):
        num = i + 1
        if wanted and num not in wanted:
            continue
        out = os.path.join(base, f"cmp-{num:02d}.png")
        stitch(os.path.join(om, orig[i]), os.path.join(pm, pptx[i]), out)
        print(out)


if __name__ == "__main__":
    main()
