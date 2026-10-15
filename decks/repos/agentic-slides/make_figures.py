#!/usr/bin/env python3
"""Generate this deck's figures (images/*.svg).

    python3 make_figures.py && python3 build_deck.py

Every box links into the repo; data-tiphead / data-tip carry the hover text
(no double quotes inside). The loop figure animates with CSS keyframes only;
its static frame (plain attributes) is the complete picture for PDF/PPTX.
"""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"
GH = "https://github.com/a-nau/agentic-slides"
BLOB, TREE = GH + "/blob/main/", GH + "/tree/main/"

BG, CARD, CODE, BORDER = "#111111", "#1a1a1a", "#0d1117", "#2a2a2a"
ACCENT, LIGHT, GREEN, ORANGE, PURPLE, RED = "#3b82f6", "#93c5fd", "#3fb950", "#f0883e", "#bc8cff", "#f85149"
TEXT, SUB, MUTED = "#f0f0f0", "#a0a0a0", "#666666"
ROOT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 600" font-family="Inter, sans-serif">'
BASE = (f".t{{fill:{TEXT};font-weight:700}}.d{{fill:{SUB}}}.mu{{fill:{MUTED}}}"
        f".m{{font-family:'JetBrains Mono',monospace;fill:{LIGHT}}}")


def esc(s):
    return str(s).replace("&", "&amp;").replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")


def tip(head, body):
    return f'data-tiphead="{esc(head)}" data-tip="{esc(body)}"'


