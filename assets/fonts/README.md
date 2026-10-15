# Vendored fonts

Used by the editable-PPTX exporter's **geometry extraction** (`scripts/pptx_export/extract.py`):
remote fonts are blocked during extraction, so these are injected as local
`@font-face` rules so headless Chrome measures text in the deck's real fonts
(Inter + JetBrains Mono). Without them, every box, wrap point, and
single-line decision would be measured in a fallback sans and deviate from
the rendered deck.

The four Inter faces are also **embedded** into editable-PPTX output
(`_embed_fonts` in `scripts/pptx_export/build.py`), so PowerPoint without Inter
installed doesn't substitute a wider font. OFL 1.1 permits this bundling.

Both families are licensed under the **SIL Open Font License 1.1**
([`OFL.txt`](OFL.txt)).

| File | Family | Source |
|------|--------|--------|
| `Inter-{Regular,Bold,Italic,BoldItalic}.ttf` | Inter | <https://github.com/rsms/inter> via <https://github.com/google/fonts> (variable font pinned to `opsz=14`, `wght=400/700` with `fonttools varLib.instancer`) |
| `JetBrainsMono-{Regular,Bold}.ttf` | JetBrains Mono | <https://github.com/JetBrains/JetBrainsMono> |
