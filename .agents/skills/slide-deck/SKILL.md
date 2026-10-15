---
name: slide-deck
description: Use when asked to build a slide deck, presentation, tech talk, brown-bag, onboarding/repo-introduction, tool/workflow demo, paper reading-group, or merge-request/code-review walkthrough slides — especially to explain a codebase, tool, change, papers, or architecture to others. Also use to highlight, annotate, or fact-check a paper or blog post against its source document (bundled annotate-source reference + scripts).
version: 1.6.4
tags: [slides, presentation, quarto, revealjs, svg, onboarding, code-review]
---

# slide-deck

## Overview

> **Quarto/reveal.js** deck skill for the agentic-slides repo (the repo this
> skill ships in: Quarto project at its root, machinery in `quarto/`). Where a bundled
> reference still says "Marp", read "Quarto/reveal.js": the theme classes,
> `<!-- _class: … -->` / `<!-- paginate: … -->` directives, FIG tokens and the
> hover toolkit work unchanged.

Build Quarto (reveal.js) slide decks that explain a **repo, tool, architecture, merge request,
or set of papers**. House style: the dark blue-accented `agentic` theme, **broad concepts
before code**, claim-first slides, **hand-authored SVG diagrams where every box
and file name is a clickable deep-link**. Let the reader digest a lot fast: be
concise, lead with one visual per slide, link everything so readers *verify*
rather than take your word. Standards: "Slide Quality Bar" below.

A deck is Markdown (`slides.tpl.qmd`) + SVG figures (`images/*.svg`), assembled by
`build_deck.py` into a `slides.qmd` that Quarto renders to reveal.js HTML (and
HTML/PDF exports). Copy `template/` and edit it.

Sibling skill (same plugin): **`deck-feedback`** — the post-build
junior-questions round (Procedure step 6). Bundled references (this skill):
single-paper review deck for a reading group → **`references/paper-deck.md`**
(the canonical paper arc: research → draft → fact-map); animated figure
needed, or an animated SVG renders **blank in the built deck** →
`references/animating-figures.md`; highlight/fact-check a document (and the
scripts behind the paper fact-map pipeline, `scripts/annotate/`) →
`references/annotate-source.md`.

## Choose a mode

Use the smallest mode that matches the request:

1. **Create a deck (default).** Build and verify it, then tell the user the
   deck path and a live-preview URL reachable from *their* machine. Unless
   they already asked for more, stop and offer the three post-delivery options
   in Procedure step 6 verbatim.
2. **Run the automated review loop.** For an existing deck, invoke
   `deck-feedback`; do not inspect source material or run grounding.
3. **Verify claims against sources.** For a paper or blog, use
   `references/annotate-source.md`; for a paper deck, run Phase 3 of
   `references/paper-deck.md`. Do not run the comprehension review.

If a new-deck request already includes review or grounding, report the initial
deck location before continuing. When it includes both, review and rebuild
first, then ground the final wording.

## Start here

```bash
REPO="$(git rev-parse --show-toplevel)"     # run from inside the agentic-slides repo
SKILL_DIR="$REPO/.agents/skills/slide-deck"
DECK_DIR="$REPO/decks/<category>/<name>"

cp -r "$SKILL_DIR/template" "$DECK_DIR"
# edit slides.tpl.qmd + images/*.svg
python3 "$DECK_DIR/build_deck.py"           # slides.tpl.qmd + SVGs -> slides.qmd
# The persistent deck server (:8093, systemd unit slides-server) re-renders the
# deck within seconds of every save: http://<host>:8093/<category>/<name>/slides.md
# To render by hand (e.g. before check_layout.py):
(cd "$REPO" && quarto/bin/quarto render "$DECK_DIR/slides.qmd")   # -> $DECK_DIR/slides.html (~2 s)

# Export ONLY when the user explicitly asks for a file (html/pptx/pdf):
# bash "$SKILL_DIR/scripts/export.sh" "$DECK_DIR" html
```

**Do not export by default.** The deliverable is the built deck (`slides.qmd`
+ rendered HTML) and the live preview. Run `export.sh` only when the user
explicitly asks for an exported file, and then only in the format they request.

