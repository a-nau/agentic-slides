# Exporting

## Exporting to PDF / PPTX / HTML

```bash
scripts/export.sh templates/visual-gallery          # → exports/templates/visual-gallery.pdf
scripts/export.sh templates/visual-gallery pptx     # → exports/templates/visual-gallery.editable.pptx
scripts/export.sh templates/visual-gallery html     # → exports/templates/visual-gallery.html
scripts/export.sh templates/visual-gallery pdf,pptx # → both formats at once
```

Exports land in the `exports/` directory. The HTML export is a **single
self-contained file** (Quarto `embed-resources`, MathJax inlined), so the
file can be mailed or moved anywhere. Only the theme's Google-Fonts import
stays remote — offline viewers fall back to system fonts. The PDF is reveal.js's
print view, printed by Chrome.

### Export from the dev server

The deck server also answers the comments/export API
(`scripts/pptx_export/export_server.py`, needs the `.venv` from
`scripts/setup.sh`) on **:8094** — same process, one systemd unit
(`slides-server`, from **`scripts/install_services.sh`**). While viewing any
deck on :8093, the hover menu bar (bottom) has download buttons —
**self-contained HTML**, **editable PPTX** and **PDF** — bundled into every
deck by `quarto/scripts/gen_client.py` and hidden automatically when the API
isn't running. Or fetch directly:

```
http://<host>:8094/html/<category>/<deck>
http://<host>:8094/pptx/<category>/<deck>
http://<host>:8094/pdf/<category>/<deck>
```

The first request runs the export (~5–60s); repeats are served from cache
until the deck or the exporter changes. On the GitHub Pages site the same
buttons link the exports prebuilt by `scripts/build_site.sh` when it ran with
`SITE_EXPORTS=1`; otherwise the site has no download buttons.

### Editable PPTX (`pptx`)

`pptx` builds a deck whose objects you can **move and edit** in PowerPoint
(`pptx-edit` is an alias):

```bash
scripts/setup.sh                             # one-time: creates the .venv

scripts/export.sh repos/my-repo pptx         # → exports/repos/my-repo.editable.pptx
```

Text becomes native, editable text boxes. Each figure is embedded as an SVG
picture; to edit its individual pieces, right-click the figure in PowerPoint →
**Group → Ungroup** and PowerPoint converts it into native shapes. The Inter
faces are embedded in the file, so layout survives machines without the font;
PowerPoint uses Consolas for code. Hover tooltips (term definitions, figure
overlays, forensics chips) are HTML-only affordances — their texts are written
to the slide's speaker notes instead of the canvas.

Raster images, local iframe visualizations, gradients,
and clipping are preserved in a browser-rendered slide backdrop when needed.
Those pixels are not individually editable, while text and SVG figures on the
same slide remain native. Remote resources are blocked rather than fetched:
font styles use local fallback; remote `<video>`/`<iframe>` embeds become
PowerPoint online-video shapes (poster tile + source URL) that play in
slideshow mode; other remote content (e.g. remote images) aborts the export.

Carried over: links as real text hyperlinks that keep the deck's colours (no
forced underline; internal "Agenda → section" jumps included), slide chrome on
a shared slide layout (logo, divider bars, auto-renumbering page-number
field), each list as one editable text frame, styled callout/card boxes, accent
bullets, explicit line breaks, and uppercase (`text-transform`) headers.

How it works: loads the rendered deck in reveal.js's print view, reads each
element's rendered geometry and style from headless Chrome (drives the system
Chrome — no browser download), and builds the `.pptx` with `python-pptx`.

Compare a deck against the original visually:

```bash
.venv/bin/python -m scripts.pptx_export.compare repos/my-repo 1 9 20
# writes side-by-side PNGs to exports/compare/<deck>/cmp-NN.png
```

Known limits: **in-figure** hyperlinks (links inside a diagram) are dropped;
on slides that need a browser-rendered backdrop, chrome and styled container
surfaces are part of that backdrop and are not individually editable.
