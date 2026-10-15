# Theme

## agentic (recommended)

Dark background, electric blue (`#3b82f6`) accents, Inter + JetBrains Mono fonts,
the agentic-slides logo bottom-right. The source is `themes/agentic.css`;
`quarto/scripts/port_theme.py` ports it to `quarto/themes/agentic.css`, which the
decks load (rerun it after editing the source). Supports cards, tags, two-column
layouts, and blockquote callouts. Palette and primitives:
[`theme-reference.md`](../.agents/skills/slide-deck/references/theme-reference.md).
The logo is embedded by `scripts/build_brand_assets.py` (see
[`assets/README.md`](../assets/README.md)).

The logo **links to this repo**: [`quarto/shim/brand-link.html`](../quarto/shim/brand-link.html),
included in every deck by `_quarto.yml`, lays an invisible link over it on every
slide and sets the tab icon. The link survives HTML, PDF, and editable-PPTX exports.

Use in front-matter:
```yaml
css:
- ../../../quarto/themes/base.css
- ../../../quarto/themes/agentic.css
```

## custom

Legacy minimal starter theme, not ported to the Quarto decks (`marp2qmd.py`
maps a migrated deck that uses it to `agentic`).

## Features (agentic)

- **`<!-- _class: title paper -->`** — the opening slide of every deck: kicker, title, claim, byline, link pills. Variants `paper`, `mr`, `repo`, `tool`, `research` set the colour and the motif (examples: [visual gallery](../decks/templates/visual-gallery/), slides 4-8; markup: the slide-deck skill's `references/theme-reference.md`)
- **`<!-- _class: lead -->`** — centered slide for the close or a section hero
- **`<!-- _class: invert -->`** — chapter divider with a blue accent bar
- **`<div class="columns">...</div>`** — two equal columns
- **`<div class="columns-wide-left">...</div>`** — 60/40 split
- **`<div class="card">...</div>`** — bordered card box
- **`<span class="tag tag-accent">Label</span>`** — colored badges (accent/green/orange/purple/red)
- **`<div class="time-saved">~2h → ~15m</div>`** — accent savings badge
- **`<a class="repo-link" href="https://github.com/owner/repo">owner/repo</a>`** — GitHub-mark pill; use it for the repo link on title slides
- **Blockquotes** render as callout cards with a blue left border
