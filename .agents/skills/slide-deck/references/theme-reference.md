# agentic theme reference

`quarto/themes/agentic.css` (ported from the repo's `themes/agentic.css` by
`quarto/scripts/port_theme.py`) is the default. It is self-contained — the agentic-slides
wordmark is baked in as a base64 data-URI, so the CSS works standalone. The
template already sets it in front-matter (paths relative to a deck in
`decks/<category>/<name>/`; paginate via `<!-- paginate: true -->`):

```yaml
---
css:
- ../../../quarto/themes/base.css
- ../../../quarto/themes/agentic.css
---
```

## Color palette (use these exact hexes in SVGs too)

| Token | Hex | Use |
|-------|-----|-----|
| accent | `#3b82f6` | primary accent, box borders, arrows |
| accent-light | `#93c5fd` | inline code / monospace in figures |
| bg-slide | `#111111` | slide + SVG background |
| bg-card | `#1a1a1a` | card / box fill |
| bg-code | `#0d1117` | code blocks, callout panels, "disk" shapes |
| text-primary | `#f0f0f0` | headings, box titles |
| text-secondary | `#a0a0a0` | body / descriptions |
| text-muted | `#666` | de-emphasized, roadmap/future arrows |
| accent-green | `#3fb950` | secondary flow (e.g. responses), links |
| accent-orange | `#f0883e` | warnings |
| accent-red | `#f85149` | breaking/danger |
| accent-purple | `#bc8cff` | cross-cutting concerns |
| border-subtle | `#2a2a2a` | hairlines, lifelines, panel borders |

Fonts: **Inter** (body), **JetBrains Mono** (code / file names).

## Logo link

The bottom-right logo links to the agentic-slides repo on every slide
(`quarto/shim/brand-link.html`, included in every deck by `_quarto.yml`,
lays an invisible `<a class="brand-link">` over it). Keep the bottom-right
corner free of other links.

## Slide classes (`<!-- _class: ... -->` at top of a slide)

| Class | Effect |
|-------|--------|
| `title <type>` | **Opening slide of every deck.** `<type>` is `paper`, `mr`, `repo`, `tool` or `research` (sets colour + motif; omit for accent). See *Title page* below. |
| `lead` | Centered slide for the close or a section hero. |
| `invert` | Chapter-divider slide with a blue accent bar. Use between major sections. |
| `bleed` | Full-bleed, no padding/logo/page-number — for embeds/full figures. |

## Title page

One layout for every deck type; only the kicker text and the `<type>` change.
Examples of all five: `decks/templates/visual-gallery/` (slides 4-8).

```markdown
<!-- _class: title paper -->

<p class="kicker">Paper deep dive</p>

# **Vaswani et al. (2017):** Attention Is All You Need

## One-line claim with the **headline number**

<p class="byline">Google Brain · NIPS 2017</p>

<p class="links"><a href="…">arXiv</a><a href="…">PDF</a><a href="…">code</a></p>
```

- Kickers: `Paper deep dive` · `MR review` · `Repo tour` · `Tool demo` ·
  `Research overview`. `**bold**` in the H1 takes the type colour — bold one
  word, or for paper decks the leading citation (`**Authors et al. (year):**`,
  rendered smaller via `section.title.paper h1` so long titles stay ≤ 3 lines).
- MR reviews add `<p class="stats"><span class="add">+127</span><span class="del">−8</span><span>4 commits</span>…</p>`.
- Repo tours put `<a class="repo-link" href="…">owner/repo</a>` in `.links`.
- Link pills get an icon from the URL (arXiv, PDF, GitHub → code, NeurIPS/CVF
  proceedings, ar5iv → sections, YouTube → video; anything else → link). Set it
  explicitly where the URL doesn't say what it is: `<a class="project" …>`.
  Classes: `paper` `arxiv` `pdf` `code` `project` `website` `video`
  `proceedings` `sections` `data` `mr` `diff` `link`.
- Keep text left of the motif: H1 ≤ 3 lines, subtitle ≤ 2 lines.

## Layout primitives (raw HTML, needs `html: true`)

```html
<div class="columns"> <div>…left…</div> <div>…right…</div> </div>
<div class="columns-wide-left"> … </div>     <!-- 60/40 split -->
<div class="columns-wide-right"> … </div>     <!-- 40/60 split -->

<div class="card"> ### Title + content </div>   <!-- bordered box -->
```

## Inline components

```html
<span class="tag tag-accent">Feature</span>     <!-- accent / green / orange / purple / red -->
<div class="time-saved">~2 hours → ~15 min</div>   <!-- accent savings badge -->
<a class="repo-link" href="https://github.com/owner/repo">owner/repo</a>   <!-- repo link pill (title slide) -->
```

- **Blockquotes** (`> …`) render as callout cards with a blue left border — use
  for the one-line definition of each concept.
- **Code blocks** get the `#0d1117` background and a blue left border.
- **Tables** are styled for the dark theme — ideal for the "Where to look" map.
- **Math**: inline `$…$` and block `$$…$$` (KaTeX) work out of the box.

## Markdown anchors for the agenda

Quarto lowercases a heading and hyphenates it into an id. `# The Big Picture`
becomes `#the-big-picture`, so the agenda can link to it:

```markdown
1. [**The Big Picture**](#the-big-picture) — what it is & how it fits
```

For links that survive retitling/reordering, use the per-slide UUID permalinks
instead (see `scripts/assign_slide_ids.py` and SKILL.md).
