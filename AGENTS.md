# agentic-slides — agent notes

Quarto (reveal.js) deck repo, Marp-style markdown: decks under
`decks/<category>/<deck>/slides.qmd` (template decks built from `slides.tpl.qmd`
by the deck's `build_deck.py`), rendered in place by the Quarto project in
`_quarto.yml`; machinery in `quarto/` (see `quarto/README.md`), exporters in
`scripts/` (editable PPTX: `scripts/pptx_export/`), the `agentic` theme source
in `themes/`. See `README.md` for usage; details in `docs/`.

## Skills live in this repo

Agent skills are in `.agents/skills/` — self-contained, no external plugin
needed (`.claude/skills` is a symlink to it, so Claude Code discovers them):

- `onboarding` — walk a newcomer through setup, first deck, review, export,
  publishing. Use it when the user asks how the repo works.
- `slide-deck` — build decks (Quarto plumbing: template, `check_layout.py`,
  export); bundled references for every deck type
  (`references/deck-*.md`, `references/paper-deck.md`), animated figures
  (`references/animating-figures.md`), and source annotation
  (`references/annotate-source.md` + `scripts/annotate/`).
- `deck-feedback` — post-build fresh-eyes reviewer round.
- `address-feedback` — work open slide comments into the deck (written for a
  fresh reader, never echoing the comment), then resolve them.
- `export-all-html` — export every deck as self-contained HTML.

Repo-specific glue when building here:

- Build decks under `decks/<category>/<name>/`; the persistent deck server
  (`scripts/start.sh`, port 8093; systemd unit `slides-server` via
  `scripts/install_services.sh`) serves each at
  `http://<host>:8093/<category>/<name>/slides.md` and re-renders a deck
  within seconds of a save.
- Front-matter `css:` list `../../../quarto/themes/base.css` +
  `../../../quarto/themes/agentic.css` (the template sets it).
- Migrating from Marp: a Marp `slides.md` still works (the deck server
  converts it to `slides.qmd` on every change and keeps `slides.md` as the
  source); `python3 quarto/scripts/marp2qmd.py <deck dir>` converts it for good.
- Paper decks are fact-checked with the in-repo review pipeline: front-matter
  `sources:` list + `scripts/review.sh <category>/<deck>` (drives the skill's
  annotate scripts and `source-review/ingest.py`). Author `annotations.json`
  in the per-deck scratch (`${TMPDIR:-/tmp}/source-review/<slug>/`); contract in
  `source-review/CONTRACT.md`.

## Theme and logo

`themes/agentic.css` is the theme source; the decks load its port,
`quarto/themes/agentic.css` — after editing the source, rerun
`python3 quarto/scripts/port_theme.py themes/agentic.css > quarto/themes/agentic.css`.
The logo block in the source is generated: change `assets/logo.svg` +
`assets/logo-mark.png`, then run `python3 scripts/build_brand_assets.py` (see
`assets/README.md`) and port again. `quarto/shim/brand-link.html` makes the
logo link to the repo and sets the favicon.

## Publishing

GitHub Pages is built by `.github/workflows/pages.yml` → `scripts/build_site.sh`
(decks; prebuilt HTML/PPTX/PDF downloads only with `SITE_EXPORTS=1`, off by
default); `.github/workflows/ci.yml` runs the
tests. Never push unless the user asks.

## Tests

```bash
.venv/bin/python -m pytest scripts/pptx_export/tests source-review/tests   # PPTX exporter, export server, source review (needs the .venv)
node --test scripts/*.test.js                          # comments / edit-mode
.venv/bin/python quarto/scripts/e2e_check.py http://localhost:8093 http://localhost:8094   # needs the running deck server
```
