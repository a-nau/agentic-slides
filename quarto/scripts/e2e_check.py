"""End-to-end smoke test of the Quarto dev-server features: control bar,
comments, edit (live preview, save, reload) and the HTML/PPTX downloads.

    python3 quarto/scripts/e2e_check.py http://HOST:8093 http://HOST:8094 [--shots DIR]

Needs a running deck server (quarto/scripts/serve.py, first URL) and an export
server from this checkout (second URL). Stages a throwaway deck,
decks/templates/e2e-check (the repo ships no example deck), waits for the
server to render it, and removes it afterwards."""
import argparse, json, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("site"); ap.add_argument("api"); ap.add_argument("--shots", default=tempfile.mkdtemp(prefix="e2e-"))
args = ap.parse_args()
REPO = Path(__file__).resolve().parents[2]
DECK = REPO / "decks/templates/e2e-check"
URL = args.site.rstrip("/") + "/templates/e2e-check/slides.md"
API = args.api.rstrip("/")
OUT = Path(args.shots); OUT.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = REPO / ".quarto/server-token"  # token login (absent or unused: SLIDES_AUTH=off)
TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.is_file() else ""
src = DECK / "slides.qmd"
backup = """---
pagetitle: e2e check
css:
- ../../../quarto/themes/base.css
- ../../../quarto/themes/agentic.css
---

<!-- paginate: true -->

<!-- _class: title -->

# E2E **check**

## A throwaway deck staged by quarto/scripts/e2e_check.py

---

## Math

Inline $e^{i\\pi} + 1 = 0$ and display:

$$\\sum_{k=1}^{n} k = \\frac{n(n+1)}{2}$$

---

## Bullet Points

- First point with regular text
- Second point with **bold emphasis**
- Third point with *accented italic*
- Fourth point with `inline code`

---

## Last slide

Done.
"""
DECK.mkdir(parents=True, exist_ok=True)
src.write_text(backup)
for _ in range(120):  # the deck server's watcher renders it
    if (DECK / "slides.html").is_file() and b"Reveal" in (DECK / "slides.html").read_bytes():
        break
    time.sleep(0.5)