def marker(mid, color):
    return (f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{color}"/></marker>')


def box(x, y, w, h, title, lines, href, head, body, stroke=ACCENT, dash="", fs=19, cls="bx"):
    """A linked card: title + (class, text) lines, hover text on the group."""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    s = (f'<a href="{href}" target="_blank"><g class="{cls}" {tip(head, body)}>'
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{stroke}" stroke-width="2"{da}/>'
         f'<text x="{x + 16}" y="{y + 30}" class="t" font-size="{fs}">{esc(title)}</text>')
    for i, (c, t) in enumerate(lines):
        size = 13 if c == "m" else 14
        s += f'<text x="{x + 16}" y="{y + 54 + i * 21}" class="{c}" font-size="{size}">{esc(t)}</text>'
    return s + "</g></a>"


def write(name, css, body):
    svg = ROOT + f"\n<style>{BASE}{css}</style>\n" + body.strip() + "\n</svg>"
    svg = "\n".join(l for l in svg.split("\n") if l.strip())  # no blank lines (markdown)
    (OUT / f"{name}.svg").write_text(svg + "\n")
    print("wrote", f"images/{name}.svg")


# ── architecture: agent, deck folder, one server process, the browser ─────────
def fig_architecture():
    css = ".bx{cursor:help}.bx:hover rect{stroke:#fff}"
    b = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    b += f'<defs>{marker("ah-b", ACCENT)}{marker("ah-g", GREEN)}{marker("ah-m", MUTED)}</defs>'
    # column labels
    for x, t, c in ((30, "AUTHOR", PURPLE), (400, "DECK SERVER · ONE PROCESS", ACCENT), (880, "READER", GREEN)):
        b += f'<text x="{x}" y="28" font-size="13" font-weight="700" letter-spacing="2" fill="{c}">{t}</text>'
    # agent
    b += box(30, 44, 310, 112, "coding agent", [("d", "Claude Code, Codex, any agent"), ("m", "AGENTS.md · .agents/skills/")],
             TREE + ".agents/skills", "Coding agent",
             "Reads AGENTS.md and the skills in .agents/skills/, then writes and rebuilds decks. Nothing to install beyond the repo.",
             stroke=PURPLE)
    # deck folder
    fx, fy, fw, fh = 30, 226, 310, 300
    b += (f'<a href="{TREE}decks" target="_blank"><g class="bx" {tip("Deck folder", "One folder per deck under decks/<category>/<deck>/. The server renders it in place: slides.html sits next to its source.")}>'
          f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-width="2"/>'
          f'<text x="{fx + 16}" y="{fy + 30}" class="t" font-size="19">deck folder</text>'
          f'<text x="{fx + 16}" y="{fy + 52}" class="m" font-size="13">decks/&lt;category&gt;/&lt;deck&gt;/</text></g></a>')
    rows = [("slides.tpl.qmd", "source", TEXT), ("images/*.svg", "figures", TEXT), ("build_deck.py", "assembles", TEXT),
            ("slides.qmd", "generated", SUB), ("slides.html", "rendered", SUB), ("comments.json", "feedback", GREEN)]
    for i, (f, what, col) in enumerate(rows):
        y = fy + 86 + i * 34
        b += (f'<rect x="{fx + 14}" y="{y - 21}" width="{fw - 28}" height="28" rx="6" fill="{CODE}"/>'
              f'<text x="{fx + 26}" y="{y - 2}" font-family="JetBrains Mono, monospace" font-size="14" fill="{col}">{f}</text>'
              f'<text x="{fx + fw - 26}" y="{y - 2}" text-anchor="end" class="mu" font-size="13">{what}</text>')
    # agent <-> folder
    b += f'<path d="M270,158 L270,222" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#ah-b)"/>'
    b += f'<text x="282" y="196" class="d" font-size="13">writes</text>'
    b += f'<path d="M80,224 L80,160" stroke="{GREEN}" stroke-width="2.5" fill="none" stroke-dasharray="6 5" marker-end="url(#ah-g)"/>'
    b += f'<text x="92" y="196" class="d" font-size="13">reads comments when you ask</text>'
    # server process
    b += f'<rect x="392" y="44" width="430" height="482" rx="16" fill="none" stroke="{ACCENT}" stroke-opacity=".45" stroke-dasharray="7 6"/>'
    b += box(412, 62, 390, 132, "watcher", [("d", "polls deck sources every second"), ("d", "quarto render → slides.html, ~2 s"),
                                             ("m", "serve.py · watch() / scan()")],
             BLOB + "quarto/scripts/serve.py#L89-L136", "Watcher",
             "Compares each deck's newest source mtime with slides.html and renders only the stale deck, one at a time under .quarto/render.lock. It renders slides.qmd as it is: it does not run build_deck.py. A Marp slides.md is converted to slides.qmd first.")
    b += box(412, 214, 390, 132, ":8093  decks", [("d", "/<category>/<deck>/slides.md → slides.html"), ("d", "landing pages · /__stamp for live update"),
                                                   ("m", "serve.py · Handler.do_GET")],
             BLOB + "quarto/scripts/serve.py#L214-L241", "Deck port",
             "A page load is a plain file read. The URL ends in slides.md, the Marp-era path, so old links keep working; it returns slides.html. Open pages poll /__stamp and swap in re-rendered slides without a reload.")
    b += box(412, 366, 390, 140, ":8094  API", [("d", "comments · edit (raw, preview)"), ("d", "HTML · PPTX · PDF downloads"),
                                                 ("m", "scripts/pptx_export/export_server.py")],
             BLOB + "scripts/pptx_export/export_server.py", "Comments and export API",
             "Same process, second port; :8093 answers these routes too, but deck pages and exported HTML call :8094. Writes comments.json and the edited source, renders an edited slide with pandoc for the live preview, and runs scripts/export.sh for downloads (cached until the deck changes).",
             stroke=GREEN)
    # folder <-> watcher
    b += f'<path d="M344,262 C372,262 380,128 408,128" stroke="{MUTED}" stroke-width="2.5" fill="none" marker-end="url(#ah-m)"/>'
    # API -> folder
    b += f'<path d="M410,440 L344,440" stroke="{GREEN}" stroke-width="2.5" fill="none" marker-end="url(#ah-g)"/>'
    # browser
    b += (f'<a href="{BLOB}quarto/scripts/gen_client.py" target="_blank"><g class="bx" {tip("Browser layers", "quarto/scripts/gen_client.py bundles the control bar, edit mode and comments into every deck; they hide themselves when the API is not reachable.")}>'
          f'<rect x="880" y="44" width="250" height="482" rx="12" fill="{CARD}" stroke="{GREEN}" stroke-width="2"/>'
          f'<text x="896" y="74" class="t" font-size="19">browser</text>'
          f'<text x="896" y="96" class="d" font-size="14">the deck, plus layers</text></g></a>')
    layers = [("live update", "swaps changed slides"), ("Edit pane", "slide source, Ctrl+S"),
              ("💬 Comment", "select text, write a note"), ("downloads", "HTML · PPTX · PDF"), ("Tips", "hover cards on/off")]
    for i, (n, d) in enumerate(layers):
        y = 122 + i * 78
        b += (f'<rect x="896" y="{y}" width="218" height="62" rx="8" fill="{CODE}" stroke="{BORDER}"/>'
              f'<text x="910" y="{y + 26}" class="t" font-size="15">{n}</text>'
              f'<text x="910" y="{y + 48}" class="d" font-size="13">{d}</text>')
    b += f'<path d="M806,280 L874,280" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#ah-b)"/>'
    b += f'<path d="M878,440 L808,440" stroke="{GREEN}" stroke-width="2.5" fill="none" marker-end="url(#ah-g)"/>'
    # legend
    b += (f'<line x1="30" y1="566" x2="62" y2="566" stroke="{ACCENT}" stroke-width="2.5"/>'
          f'<text x="70" y="571" class="d" font-size="14">deck goes out</text>'
          f'<line x1="200" y1="566" x2="232" y2="566" stroke="{GREEN}" stroke-width="2.5"/>'
          f'<text x="240" y="571" class="d" font-size="14">feedback comes back</text>'
          f'<text x="1130" y="571" text-anchor="end" class="mu" font-size="13">binds 127.0.0.1; SLIDES_HOST=0.0.0.0 opens it to the network, no login</text>')
    write("architecture", css, b)


# ── loop: build, look, comment, address, resolve; a dot orbits, stages light up ──
def fig_loop():
    T = 12
    cx, cy, rx, ry = 580, 290, 360, 205
    W, H = 280, 92
    stages = [  # name, who, line, mono, href, tip
        ("build", "agent", "writes the deck from sources", "slide-deck skill", BLOB + ".agents/skills/slide-deck/SKILL.md",
         "The agent follows the slide-deck skill: research, storyboard, SVG figures, build, check the layout."),
        ("look", "you", "the open page updates itself", "serve.py · /__stamp", BLOB + "quarto/scripts/serve.py",
         "The server re-renders a saved deck in a few seconds (about 2 s per deck, quarto/README.md); the open page swaps in the changed slides."),
        ("comment", "you", "select text → 💬 Comment", "comments.json", BLOB + "scripts/comments.js",
         "Each note is saved with its quote, slide, heading and stable slide id in the deck folder."),
        ("address", "agent", "folds each note into the slide", "address-feedback skill", BLOB + ".agents/skills/address-feedback/SKILL.md",
         "Starts when you ask it, e.g. address the open comments: the agent does not watch comments.json. It fixes the cause for a fresh reader, never echoes the comment, then rebuilds."),
        ("resolve", "agent", "closes it, history kept", "POST /comments/<deck>", BLOB + "docs/comments-and-edit-mode.md",
         "Resolve via the API with expected_updated: a stale write returns 409, so nobody's edit is lost."),
    ]
    angles = [-90 + k * 72 for k in range(5)]
    css = ".lp-b{cursor:help}.lp-b:hover rect.lp-f{stroke:#fff}"
    # the dot sits at the top of the ellipse (its static position) and walks the
    # ellipse through 60 translate waypoints: no offset-path, so exports and the
    # layout checker see a real, on-canvas position
    steps = []
    for i in range(61):
        th = -math.pi / 2 + 2 * math.pi * i / 60
        dx, dy = rx * math.cos(th), ry * math.sin(th) + ry
        steps.append(f"{100 * i / 60:.2f}%{{transform:translate({dx:.1f}px,{dy:.1f}px)}}")
    css += f".lp-dot{{animation:lp-dot {T}s linear infinite}}@keyframes lp-dot{{{''.join(steps)}}}"
    b = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    b += (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{BORDER}" stroke-width="3" '
          f'stroke-dasharray="2 10" stroke-linecap="round"/>')
    # the dot runs under the cards: it shows between stages, the lit card marks
    # where it is; in the static frame it is hidden under stage 1
    b += (f'<g class="lp-dot"><circle cx="{cx}" cy="{cy - ry}" r="9" fill="{ACCENT}"/>'
          f'<circle cx="{cx}" cy="{cy - ry}" r="17" fill="{ACCENT}" opacity=".25"/></g>')
    seg = 100 / 5
    for k, ((name, who, line, mono, href, t), ang) in enumerate(zip(stages, angles)):
        a = math.radians(ang)
        x, y = cx + rx * math.cos(a) - W / 2, cy + ry * math.sin(a) - H / 2
        col = PURPLE if who == "agent" else GREEN
        g = f"lp-g{k}"
        s0 = k * seg
        # glow: hidden in the static frame (attribute), lit while the dot passes this stage
        if k == 0:
            kf = f"0%,{seg - 4:.0f}%{{opacity:1}}{seg:.0f}%,{100 - 4:.0f}%{{opacity:0}}100%{{opacity:1}}"
        else:
            kf = f"0%,{s0 - 4:.0f}%{{opacity:0}}{s0:.0f}%,{s0 + seg - 4:.0f}%{{opacity:1}}{s0 + seg:.0f}%,100%{{opacity:0}}"
        css += f".{g}{{animation:{g} {T}s infinite}}@keyframes {g}{{{kf}}}"
        b += (f'<a href="{href}" target="_blank"><g class="lp-b" {tip(name, t)}>'
              f'<rect class="lp-f" x="{x:.0f}" y="{y:.0f}" width="{W}" height="{H}" rx="14" fill="{CARD}" stroke="{col}" stroke-width="2"/>'
              f'<rect class="{g}" x="{x:.0f}" y="{y:.0f}" width="{W}" height="{H}" rx="14" fill="{ACCENT}" fill-opacity=".10" stroke="{ACCENT}" stroke-width="3" opacity="0"/>'
              f'<text x="{x + 18:.0f}" y="{y + 30:.0f}" class="t" font-size="20">{k + 1} · {name}</text>'
              f'<text x="{x + W - 16:.0f}" y="{y + 29:.0f}" text-anchor="end" font-size="13" font-weight="700" fill="{col}">{who.upper()}</text>'
              f'<text x="{x + 18:.0f}" y="{y + 55:.0f}" class="d" font-size="15">{esc(line)}</text>'
              f'<text x="{x + 18:.0f}" y="{y + 78:.0f}" class="m" font-size="13">{esc(mono)}</text></g></a>')
    # the hand-off 3 -> 4: the agent does not watch comments.json; you ask it
    b += f'<defs>{marker("lp-h", PURPLE)}</defs>'
    b += (f'<path d="M790,506 L790,540 L370,540 L370,512" stroke="{GREEN}" stroke-width="2.5" fill="none" '
          f'stroke-dasharray="6 5" marker-end="url(#lp-h)"/>')
    b += (f'<a href="{BLOB}.agents/skills/address-feedback/SKILL.md" target="_blank"><g class="lp-b" '
          f'{tip("Hand-off", "Nothing watches comments.json. When you are done commenting, tell the agent, e.g. address the open comments; that request loads the address-feedback skill.")}>'
          f'<rect x="372" y="521" width="416" height="38" rx="19" fill="{BG}" stroke="{GREEN}" stroke-width="2"/>'
          f'<text x="580" y="546" text-anchor="middle" font-size="17" fill="{TEXT}"><tspan font-weight="700" fill="{GREEN}">you ask: </tspan>'
          f'\u201caddress the open comments\u201d</text></g></a>')
    b += (f'<text x="{cx}" y="{cy - 10}" text-anchor="middle" class="t" font-size="24">one deck, many rounds</text>'
          f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" class="d" font-size="16">until no comment is open</text>')
    b += (f'<text x="40" y="584" font-size="13" font-weight="700" fill="{GREEN}">YOU</text>'
          f'<text x="76" y="584" class="d" font-size="13">read and comment in the browser</text>'
          f'<text x="330" y="584" font-size="13" font-weight="700" fill="{PURPLE}">AGENT</text>'
          f'<text x="384" y="584" class="d" font-size="13">edits files, never the rendered page</text>')
    write("loop", css, b)


# ── pipeline: source → build_deck.py → slides.qmd → quarto render → exports ────
def fig_pipeline():
    css = ".bx{cursor:help}.bx:hover rect{stroke:#fff}"
    b = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    b += f'<defs>{marker("pp-b", ACCENT)}{marker("pp-m", MUTED)}{marker("pp-g", GREEN)}</defs>'
    W, H, Y = 190, 116, 52
    top = [  # x, title, lines, href, head, tip, stroke
        (30, "slides.tpl.qmd", [("m", "+ images/*.svg"), ("d", "you and the agent"), ("d", "edit these")],
         BLOB + "decks/repos/agentic-slides/slides.tpl.qmd", "Deck source",
         "Marp-style Markdown with FIG tokens where figures go; the SVGs sit in images/. This deck's own source is linked.", ACCENT),
        (262, "build_deck.py", [("m", "FIG token → <svg>"), ("d", "run by the agent, or"), ("d", "the Edit pane on save")],
         BLOB + ".agents/skills/slide-deck/template/build_deck.py", "build_deck.py",
         "Lives in each deck folder: python3 build_deck.py. Replaces each FIG token with the SVG file inline, so links and hover cards keep working, and adds permalinks. The server watcher never runs it; the agent does, and the Edit pane does after a save.", ACCENT),
        (494, "slides.qmd", [("m", "generated"), ("d", "never edit by hand;"), ("d", "committed, kept in sync")],
         BLOB + "decks/repos/agentic-slides/slides.qmd", "slides.qmd",
         "What Quarto renders. It is committed, because GitHub Pages and a fresh clone render it as is; the pre-commit hook rebuilds and stages it for every deck with staged changes, so it never lags the template.", BORDER),
        (726, "quarto render", [("m", "_quarto.yml"), ("d", "the watcher runs it"), ("d", "on every change")],
         BLOB + "_quarto.yml", "Quarto render",
         "Slides split on --- only (slide-level 0), CommonMark like Marp; quarto/filters/marp-compat.lua and quarto/shim/ keep Marp behaviour; quarto/themes/ styles it.", ACCENT),
        (958, "slides.html", [("m", "reveal.js deck"), ("d", "served on :8093,"), ("d", "next to the source")],
         BLOB + "quarto/scripts/serve.py", "slides.html",
         "Rendered in place, gitignored. The deck server serves it as /<category>/<deck>/slides.md.", GREEN),
    ]
    for x, title, lines, href, head, t, st in top:
        b += box(x, Y, W, H, title, lines, href, head, t, stroke=st, fs=18)
    for i in range(4):
        x1 = top[i][0] + W + 4
        b += f'<path d="M{x1},{Y + H / 2} L{x1 + 34},{Y + H / 2}" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#pp-b)"/>'
    # Marp branch
    b += box(30, 232, W, 92, "slides.md", [("d", "a Marp deck")], BLOB + "docs/decks.md", "Marp deck",
             "Drop a Marp slides.md into a deck folder: it stays the source, converted on every change.", stroke=MUTED, dash="6 5", fs=18)
    b += box(262, 232, 238, 92, "marp2qmd.py --keep", [("d", "converts it on change")], BLOB + "quarto/scripts/marp2qmd.py",
             "marp2qmd.py", "Rewrites only what pandoc cannot read the Marp way: front matter, image sizing, separators. Without --keep it migrates the deck for good.",
             stroke=MUTED, dash="6 5", fs=18)
    b += f'<path d="M224,278 L258,278" stroke="{MUTED}" stroke-width="2.5" fill="none" stroke-dasharray="6 5" marker-end="url(#pp-m)"/>'
    b += f'<path d="M504,278 C566,278 589,230 589,174" stroke="{MUTED}" stroke-width="2.5" fill="none" stroke-dasharray="6 5" marker-end="url(#pp-m)"/>'
    # export bus
    BUS = 384
    xs = [30 + 125, 320 + 125, 610 + 125, 900 + 125]
    b += f'<path d="M1053,{Y + H + 2} L1053,{BUS} L{xs[0]},{BUS}" stroke="{GREEN}" stroke-width="2.5" fill="none"/>'
    for x in xs:
        b += f'<path d="M{x},{BUS} L{x},{BUS + 32}" stroke="{GREEN}" stroke-width="2.5" fill="none" marker-end="url(#pp-g)"/>'
    b += f'<text x="1040" y="{BUS - 12}" text-anchor="end" class="d" font-size="14">scripts/export.sh &lt;category/deck&gt; html | pdf | pptx</text>'
    bottom = [
        (30, "HTML", [("m", "export.sh … html"), ("d", "one self-contained file,"), ("d", "MathJax inlined")], BLOB + "scripts/export.sh",
         "HTML export", "Quarto embed-resources plus MathJax inlined: mail it anywhere. Comments post back to the API when it is reachable."),
        (320, "PDF", [("m", "export.sh … pdf"), ("d", "reveal.js print view,"), ("d", "printed by Chrome")], BLOB + "scripts/export.sh",
         "PDF export", "One page per slide at 1280 by 720. Animated figures show their static frame."),
        (610, "editable PPTX", [("m", "scripts/pptx_export/"), ("d", "native text boxes,"), ("d", "SVG-picture figures")], TREE + "scripts/pptx_export",
         "Editable PPTX", "extract.py reads every element's geometry and style from headless Chrome; build.py writes native PowerPoint objects with python-pptx."),
        (900, "GitHub Pages", [("m", "scripts/build_site.sh"), ("d", "every deck; downloads"), ("d", "opt-in")], BLOB + "scripts/build_site.sh",
         "GitHub Pages", "On every push to main, .github/workflows/pages.yml builds the read-only site: every deck; prebuilt HTML, PPTX and PDF only when run by hand with exports on."),
    ]
    for x, title, lines, href, head, t in bottom:
        b += box(x, BUS + 36, 250, 116, title, lines, href, head, t, stroke=GREEN, fs=18)
    write("pipeline", css, b)


# ── fact-check: sources → fetch → agent claims → annotate → ingest → Review pane ─
def fig_factcheck():
    css = ".bx{cursor:help}.bx:hover rect{stroke:#fff}"
    b = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    b += f'<defs>{marker("fc-b", ACCENT)}{marker("fc-p", PURPLE)}</defs>'
    W, H = 310, 120
    A = BLOB + ".agents/skills/slide-deck/scripts/annotate/"
    row1 = [
        (40, "sources:", [("m", "front matter of the deck"), ("d", "paper PDF or blog HTML URLs")], BLOB + "decks/paper-reviews/attention/slides.tpl.qmd",
         "sources:", "A YAML list in the deck's front matter, e.g. the arXiv PDF of the paper the deck explains.", ACCENT),
        (425, "fetch.py", [("m", "source.pdf + dump.txt"), ("d", "one workdir per source")], A + "fetch.py",
         "fetch.py", "Downloads each source once into the per-deck scratch folder and dumps its text, so quotes can be copied exactly.", ACCENT),
        (810, "agent: claims", [("m", "annotations.json"), ("d", "deck text, source quote, verdict")], BLOB + "source-review/CONTRACT.md",
         "Agent step", "The agent pairs each claim on a slide with the verbatim passage that backs it and picks the verdict. review.sh stops with exit code 2 until this file exists; run it again afterwards.", PURPLE),
    ]
    row2 = [
        (810, "annotate_*.py", [("m", "annotate_pdf.py / _html.py"), ("d", "highlights each quote")], A + "annotate_pdf.py",
         "Annotate", "Finds each quoted passage in the source and highlights it; a paraphrased quote does not match.", ACCENT),
        (425, "ingest.py", [("m", "review.json + annotated.*"), ("d", "claims, tally, page jumps")], BLOB + "source-review/ingest.py",
         "ingest.py", "Writes review.json (the contract in source-review/CONTRACT.md) and the annotated sources into the deck folder.", ACCENT),
        (40, "Review button", [("m", "decks/_assets/review.js"), ("d", "slide claim ↔ source page")], BLOB + "source-review/README.md",
         "In-deck viewer", "Highlights the claims on the current slide; selecting one opens the annotated source at that page in a side pane.", GREEN),
    ]
    for x, title, lines, href, head, t, st in row1:
        b += box(x, 60, W, H, title, lines, href, head, t, stroke=st)
    for x, title, lines, href, head, t, st in row2:
        b += box(x, 270, W, H, title, lines, href, head, t, stroke=st)
    b += f'<path d="M354,120 L419,120" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#fc-b)"/>'
    b += f'<path d="M739,120 L804,120" stroke="{PURPLE}" stroke-width="2.5" fill="none" marker-end="url(#fc-p)"/>'
    b += f'<path d="M965,184 L965,264" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#fc-b)"/>'
    b += f'<path d="M806,330 L741,330" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#fc-b)"/>'
    b += f'<path d="M421,330 L356,330" stroke="{ACCENT}" stroke-width="2.5" fill="none" marker-end="url(#fc-b)"/>'
    b += (f'<text x="40" y="32" class="d" font-size="16" letter-spacing="0.5">scripts/review.sh &lt;category&gt;/&lt;deck&gt;, TWICE: '
          f'RUN 1 STOPS (EXIT 2) FOR THE AGENT STEP, RUN 2 FINISHES</text>')
    # verdicts
    b += f'<text x="40" y="448" class="mu" font-size="13" letter-spacing="1.5">VERDICT PER CLAIM</text>'
    verdicts = [("supported", GREEN, "the source backs it"), ("contradicted", RED, "fix the slide, re-run"),
                ("not_found", ORANGE, "fine if it is context"), ("unverifiable", SUB, "check it yourself"),
                ("reference", MUTED, "terminology, no check")]
    for i, (v, c, d) in enumerate(verdicts):
        x = 40 + i * 220
        b += (f'<rect x="{x}" y="462" width="200" height="40" rx="20" fill="{CARD}" stroke="{c}" stroke-width="2"/>'
              f'<text x="{x + 100}" y="488" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="14" fill="{c}">{v}</text>'
              f'<text x="{x + 4}" y="530" class="d" font-size="17">{d}</text>')
    b += (f'<text x="40" y="580" font-size="19" fill="{TEXT}">The agent grades its own claims: check them in the Review pane, '
          f'where a claim opens its source quote.</text>')
    write("factcheck", css, b)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_architecture()
    fig_loop()
    fig_pipeline()
    fig_factcheck()