`build_deck.py` lives **inside the deck** (it reads `slides.tpl.qmd` and
`images/` next to itself). The theme (`quarto/themes/`), the Marp-directive
shim and the render settings (`_quarto.yml` at the repo root) are shared by every deck.
One-time setup: `quarto/scripts/setup.sh` (user-level Quarto release + local
MathJax; no Docker).

### What the Quarto backbone adds (use where it helps the reader)

- **Step-by-step builds**: `::: {.fragment}` … `:::` reveals a block on the next
  key press (also `{.fragment .fade-in-then-semi-out}` etc.). Use for
  mechanisms that unfold in steps; the checker shows all fragments.
- **Speaker notes**: `::: {.notes}` … `:::` (or a plain HTML comment, as in Marp);
  press `S` for the speaker view with timer and next-slide preview.
- **Slide menu / search**: `M` opens a slide list, `Ctrl+Shift+F` searches.
- **Math**: `$…$` and `$$…$$` (MathJax 3, served locally — works offline and in
  self-contained exports).
- **Reading rules (CommonMark, like Marp's markdown-it)**: slides split on `---`
  only; a raw HTML block ends at the first blank line, and its content stays
  raw; `{…}` attributes need double-quoted values.

## Deck types

Pick the type that matches the job, then open its reference for a concrete slide
arc, the signature techniques, a quality-bar checklist, and the anti-patterns to
avoid.

**Arcs are guidelines, not molds.** Check the fit for *this* subject and
audience first, adjust (add, cut, reorder, blend types), then build. A small MR
might need 6 slides, a repo walkthrough 18. One constant: **concepts first,
then code, with a clickable path from every claim to the source.**

| Type | Audience & goal | Reference |
|------|-----------------|-----------|
| **Repo introduction** | New engineer onboarding to a codebase: architecture, subsystems, flow, where to look. | `references/deck-repo-intro.md` |
| **MR review** | Reviewer who must understand a change well enough to review it — what changed, what could go wrong, where to look. | `references/deck-mr-review.md` |
| **Tool presentation** | Teammate who might adopt a new tool or workflow: feel the pain, see it work, get the on-ramp. | `references/deck-tool-presentation.md` |
| **Research — literature overview** | Reading-group peers mapping a *body* of recent papers: landscape, taxonomy, key ideas, takeaways. | `references/deck-research-overview.md` |
| **Research — paper deep dive** | Reading-group peers spending a session on *one* paper: mechanism, results, ablations, critique. | `references/paper-deck.md` (canonical); `references/deck-research-deep-dive.md` is its precursor. |

## Inputs

- **Subject** — repo, tool, architecture, MR, code change, or papers.
- **Audience** — newcomer, reviewer, adopter, reading group, operator, or mixed.
- **Source links** — repo/MR/diff URL, docs/tickets, and a commit SHA for stable
  code links.
- **Output** — built deck + live preview. Export to a file (HTML/PPTX/PDF) only
  on explicit request; HTML when clickable links matter.

Infer missing inputs from the working tree, `git remote -v`, `git rev-parse HEAD`,
README/docs, and any MR/ticket context. If a required public link or SHA cannot be
inferred, leave a placeholder in the draft and call it out before final delivery.

## Procedure

1. **Define the audience and choose a deck type.** Record learning goals,
   source links, the commit SHA, and the 5-12 code/doc targets to make easy to
   find. Read the matching deck-type reference, adapt its outline to this
   presentation, and follow its quality criteria.
2. **Research before writing slides.** Read the README, architecture docs, entry
   points, tests, and key files. For an MR, read the diff, commits, tests, rollout
   notes, and review discussion.
3. **Storyboard two paths.** Keep the main path to the reader promise:
   prerequisites before jargon, plain-language bridges before formalism,
   essential mechanisms and evidence, then a useful action, decision,
   discussion, or "where to look" close. Move derivations, exhaustive inventories,
   review history, and anticipated Q&A to an appendix; keep optional depth in
   links and tooltips. List slide titles as claims, give each slide one primary
   visual, and cut any slide with neither.
4. **Build clickable figures.** Hand-author SVGs under `images/`. Link diagram
   boxes and file names to pinned code, docs, MRs, tickets, or tests.
5. **Edit, build, preview.** Run `python3 build_deck.py`, render, and run the
   editorial pass against the Slide Quality Bar and review-shaped self-check.
   Do **not** export — exporting is a separate step that runs only on explicit
   request (see Exporting below).
6. **Deliver, then offer optional passes.** Tell the user where the built deck
   is and give a live-preview URL reachable from their machine — never
   `localhost` when the deck is hosted elsewhere. Unless review or grounding
   was already requested, stop and always offer exactly these three options:
   - **Run the automated review loop** — launch reviewer bots, then revise and
     rebuild the deck from their feedback.
   - **Verify claims against sources** — check and annotate claims against exact
     source passages.
   - **Run both quality passes** — run the review and rebuild first, then verify
     the final wording against sources.

## Slide Quality Bar

- Title is a claim, not a label: prefer "The Store boundary makes the core
  testable" over "Store".
- **Exactly one headline per slide.** If a figure carries its own title, it
  competes with the slide headline — keep whichever phrasing is stronger as
  the slide headline and strip the other. A figure may keep a small caption
  or legend line, never a second headline.
- One primary idea per slide. If the slide needs "and", split or cut.
- Prefer one large visual over many small bullets. Good visuals: map, flow,
  sequence, before/after, lifecycle, ownership table.
- Use code blocks only for commands, tiny APIs, or a decisive diff. Never paste
  a long code screenshot.
- Put "why this matters" near the figure, not in speaker notes.
- Keep bullets to the minimum needed to orient the visual. Five is usually too
  many.
- File names, diagram boxes, commands, and claims should link to code, tests,
  docs, tickets, or commits whenever practical.
- Keep required explanations visible. Put optional detail in `.term` tooltips
  for terms and a hover region for each component of a complex figure. Never
  hide prerequisites in tooltips.
- **Never write "hover", "click", or any other interaction instruction** in
  slide prose or figures. Tooltips must be discoverable on their own, the
  instruction describes the medium instead of the subject, and it reads as
  broken in PDF/PPTX exports.
- **The story arc is a deliverable.** Before delivery, read only the slide
  headlines top to bottom: they must read as one connected argument, each
  chapter opening with a promise and closing with a hand-off into the next.
  A deck of good slides in a weak order still fails review.
- **Animate where motion is the mechanism** — a walk, a loop, an
  accumulation, a step count. CSS-keyframe animation inside the SVG (see
  `references/animating-figures.md`); the static state must still show the
  complete labelled layout, since exports run no animation.

## Review-shaped self-check

Before first delivery, read only the main path of the deck as a cold audience
member.
For every slide, make the deck answer:

- **What does this mean?** Define prerequisites before first use.
- **How does it work?** Bridge each non-obvious mechanism, calculation, or
  transition in plain language before adding detail or notation.
- **Why should I believe it?** Put the direct verdict, decisive number,
  provenance, scope, and important caveat beside the evidence.
- **What follows?** Make the next idea clear; end with what this audience should
  do, decide, discuss, or inspect next.

If an answer needs a long detour, keep the necessary bridge in the main path and
move the depth to an appendix, link, or tooltip.

## Authoring rules

- **Edit `slides.tpl.qmd`, never `slides.qmd`** — the latter is generated and
  overwritten on every build.
- **Credit every third-party figure visibly on its slide** — paper crops,
  tables, equations, clips — never only in a hover:
  `Figure 2 from <a href="https://arxiv.org/abs/2003.08934">Mildenhall et al. 2020</a>, p. 5`
  (figure number, first author et al., year, link to the paper, page). The
  repo's MIT license excludes these; they stay the authors' property.
- **Embed figures with a `FIG` token** (HTML-comment syntax): `FIG:arch-hero`
  → inlines `images/arch-hero.svg` centered and sized. Variants: `FIGSM` (smaller,
  for slides with caption text) and `FIGFULL` (full-bleed). See `build_deck.py`.
- **Link liberally — boxes, file names, and prose alike.** Every diagram box and
  file name links into the repo, pinned to a commit SHA (`/-/blob/<sha>/path`) so
  links never rot; for an MR, link the diff/commit too. Also embed inline links in
  the body text — to docs, tickets, related code — so a reader can click through
  and verify. This is the signature move: the deck becomes a navigable index, not
  a wall of claims.
- **Figure canvases use the slide background color** (the theme's
  `--bg-slide`), not their own darker panel — a figure sitting in a visibly
  different box reads as an embedded screenshot instead of part of the slide.
- **For diagrams, hand-author SVGs** rather than screenshotting them — they stay
  crisp, themed, and clickable. (A screenshot of the real *product* is still great
  for showing a tool in action; this rule is about diagrams.) See
  `references/svg-figures.md` for the palette, arrow markers, and clickable-box pattern.
- **Open every deck with the title page**: `<!-- _class: title <type> -->`
  (`paper` · `mr` · `repo` · `tool` · `research`) with a kicker, `#` title,
  `##` one-line claim, byline and link chips — see `references/theme-reference.md`.
- **Theme primitives**: `_class: lead` / `_class: invert`, `<div class="columns">`,
  `<div class="card">`, `<span class="tag tag-accent">`, blockquote callouts.
  Full vocabulary in `references/theme-reference.md`.
- **Hover toolkit ships in the template — use it in every deck type, not
  just paper decks.** `slides.tpl.qmd` includes the body-level tooltip card
  plus `.term` (dashed-underline term explanations) and `.finfo` (info chip)
  styles; put `data-tiphead`/`data-tip` on elements instead of re-authoring
  tooltip machinery. When to reach for it, any deck: a **jargon term** part
  of the audience may not know → `.term` span with a one-sentence
  plain-language explanation; a **figure with several meaningful
  components** (architecture boxes, pipeline stages, curves, table rows) →
  a hover region per component (`data-tip` on the SVG box's `<g>`, or a
  transparent positioned span over an `<img>` region); a caveat that would
  clutter the slide → `.finfo` chip. Tooltips carry the depth; the slide
  stays scannable. Keep the block when trimming the template; full usage
  patterns in `references/paper-deck.md`.
- **Per-slide permalinks** (optional, nice for sharing): run
  `scripts/assign_slide_ids.py slides.tpl.qmd` before building to give each slide
  a stable `#uuid` anchor; `build_deck.py` wires up a click-to-copy hotspot on
  the page number.

## Verification

Run these before calling the deck done:

```bash
python3 build_deck.py
rg -n "Forge|your.gitlab|COMMIT|TODO|FIXME" slides.tpl.qmd images || true

# Catch overflow/overlap — content that is silently clipped and invisible:
python3 "$SKILL_DIR/scripts/check_layout.py" figs "$DECK_DIR"/images/*.svg   # figures (deterministic)
python3 "$SKILL_DIR/scripts/check_layout.py" slides "$DECK_DIR"              # quarto render + 1 PNG/slide to inspect
# add --strict to either for an exact Chromium pass/fail gate (needs playwright)
```

`check_layout.py` is the antidote to "looks fine to me": figures are checked
deterministically (text-past-box, off-canvas, box overlap); for slides it renders
one PNG per slide — **open each and confirm nothing is clipped at the bottom/right
edge** (overflowed slide content is invisible in the export). Then inspect the
rendered deck:

- No unreplaced placeholders unless explicitly called out as draft status.
- No text overlaps, tiny labels, clipped SVGs, mystery arrows, or slide content
  running off the edge.
- Every link that matters opens the intended code, diff, test, doc, or ticket.
- The final response names the deck path (and the export path only if an export
  was explicitly requested), plus any remaining placeholder inputs.

## Exporting (only when explicitly requested)

Exporting is **never** part of the default flow — the deliverable is the built
`slides.qmd` plus the rendered deck. Export only on explicit request, only in
the format(s) named:

```bash
bash "$SKILL_DIR/scripts/export.sh" "$DECK_DIR" html   # or: pptx / pdf
```

`html` is one self-contained file (images, CSS and MathJax inlined); `pptx` is
the repo's editable PowerPoint (native text boxes, SVG-picture figures). Clickable
in-figure links and per-slide permalinks survive **only in HTML** — suggest HTML
when those links carry the value, but never export unasked.

## Hosting

Decks live in this agentic-slides repo under `decks/<category>/<name>/`
(categories: `tools`, `repos`, `reading-groups`, `paper-reviews`,
`investigations`, `templates`; per-MR decks under `decks/mrs/mr-<iid>-<descr>/`)
and render in
place (`slides.html` + `slides_files/`, gitignored). The persistent deck server
is :8093 (`scripts/start.sh`; systemd unit `slides-server`): it re-renders a
deck on save, and every deck gets the Edit / Comments / HTML / PPTX / PDF
control bar, backed by the same server's comments/export API on :8094. The deck URL is
`http://<host>:8093/<category>/<name>/slides.md`. Report a URL the user can
open — the host's name or LAN IP, never `localhost` when they are on another
machine (the server binds 127.0.0.1 unless started with `SLIDES_HOST=0.0.0.0`).
Fetch the exact deck URL and confirm it returns the deck before reporting it.

- **Build every deck in the checkout the user's server already serves** —
  find it first (`systemctl --user show -p WorkingDirectory slides-server`,
  or the :8093 process's cwd); no `/tmp` decks or side previews. Hosting
  needs no commit or push; commit only when asked.
- **Reuse the running server.** Never restart it against a worktree, point
  it at a single deck, or start a second one on another port; if it is
  down, restore it with `scripts/start.sh` from its own checkout.
- **Verify the landing pages.** Rendering regenerates them
  (`quarto/scripts/gen_index.py`, post-render). After creating, revising,
  copying or moving a deck, fetch `http://<host>:8093/` and
  `/<category>/`, confirm each lists the deck exactly once and its link
  opens it (if not, run `gen_index.py` and recheck), and report those URLs
  with the deck URL.

## Pitfalls

1. **Never write a literal `FIG:name` token (in comment form) in prose/comments**
   — the build regex matches it anywhere and tries to inline a missing SVG.
   Refer to it descriptively instead.
2. **No blank lines inside an SVG file.** A blank line ends the CommonMark raw-HTML
   block early and fragments the figure. `build_deck.py` strips them on inline,
   but keep source SVGs blank-line-free too.
3. **SVG root must be exactly `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 600" ...>`**
   — `build_deck.py` string-matches that to inject `width`/`height`. Different
   viewBox → no sizing, figure renders at intrinsic size.
4. **Clickable in-figure links and permalinks only survive in HTML export**, not
   PDF/PPTX. Share the `.html` when links matter.
5. **Never write raw `:::` in prose** — it opens a Quarto fenced div. Use it only
   for `{.fragment}`, `{.notes}` and other deliberate divs.
6. **Do not hand-edit `slides.html` / `slides_files/`** — they are regenerated on every render.
7. **Paraphrased quotes never match.** Copy from `dump.txt`
   character-for-character; UNMATCHED usually means a paraphrase or an
   OCR/ligature difference — recopy a shorter exact span.
8. **Long quotes spanning lines/columns match poorly.** PyMuPDF searches
   within a text line. Keep each `quote` to one sentence or a distinctive
   clause.
9. **`not_found` claims have nothing to highlight.** `"quote": ""`, carry the
   gap in `claim`/`detail` and the reply; never invent a passage. It still
   counts in the tally.
10. **HTML quotes that span tags fall back to a leading word-run.** Prefer
    quotes within a single sentence/paragraph.
11. **SingleFile needs a headless browser and can be slow.** First `npx` run
    downloads Chromium; sandboxed/offline environments may block it. On
    failure `fetch.py` falls back to a raw download and warns — annotation
    still works. Copy quotes from `dump.txt`, not the styled `source.html`,
    either way.
12. **Optional automated review does not make baseline editorial quality
    optional.** Every first delivery still passes the review-shaped self-check.
13. **Do not hide required explanations in optional material.** Prerequisites and
    plain-language mechanism explanations needed to follow the claim stay in the
    main path; derivations and extra detail can move to a tooltip, link, or
    appendix.
14. **A figure is not evidence by itself.** Put the verdict, decisive number,
    provenance, scope, and important caveat beside it.
15. **Completeness must not bury the reader promise.** Move exhaustive
    inventories, review history, and anticipated Q&A to the appendix; end the
    main path with the action, decision, discussion, or next place to inspect.
