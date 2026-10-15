# Quarto machinery — Marp-compatible reveal.js decks

Every deck in `../decks/` is a Quarto (reveal.js) deck written in Marp-style
markdown: `slides.qmd`, rendered in place to `slides.html` by the project in
`../_quarto.yml`. They render near pixel-identical to the Marp originals they
were converted from (`scripts/marp2qmd.py`, deterministic) and gain reveal.js
fragments, speaker view, slide menu and search.

```bash
quarto/scripts/setup.sh                    # once: Quarto release + local MathJax
quarto/scripts/render_all.sh --quiet       # every deck (~3 min; safe while serving)
quarto/bin/quarto render decks/templates/visual-gallery/slides.qmd   # one deck (~2 s)
scripts/start.sh                           # deck server: decks :8093, comments/export API :8094
scripts/export.sh templates/visual-gallery html   # or pptx / pdf -> exports/…
python3 quarto/scripts/marp2qmd.py decks/<cat>/<deck>         # convert a Marp deck for good
```

## Deck server (`scripts/serve.py`, :8093)

- Serves `decks/` at the URLs the Marp server used: `/<category>/<deck>/slides.md`
  returns the rendered `slides.html`; `/<deck>/…` short aliases redirect to the
  category path; `/` and `/<category>/` are the landing pages (`scripts/gen_index.py`,
  a post-render step); `/quarto/themes/` and `/quarto/vendor/` come from here.
- A watcher renders a deck when its sources change, one at a time under
  `.quarto/render.lock` (shared with `render_all.sh`); open pages poll
  `/__stamp` and swap in the changed slides without a reload.
- A Marp `slides.md` (e.g. a deck built with a Marp slide-deck skill) is
  converted to `slides.qmd` next to it on every change
  (`marp2qmd.py --keep`); the Marp file stays the source and the edit pane edits it.
- Decks get the repo's browser layers — **Edit** (slide source pane, live
  preview, Ctrl+S save, template decks rebuilt), **Comments** (select → comment
  → `comments.json` in the deck folder) and the **HTML / PPTX / PDF** downloads —
  bundled by `scripts/gen_client.py` into `shim/_client.html` (an
  include-after-body). The backend is `../scripts/pptx_export/export_server.py`,
  run inside this process and answering on :8094 as well (`POST /preview/<deck>`
  renders one slide with pandoc for the live preview). `DECK_API_PORT` (env of `serve.py`) points a test instance at another one.

No `output-dir`: with one, Quarto walks the whole repo (`.venv`, `.git`) on
every render; in place a render takes ~2 s. Render globs start with `/` for
the same reason (Quarto otherwise prefixes them with `**/`).

## How Marp parity works

| Marp behaviour | Mechanism |
|---|---|
| Slides split on `---` only; headings stay inside the slide | `slide-level: 0` (`../_quarto.yml`) |
| markdown-it: raw HTML/SVG blocks stay raw, newline = `<br>`, no smart quotes | `from: commonmark_x+hard_line_breaks-smart` |
| `<!-- _class: … -->`, `paginate`, `header`/`footer`, comments as notes | `shim/marp-compat.html` applies the directives at load |
| Theme CSS on `section`, bare element selectors | `scripts/port_theme.py` rescopes the themes to `.reveal .slides section.slide`, splits `display` onto the visible slide, and ports Marpit's slide-relative `rem` |
| 1280×720 border-box slide, browser-default element styles | `themes/base.css` (slide box + a targeted reset of reveal/Quarto typography) |
| A deck's own `<style>` is slide-scoped with slide-relative `rem` | the Lua filter pipes every `<style>` block through `port_theme.py -` at render time |
| Page links `[s7](#7)` | the shim rewrites them to reveal's `#/7` |
| reveal/Quarto CSS Marp lacks: `.reveal a` styling, Quarto's `.columns:nth-child(3)` margin, print-view `padding: 0` and 11pt root | `base.css` overrides, the shim drops the inlined columns rule, `port_theme.py` adds print copies of slide padding |
| Code blocks shrink to fit (marp-core `downscale-only`) | the shim scales `pre` font-size down when a line overflows |
| A `<div>` stays a `<div>` | `filters/marp-compat.lua`: a heading-led Div must not become a nested `<section>` (a vertical slide); it also repairs Quarto's auto-generated fence under `commonmark_x` |
| MathJax rendered without network | `vendor/mathjax/tex-svg.js` (local, `scripts/setup.sh`; also inlined in self-contained exports) |

`themes/agentic.css` is generated from the repo's theme source; edit
`../themes/agentic.css` and rerun `port_theme.py`.

## Layout

- `bin/quarto` — Quarto from `.dist` (release download, checksum-verified) with its caches in `.state/`
- `filters/`, `shim/`, `themes/` — the Marp-compat layer above; `shim/brand-link.html`
  makes the slide logo link to the repo and sets the tab icon
- `scripts/` — deck server, converter, landing pages, theme porter, e2e check

Smoke test (needs the deck server running):
`python3 quarto/scripts/e2e_check.py http://HOST:8093 http://HOST:8094` — 19 checks
(control bar, local MathJax, comment → comments.json, edit → live preview → save →
in-place update, HTML + PPTX + PDF downloads) on a throwaway deck it stages and
removes afterwards.

## Known gaps

- **`<style scoped>`** is kept unscoped; Marp `![bg]` backgrounds become plain images.
- **Headerless tables** (`| | |` + `|---|---|`): pandoc drops the empty header
  row Marp renders, so such a table loses its top rule and sits a few px higher.
- **Code blocks** get pandoc syntax colours (Marp: highlight.js + theme), and
  marp-core's code fitting can shrink a block further than the shim does.
- **Live preview** renders one slide with pandoc + the Lua filter, not the
  full Quarto pipeline (Quarto-only constructs show approximately until save).