cm = DECK / "comments.json"
results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name, detail)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome"); pg = b.new_page(viewport={"width": 1600, "height": 900})  # system Chrome, like the exporters
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        if TOKEN:  # log in once: the server sets the cookie the API calls carry
            pg.goto(args.site.rstrip("/") + "/?token=" + TOKEN)
        pg.goto(URL + "#/3"); pg.wait_for_function("window.Reveal && Reveal.isReady()"); pg.wait_for_timeout(1500)
        pg.mouse.move(400, 400); pg.wait_for_timeout(300)
        labels = pg.eval_on_selector_all(".reveal-osc button", "bs => bs.map(b => b.textContent.trim())")
        check("control bar mounted (HTML, PPTX, PDF, Edit, comments badge)",
              any("HTML" in l for l in labels) and any("PPTX" in l for l in labels) and any("PDF" in l for l in labels)
              and any("Edit" == l for l in labels) and any("💬" in l for l in labels), str(labels))
        pg.screenshot(path=str(OUT / "1-controls.png"))
        check("math typeset by the local MathJax (no CDN)",
              pg.evaluate("document.querySelectorAll('section.slide mjx-container svg').length") >= 2
              and pg.evaluate("[...document.scripts].some(s => /quarto\\/vendor\\/mathjax\\/tex-svg\\.js/.test(s.src))"))

        # comments: select text on slide 3, comment it
        li = pg.locator("section.slide.present li").first
        box = li.bounding_box()
        pg.mouse.move(box["x"] + 2, box["y"] + box["height"] / 2); pg.mouse.down()
        pg.mouse.move(box["x"] + 120, box["y"] + box["height"] / 2, steps=8); pg.mouse.up()
        pg.wait_for_timeout(300)
        check("comment chip appears on selection", pg.is_visible("#cm-chip"))
        pg.click("#cm-chip"); pg.fill("#cm-editor textarea", "e2e: punchier wording"); pg.click("#cm-save")
        pg.wait_for_timeout(800)
        data = json.loads(cm.read_text()) if cm.exists() else {"comments": []}
        c = data["comments"][-1] if data["comments"] else {}
        check("comment saved to the deck's comments.json", c.get("comment") == "e2e: punchier wording"
              and c.get("page") == 3 and c.get("source_file") == "slides.qmd", json.dumps({k: c.get(k) for k in ("page", "quote", "source_file")}))
        check("comment snapshot holds the slide source", "Bullet Points" in c.get("slide_src", ""))
        check("comment highlight rendered", pg.locator(".cm-hl").count() >= 1)
        pg.screenshot(path=str(OUT / "2-comment.png"))

        # edit: open pane, live preview, save -> dev server re-renders + live-reloads
        pg.keyboard.press("Escape"); pg.mouse.move(400, 400); pg.wait_for_timeout(200)
        pg.click("#ed-btn"); pg.wait_for_timeout(1200)
        ta = pg.locator("#ed-ta")
        frag = ta.input_value()
        check("edit pane loads this slide's source", "## Bullet Points" in frag, frag.splitlines()[1] if frag else "")
        check("deck squeezed beside the pane", pg.evaluate("document.querySelector('.reveal').getBoundingClientRect().width") < 1000)
        ta.fill(frag.replace("## Bullet Points", "## Bullet Points LIVE"))
        pg.wait_for_function("Reveal.getCurrentSlide().querySelector('h2').textContent.includes('LIVE')", timeout=20000)
        check("live preview patches the slide before saving", True)
        pg.screenshot(path=str(OUT / "3-edit-preview.png"))
        pg.evaluate("window.__noReload = 1; window.__upd = 0; addEventListener('deck:updated', () => window.__upd++)")
        t0 = time.time()
        pg.keyboard.press("Control+s")
        check("save request returns", True)
        pg.wait_for_function("window.__upd > 0", timeout=30000)
        took = time.time() - t0
        check("saved to slides.qmd", "## Bullet Points LIVE" in src.read_text())
        check("re-rendered slide swapped in place, no page reload",
              pg.evaluate("window.__noReload === 1") and "LIVE" in pg.evaluate("Reveal.getCurrentSlide().querySelector('h2').textContent"),
              f"{took:.1f}s save -> final render shown (the pane previewed it instantly)")
        check("pane still open on the same slide",
              pg.is_visible("#ed-panel") and pg.evaluate("Reveal.getIndices().h") == 2)
        check("comment highlight survives the swap", pg.locator(".cm-hl").count() >= 1)
        pg.screenshot(path=str(OUT / "4-after-save.png"))
        check("no page errors", not errs, "; ".join(errs[:3]))
        b.close()
    src.write_text(backup)  # restore before exporting, so no test edit lands in a cached export

    if TOKEN:
        try:
            code = urllib.request.urlopen(f"{API}/raw/templates/e2e-check", timeout=30).status
        except urllib.error.HTTPError as e:
            code = e.code
        check("API refuses a request without the token", code == 401, f"HTTP {code}")
    for kind, ctype in (("html", "text/html"), ("pptx", "presentation"), ("pdf", "application/pdf")):
        t0 = time.time()
        req = urllib.request.Request(f"{API}/{kind}/templates/e2e-check", headers={"X-Deck-Token": TOKEN})
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read(); disp = r.headers.get("Content-Disposition", "")
            check(f"{kind} download", r.status == 200 and ctype in r.headers.get("Content-Type", "")
                  and len(body) > 10000, f"{len(body)} bytes, {disp}, {time.time() - t0:.1f}s")
finally:
    shutil.rmtree(DECK, ignore_errors=True)
    subprocess.run([sys.executable, str(REPO / "quarto/scripts/gen_index.py")])  # drop it from the listing
print(f"\n{sum(ok for _, ok, _ in results)}/{len(results)} passed")
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
