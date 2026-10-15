# assets

Shared brand assets used by the theme and exporters.

- `logo.svg` — the agentic-slides mark (a slide whose frame an AI sparkle
  breaks out of). Also the favicon (`themes/favicon.svg`, the skill's `theme/favicon.svg`).
- `logo-wordmark.svg` — mark + `agentic·slides` wordmark (README header).
- `logo-mark.png` — 2× raster of `logo.svg`, embedded bottom-right on every
  slide by `scripts/build_brand_assets.py`; `quarto/shim/brand-link.html` makes it
  link to the repo. PNG, not SVG, because the editable-PPTX exporter
  re-embeds the logo as a picture.
- `fonts/` — vendored deck fonts (Inter, JetBrains Mono; OFL — see
  `fonts/README.md`). Used for export-time layout and embedded into
  editable PPTX exports.

## Changing the logo

1. Edit `logo.svg` (copy it to the favicons; keep `logo-wordmark.svg` in step).
2. Re-render `logo-mark.png` at 2× (64×60 CSS px → 128×120), e.g. a Playwright
   screenshot of a page that inlines the SVG, with a transparent background.
3. `python3 scripts/build_brand_assets.py` — rewrites the BRAND ASSETS block in
   `themes/agentic.css`; then `python3 quarto/scripts/port_theme.py themes/agentic.css
   > quarto/themes/agentic.css` ports it to the decks.
