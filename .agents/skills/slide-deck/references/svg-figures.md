# Authoring clickable SVG figures

The deck's signature is hand-authored SVG diagrams whose elements are **clickable
deep-links**. A box, label, or arrow links to whatever lets the reader verify or
dig deeper — source code, an MR diff, a doc, a ticket, a paper / arXiv page, or an
in-deck anchor (e.g. a jump to a gallery card). **Link everything that has a
meaningful destination; don't force a link where none makes sense.** A purely
illustrative box can stay unlinked. Inlining the SVG (not `<img src>`) is what keeps
the links clickable in the exported HTML. The three template figures
(`template/images/`) are the reference implementations — copy and adapt them.

## The contract with `build_deck.py`

- One figure per file: `images/<name>.svg`, embedded with a `FIG:<name>` token
  (HTML-comment form) in the template.
- **Root element must be exactly:**
  ```
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 600" font-family="Inter, sans-serif">
  ```
  The builder string-matches `viewBox="0 0 1160 600"` to inject `width`/`height`.
  Design on a **1160×600** canvas (16:9-ish, fits the slide content area).
- **No blank lines anywhere in the file.** A blank line terminates the raw-HTML
  block in markdown and fragments the figure. Keep it dense.
- Sizing variants (same SVG, different token):
  | Token | Rendered size | Use |
  |-------|---------------|-----|
  | `FIG:name`     | 980×507 | a slide that is mostly the figure |
  | `FIGSM:name`   | 860×445 | figure + intro/caption text on one slide |
  | `FIGFULL:name` | full-bleed | on a `_class: bleed` slide |

## The clickable pattern

Wrap the rect **and** its labels in an `<a href target="_blank">` so the whole
element is one hotspot. The `href` points at whatever that element represents:

- **Repo code** — pin to a commit SHA (`/-/blob/<sha>/path`) so the link never rots;
  add a line anchor (`#L84-99`) when you mean specific lines.
- **An MR / diff, a doc page, a ticket** — link the canonical URL.
- **A paper** — link arXiv / the project page (research decks).
- **An in-deck jump** — `href="#p-paper-name"` to leap to a gallery card or another
  slide (works in HTML export; great for "tap a box on the map → its detail card").

Arrows and free-standing labels can be links too, not just boxes — link the edge
that represents an RPC to its handler, a label naming a file to that file.

```xml
<a href="https://your.gitlab/org/repo/-/blob/COMMIT/src/engine.py#L84-99" target="_blank">
  <rect x="780" y="168" width="300" height="150" rx="14"
        fill="#1a1a1a" stroke="#3b82f6" stroke-width="2"/>
  <text x="930" y="210" text-anchor="middle" fill="#f0f0f0" font-weight="700" font-size="23">Engine</text>
  <text x="930" y="240" text-anchor="middle" font-family="JetBrains Mono, monospace"
        fill="#93c5fd" font-size="14">Engine.run(ast)</text>
  <text x="930" y="270" text-anchor="middle" fill="#a0a0a0" font-size="14">the core</text>
</a>
```

Define reusable text styles once and reference by class to keep the file short:

```xml
<style>.t{fill:#f0f0f0;font-weight:700}.m{font-family:'JetBrains Mono',monospace;fill:#93c5fd}.d{fill:#a0a0a0}</style>
```

Per-slide figure width without a new token: define
`section.fig-760 svg[viewBox="0 0 1160 600"]{width:760px;height:393px}` (and
`fig-860`, `fig-700` …) once in the deck's `<style>`, then
`<!-- _class: fs-sm fig-760 -->` on the slide. Keeps `build_deck.py` to the
three standard variants.

## Arrows

Define an arrowhead marker per color in `<defs>`, then `marker-end` a path.
Solid for the primary flow, **dashed for future/roadmap or optional** edges.

```xml
<defs>
  <marker id="g" markerWidth="11" markerHeight="11" refX="8" refY="4" orient="auto">
    <path d="M0,0 L9,4 L0,8 z" fill="#3b82f6"/>
  </marker>
</defs>
<path d="M380,203 C540,170 620,170 780,203" fill="none"
      stroke="#3b82f6" stroke-width="2.5" marker-end="url(#g)"/>
```

Color convention: **blue (accent)** = the main/forward path, **green** = the return/response
path, **grey `#666` dashed** = launch/roadmap/cache edges.

## Diagram archetypes (which template figure to start from)

| Goal | Start from |
|------|-----------|
| Components + how data flows between them (the hero) | `arch-hero.svg` |
| How the codebase is layered / packaged | `layers.svg` |
| What fires step-by-step on one request | `request-flow.svg` (sequence) |

Other useful shapes: a "disk cylinder" for a store/file hop, a topology grid for
processes/GPUs, a timeline for a lifecycle. Stay on the palette and keep labels
to a title + a mono symbol + one grey line.

## Checking layout

Text overflow and overlaps are the common defects — and they hide content. Don't
trust your eye alone; run the **deterministic** checker, which measures every
element with `inkscape --query-all` and flags three failures: a `<text>` spilling
past its box, anything running off the 1160×600 canvas, and partial box overlaps.

```bash
# Deterministic figure check (no browser, exact geometry):
python3 "$SKILL_DIR/scripts/check_layout.py" figs images/*.svg
# or all of a deck's figures:
python3 "$SKILL_DIR/scripts/check_layout.py" figs --dir <deck-dir>
```

Then look, too — a render catches what geometry can't (mystery arrows, ugly
spacing, rotated-label collisions):

```bash
scripts/start.sh          # deck server :8093, re-renders on save — best viewed in context
```

The same script also catches **slide-level** overflow (content clipped off the
slide and invisible in export) — see the slide-deck SKILL.md "Verification".

Notes: the text-overflow check uses inkscape's font metrics, so if Inter isn't
installed there, widths are approximate — `--strict` re-measures in headless
Chromium for an exact gate (needs `pip install playwright`; the browser binary is
usually already cached). Free labels and captions (text not inside any box) carry
no overflow constraint and are skipped.
