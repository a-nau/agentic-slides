# Repository layout

## Structure

```
_quarto.yml         Quarto project: renders decks/**/slides.qmd in place
decks/              Slide decks, grouped into category folders
  index.html        Generated main landing page (gitignored; category boxes, newest-first)
  tools/            Tool walkthroughs
    index.html      Generated per-category landing page (gitignored), newest-first
    my-tool/
      slides.qmd    Deck source (Marp-style markdown); slides.html + slides_files/ are the render
  repos/            Repo / codebase walkthroughs
  reading-groups/   Paper / reading-group decks
  paper-reviews/    Single-paper deep dives with source-review fact-checking
  investigations/   Investigation / deep-dive decks
  templates/        Starter templates
  mrs/              Per-MR walkthrough decks (one per merge request)
    index.html      Generated landing page, sorted newest-first
    mr-<iid>-<descr>/  e.g. mr-42-add-cache/
  _assets/          In-deck fact-check viewer (copied from source-review/viewer/)
themes/             Theme sources; quarto/scripts/port_theme.py ports them to quarto/themes/
  agentic.css       Dark theme, blue accents, Inter + JetBrains Mono, logo
  custom.css        Legacy minimal starter theme (not ported)
quarto/             Quarto machinery (see quarto/README.md)
  bin/quarto        Quarto from quarto/.dist (release download, quarto/scripts/setup.sh)
  filters/          Lua filter: Marp parity under pandoc
  shim/             Marp directives, brand link + favicon, generated browser layers
  themes/           base.css + the ported agentic.css
  scripts/serve.py  The :8093 deck server (+ :8094 API, re-render on change, Marp auto-convert)
  scripts/gen_index.py  Landing pages (post-render)
  scripts/marp2qmd.py   Marp deck -> Quarto deck
assets/             Logo (SVG + PNG raster) and vendored fonts
source-review/      Fact-check kit: review.json ingest + in-deck source viewer
.agents/skills/     Agent skills (onboarding, slide-deck, deck-feedback, address-feedback, export-all-html)
docs/               Detailed documentation (linked from the README)
scripts/
  setup.sh          One-time setup (.venv, Quarto toolchain, git hooks)
  new_deck.sh       Scaffold decks/<category>/<name>/slides.qmd
  start.sh          Start/restart the deck server (:8093 decks, :8094 comments/export API)
  stop.sh           Stop it
  install_services.sh  Make it a per-user systemd unit (slides-server)
  archive_mr.sh     Move a merged MR deck into decks/mrs/archive/
  export.sh         Export a deck to PDF, editable PPTX, or HTML
  review.sh         Fact-check a deck against its sources (source-review)
  build_site.sh     Build the static GitHub Pages site (decks; + exports with SITE_EXPORTS=1) into _site/
  build_brand_assets.py  Embed the logo into the theme CSS
  client-common.js, deck-controls.html, edit-mode.js, comments.js
                    Browser layers bundled into every deck (quarto/scripts/gen_client.py)
  pptx_export/      Editable-PPTX exporter + the comments/export API server
  install-hooks.sh  Symlink scripts/git-hooks/* into .git/hooks
  git-hooks/
    pre-commit      Regenerate + stage each template deck's generated slides.qmd
```
