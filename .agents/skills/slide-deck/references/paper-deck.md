# paper-deck — annotated paper presentation

Build a single-paper reading-group deck in three phases: research its arXiv
source and PDF, draft the presentation, then link every statement to evidence.
Complete each phase's required outputs before starting the next.

Start with a summary and early demonstration. Explain the method in steps,
assess evidence and ablations, and identify ideas to adopt. Use dense bold
highlighting and short blocks. Keep required explanations visible; put optional
detail in tooltips or the appendix.

Build mechanics come from the main `SKILL.md` of this skill: theme
vocabulary, SVG conventions, `build_deck.py` + FIG tokens, `check_layout.py`,
dev preview, Slide Quality Bar. Where the two conflict on paper decks, this
reference wins. Paper decks need the fact-map pipeline (`scripts/review.sh` +
`source-review/`) — build them in the agentic-slides repo, which ships the
full pipeline (see SKILL.md → Local hosting).

---

## Phase 1 — Research the paper

Extract everything the deck could need before writing a single slide. Reading
methods are distilled in **`reading-and-presenting-distilled.md`** (this
directory) — read it first; self-contained, no web access needed.

1. **Fetch both artifacts.** `scripts/review.sh paper-reviews/<slug>` (first
   pass) fetches the PDF into the scratch. When the paper is on arXiv, also
   pull the **source tarball** — denser, artifact-free:
   ```bash
   SCRATCH="${TMPDIR:-/tmp}/source-review/<slug>"   # review.sh's scratch; it prints SCRATCH=... but cannot export it into your shell
   curl -sL "https://arxiv.org/src/<id>" -o "$SCRATCH/src.tar.gz" && mkdir -p "$SCRATCH/src" && tar -xzf "$SCRATCH/src.tar.gz" -C "$SCRATCH/src"
   ```
   Read the `.tex` (usually `sections/*.tex`) for comprehension — lossless
   text, exact math, explicit structure. Grab **original figure assets** from
   the tarball instead of cropping PDF pages. No source? Fall back to the PDF
   dump.
2. **Keshav pass 1 (5-10 min):** the **five Cs** — Category, Context,
   Correctness (assumptions plausible?), Contributions (verbatim), Clarity.
   Becomes the compact 5-Cs slide.
3. **Shaw abstract close-read:** problem / kind of result / method+validation.
   Becomes the TL;DR.
4. **Figure inventory:** list EVERY figure and table; per figure note (a) what
   it proves, (b) deck-worthy or not, (c) a one-line forensics check (axes
   labeled? error bars? seeds? log-axis tricks?). Include only figures needed
   for the argument. Show interpretive limitations beside each figure and
   optional checks in tooltips.
5. **Demo media hunt, in priority order:** (a) video/GIF from project website
   or repo; (b) **generate a GIF/mp4 from time-series frames** in the tarball
   (ffmpeg concat, ~1s/frame); (c) static figure(s) + a written intuition of
   the motion. Avoid committing video: prefer remote embeds
   (`<video src="https://…">`); keep generated clips small (<1 MB plain blob
   is fine); a genuinely helpful clip with no stable remote home goes in via
   **git-lfs**, never dropped.
6. **Evidence + ablations:** headline numbers (number + metric + baseline),
   which ablation carries the story, what each proves vs merely suggests,
   missing ablations by name.
7. **Limitations:** the paper's own admissions (verbatim quotes), separate
   from your observations.
8. **Team relevance + prior-work check:** search the literature and any
   team wiki/notes for adjacent work. For each steal-list candidate gather: (a)
   prior/team work that *already does* it (name it — done-already becomes a
   "validated by X" note or gets cut); (b) transfer feasibility (what breaks,
   closest precedent); (c) backing wiki pages. Steal list and discussion must
   cite this evidence.
9. **Terminology audit:** audience is a **research engineer with broad
   knowledge, not in this subfield**. List every term such a reader may not
   know (objectives, metrics, architecture pieces, named baselines) + a
   one-sentence plain-language explanation each — these become hover tooltips
   and the appendix glossary. Unsure whether a term needs explaining? Explain
   it.

Exit bar: research-notes file in the scratch with the 5 Cs, figure inventory +
forensics, demo media plan, headline numbers, ablation verdicts, limitation
quotes, steal-candidate evidence with wiki citations, terminology list.

## Phase 2 — Draft the presentation

Plan 13-18 slides including the appendix. State claims in titles. **Bold the key
phrase of every sentence.** Use bullets by default; a paragraph is allowed only
when one sentence carries the point. Keep mechanisms, evidence, and important
limitations visible; put optional detail in the appendix or tooltips. Use one
source line per bullet/paragraph and a blank line before every `---`.

1. **Title** (`_class: title paper`, kicker `Paper deep dive`): H1 is a
   citation followed by the paper title — `# **Vaswani et al. (2017):** Attention
   Is All You Need` (the bold citation takes the type colour; keep the H1 to
   3 lines beside the motif). Subtitle = the one-line claim with the headline
   number, byline = `institutions · venue, arXiv date` (spell out short author
   lists there, e.g. `<strong>He, Zhang, Ren &amp; Sun</strong> · …`, when
   "et al." hides them), then link pills (arXiv · PDF · code · project).
   Examples: `decks/paper-reviews/*/`.
2. **TL;DR** — 4-5 heavily-bolded **bullets**: what it is, headline
   capability, headline number, release posture. No "if you remember nothing
   else…" summary quote line.
3. **Demo, early.** The Phase-1 demo media; autoplay muted loop for
   video/GIF; static images get the motion intuition explained. Caption cites
   the media's origin. **Restate the task explicitly** — one sentence naming
   input → output (e.g. "*Task: single RGB image → 4 s interactive video*"),
   so the demo is legible without narration. The demo makes the *problem*
   visceral — it sets up the next slide.
4. **The core idea** — right after the demo: one slide of *intuition*. 4-5
   bullets: **motivation first**, what prior setups do, why that breaks, what
   this paper does differently, what that buys. No architecture detail yet.
   When bullets can't carry the prior-vs-this contrast, consider a small
   animated figure — see `animating-figures.md` (this directory).
5. **The five Cs — compact:** open with one line naming the checklist
   ("Five Cs — a standard first-pass checklist for a paper: Category, Context,
   Correctness, Contributions, Clarity"), then five bullets, **one short line
   each**. No sub-bullets, no go/no-go verdict line (the read/skim/skip slide
   carries the recommendation).
6. **Should you read further?** *read if / skim if / skip if* bullets, each
   tied to what the reader works on (prior-work context). It comes before the
   evidence, so make it a **forward-pointing reading guide**: say what each
   cited section contains and which later slides carry the evidence for the
   verdict.
7. **Background**, only if the audience needs it: 1-2 slides,
   definitions-heavy (dashed term underlines), **visual where the topic allows**;
   no results spoilers.
8. **Pipeline at a glance — optional custom figure.** Draw a custom SVG
   abstraction **only when it adds something the paper's own figures can't**:
   no single overview figure exists, the overview needs team/repo deep links,
   or the real figure is unreadable at slide size. When the mechanism slides
   already walk every panel of the paper's main figure with hover overlays, a
   custom SVG duplicates them — skip it. If drawn: every component box gets
   BOTH a deep link (`<a href>`) AND a hover explanation
   (`data-tiphead`/`data-tip` on the box's `<g>`, rendered by the shared
   tooltip card below). Never native SVG `<title>` tooltips — unstyled, slow.
9. **Mechanism build-up:** 2-4 slides building the system in dependency order
   — representation/codec, then objective, then full architecture — each
   anchored on a paper figure or tarball asset. Lettered panels in the main
   figure → **every panel gets its own mechanism slide** with atomic hover
   overlays; don't drop a stage the figure calls out. Intuition before
   notation; generous bolding. **Titles are the claims themselves — never
   "Mechanism N:" prefixes.**
10. **The figures that matter:** explain figures/tables supporting the main
    claims. State numbers, metrics, and baselines **as bullets, never a caption
    paragraph**. Layout: **wide → figure above bullets; tall → `columns` with
    figure beside bullets.** Size figures
    **as large as the slide allows**, just before overflow (Phase-3 scrollHeight
    check); leave no dead space around a small crop. Show interpretive limitations
    beside each figure. Put optional checks in the hover chip; give sub-parts hover overlays.
11. **Evidence on trial + ablations:** strongest evidence first, what each
    ablation proves vs suggests, missing ablations by name.
12. **Challenge the assumptions:** the 2-3 claims most likely confounded, and
    why (compute budgets, metric blind spots, data provenance). Paper
    admissions referenced; your additions editorial.
13. **Steal list** — its own slide: what a practitioner would adopt, each with (a) rough
    effort estimate, (b) the **prior-work verdict from Phase 1** (already done
    by X → cite; not done anywhere → say so), (c) one-line feasibility note.
    Cites the prior-work evidence.
14. **What to keep from this paper** — 3-5 bolded, actionable sentences for a
    practitioner today; later practice is labelled as later background. The
    main story must end on a takeaway, not only on open questions.
15. **Discussion** — its own closing slide. **Not a bare ordered list**: each
    prompt gets a styled block — bolded one-line question + an indented,
    dimmer evidence line citing the paper/prior-work context that makes it
    concrete.
16. **Appendix divider + hover appendix** — after Discussion, an
    `invert` divider ("# Appendix" + "Reference for review: every hover note
    and term, restated in print. Not presented."), then (see "Reviewable hover
    content"):
    every hover text restated word-by-word, linked to its slide, fact-mapped
    like any other deck text.

### Hover tooltips — one shared card for SVG boxes and figure forensics

Both hover affordances use ONE body-level tooltip card. **The slide-deck
template ships it**: `template/slides.tpl.qmd` includes the `#tipcard` script
plus `.term`/`.finfo` styles near the top — start from the template and keep
that block; don't re-author it. (It must stay appended to `document.body` by
script — reveal.js scales the slide container with a CSS transform, where
`position: fixed` and CSS-only popovers break. A deck NOT started from the
template: copy the HOVER TOOLKIT block from `template/slides.tpl.qmd`.)

Usage — SVG pipeline box (attributes on the box's `<g>`, no `<title>` child):
`<g data-tiphead="Codec encoder" data-tip="Frozen DINOv3 features + one learned bottleneck compress each view 192x.">…</g>`

Usage — figure forensics chip in a results-slide heading:
`<span class="finfo" data-tiphead="Figure forensics" data-tip="No error bars — one run per condition; the log time axis compresses the divergence.">ⓘ forensics</span>`

No double quotes inside `data-tip` values (HTML attributes); the card shows
them as plain text.

### Figure hover overlays — explain the parts of paper figures

Raster figure crops get **invisible hover regions** — hover any part for an
explanation (same tooltip card). Wrap the image in a relative container,
position transparent spans with percentage coordinates:

```html
<span style="position:relative; display:inline-block"><img src="images/paper/fig9.png" width="880"/><span data-tiphead="Teacher forcing curve" data-tip="Past the 4 s training window gFID jumps roughly 10x and stays there." style="position:absolute; left:66%; top:2%; width:26%; height:32%"></span><span data-tiphead="Training window" data-tip="The dashed line marks the 4 s training horizon — everything to its right is extrapolation." style="position:absolute; left:59%; top:0%; width:6%; height:55%"></span></span>
```

**Granularity is atomic, not coarse:** one region per meaningful box, table
row, curve, axis, legend, or labeled sub-panel. An architecture figure with
ten boxes gets ~ten regions ("Encoder / Decoder" alone is not enough); a
results figure gets a region per row and per curve. Read the actual crop (Read
tool renders it) to place coordinates. Regions non-overlapping. Every overlay
text also appears in the hover appendix.

### Terminology tooltips — write for the broad research engineer

Every term from the Phase-1 terminology audit gets an inline tooltip where it
first appears:

```html
<style>
.term { border-bottom: 1px dashed #3d5a8c; cursor: help; }
</style>
```

`<span class="term" data-tiphead="Flow matching" data-tip="Trains the network to predict the velocity that moves a noise sample toward the data sample along a straight path — a simpler, more stable cousin of diffusion training.">flow matching</span>`

**Every metric the deck names (FID/FVD variants, the paper's own metrics,
probes) must be hover-explained** wherever it appears — `.term` span, figure
overlay region, or both. The dashed underline is deliberately distinct from
review-mode underlines. If the term sits inside an annotated bold run, don't
wrap it (splits the text node, breaks the underline match) — shorten the
annotation's `wiki_quote` or attach the span to adjacent plain text.

### Formulas — intuition first, subparts labeled

Every formula the deck shows:

- **State the intuition of the whole formula** in a bullet next to it — what
  it computes, why the paper needs it, plain language.
- **Label subparts with brackets under the formula**:
  `\underbrace{...}_{\text{plain-language name}}` per meaningful term, so the
  formula self-explains on the slide.
- If underbrace labels can't carry the full meaning, **add hover info** (ⓘ
  chip or invisible overlay regions over the rendered math) — texts restated
  in the hover appendix like any other hover.

### Reviewable hover content — the hover appendix

Hover texts are attributes, not text nodes — invisible to review mode, so
they can't be underlined in place. Therefore: an **appendix section after the
Discussion slide** restates every hover text —

- one appendix slide per group ("Appendix — figure hover notes 1/N",
  "Appendix — glossary"), as many slides as needed — atomic overlays produce
  dozens of entries;
- **every entry — glossary included — links back to a slide** (`[s7](#7)`);
  glossary terms without an inline span link to the slide where they are most needed;
- each entry: slide link + tooltip head + the hover text **word-by-word**
  (must match the `data-tip` attribute exactly — scriptably checkable);
- entries are annotated through the normal pipeline (wiki_quote = the appendix
  line, quote = the paper passage) — figure-overlay notes and paper-defined
  terms as `reference`/`definition`; general-background glossary lines the
  paper doesn't state stay unannotated (common knowledge, not paper claims).

The appendix is exempt from "titles are claims"; density rules still apply.

### Per-slide font sizing — match density

Define once in the deck's global `<style>` block, set per slide via `_class`:

```html
<style>
section.fs-lg { font-size: 1.14em; }
section.fs-sm { font-size: 0.9em; }
section.fs-xs { font-size: 0.8em; }
</style>
```

`<!-- _class: fs-lg -->` on sparse slides so they don't look empty;
`fs-sm`/`fs-xs` on dense slides (appendix, big evidence slides) instead of
overflowing. Default for everything in between — don't micro-tune.

### Hard style rules

- **Bullets over prose:** every content slide defaults to bullets, including
  figure explanations. Use a paragraph only when one sentence carries the point.
- **Paragraph length:** never exceed about four rendered lines.
- **Not verbose:** compact beats complete.
- **Bold generously:** every sentence's key phrase.
- **No meta-labels in titles**: no "Mechanism 2 —", no "Verdict: go" lines;
  the claim itself is the title.
- **Figures as large as possible, media never overflowing** — grow figures to
  the overflow limit; shrink fonts (`fs-sm`) before shrinking an essential figure
  (check `scrollHeight` AND `scrollWidth`). In columns, tune the split
  (`grid-template-columns: 57% 43%`) so the figure fills its column.
- **Say each thing once.** If the figure states it, the caption does not
  repeat it; every statement has one home on the slide, and the figure wins.
- **A tooltip that could be a slide, is one.** Hover text holds a single
  concept in two or three sentences. When an explanation outgrows that, give
  it a slide and link to it from the term.
- **Slide prose stands alone.** Never answer a reviewer on the slide ("Yes —
  a displacement, not a position", "Reading check: right, with two
  refinements"). Only the reviewer saw the comment; rewrite the passage so a
  cold reader gets it (the `address-feedback` skill enforces this).
- **Markdown is inert inside raw HTML blocks.** In a `<div>` or `<figure>`,
  `**bold**` renders literally — use `<b>`, `<i>`, `<code>`.
- **No hover-instruction prose**: never "hover any box for an explanation"
  helper text. The affordances (dashed underline, ⓘ chip, legend) carry
  discoverability; the title slide's one-line review legend is the only
  permitted meta text.
- **Explain for the outsider**: broad ML knowledge, zero subfield context —
  jargon gets a `.term` tooltip, not silence.
- **Hyperlink referenced works**: every named paper, benchmark, or tool
  (baselines, table rows, glossary entries) gets its canonical link. Resolve:
  the paper's own `.bib`, then arXiv/web search. **Only link when it's obvious which work
  is meant.** Mind the fact map: never split an annotated run — wrap the
  whole bold run (`**[text](url)**` keeps one text node) or link adjacent
  plain text.
- Demo/figure reuse: cite origin (paper Fig. N p. M / tarball asset / website).

### Slide patterns that earned their keep

Harvested from long-iterated paper and method decks:

- **Let the reader guess first.** When the paper has a side-by-side (ours vs
  baseline, real vs generated), show it unlabelled as the demo — "which is
  which?" — and reveal on the next slide. It makes the quality claim felt
  before it is stated.
- **Ablations as Q&A.** One bullet per ablation: the question it answers in
  bold, then the paper's own answer, close to verbatim, with the table or
  figure reference. Verdicts lead with the direct answer and use the figure's
  own labels ("Large is enough"), not a paraphrase the reader must map back.
- **A "Keep these N sentences" close.** Three to five numbered sentences that
  the reader should carry out, each linking back to the slide that earned it.
  Stronger than a bullet summary because each sentence is a full claim.
- **A symptom → likely cause → first check table** for method decks: it turns
  the mechanism slides into something a practitioner can act on, and it is
  the slide people come back to.
- **Related-work table columns**: work (linked) · primary job · the
  transferable mechanism · one representative number — plus a one-line note
  that the numbers are within-paper anchors, not a leaderboard.
- **Anticipated Q&A appendix**: two or three `fs-xs` slides of "Q: … — A: …"
  bullets grouped by theme (scope and I/O · training and cost · evidence and
  transfer), each answer pointing at the slide or paper table that backs it.
- **Cross-deck links by stable id.** Link to another deck's slide through its
  per-slide UUID (`/paper-reviews/<slug>/slides.md#<uuid>`), never `#12`;
  reorderings in the other deck are otherwise silent breakage.
- **Explain a formula on one axis.** When several quantities are "the same
  arrow in different units" (ε, x₀, score, velocity; or losses that differ
  only by weighting), draw them on one shared axis rather than as four
  equations; two columns of formulas never read as one idea.

### Review rounds — the iteration loop

Decks that got good went through many short rounds, not one long pass:

1. **Snapshot the open comments first** — record the exact comment ids you
   read before editing. Resolve only those ids afterwards; anything that
   arrived mid-round stays open for the next one. Sweeping "everything open"
   silently buries comments you never read.
2. **One commit per round** with a message that names what changed in the
   reader's terms ("intuition slide leads, codec slide sharpened").
3. **Each round ends in the served browser**: slide count, overflow probe,
   `pageerror` empty, videos playing, animations proven to move.
4. **Restructure before polishing.** The most common round-two change was
   not a fix but a move: main path down to ~25 slides, depth to an appendix
   behind an `invert` divider that says "everything below is optional".

## Phase 3 — Fact-map for review

A reviewer must be able to verify the deck **by clicking**, statement by
statement.

1. Author `annotations.json` in the scratch, maximal coverage: every factual
   sentence gets an underline. Every annotation requires `source: "sN"`, mapped
   positionally to the deck front-matter `sources:` list (`s0` = first source,
   `s1` = second, and so on). Kinds: `claim` (red) / `important` (yellow —
   headliners) / `definition` (green — terms) / `reference` (gray —
   paraphrase, captions, framing). Editorial takeaways = `claim` + verdict
   `not_found` + honest `detail` (renders as subtle wavy underline with an
   explanation card). Editorial marks sparingly, on factual editorial *claims*
   only — **never on the steal list or discussion slides**: those are openly
   our ideas, they stay unannotated.
2. `wiki_quote` = verbatim DECK text on ONE source line inside one markup run;
   `quote` = verbatim from the **PDF text layer** (validate against the PDF
   dump even when researching from `.tex` — ligatures/hyphenation differ;
   pick clean substrings, avoid `×`, curly quotes, hyphen-linebreaks).
3. Run `scripts/review.sh paper-reviews/<slug>`; fix every UNMATCHED quote.
4. Verification bar (all must hold, in a served browser):
   - highlights == annotation count; **zero** `[source-review]` warnings;
   - no slide `scrollHeight > clientHeight+2`;
   - forward jump (underline → passage) and reverse jump (passage → slide)
     work;
   - hover legend renders; the shared tooltip card appears on hover over each
     affordance class: pipeline SVG box, forensics chip, figure overlay
     region, `.term` span (`#tipcard` is a direct child of `document.body`);
   - every `data-tip` on figure overlays and `.term` spans has its
     word-by-word counterpart in the hover appendix (scriptable: extract all
     `data-tip` values, assert each appears in the appendix slides' text).
5. Target: ≥2 annotations per content slide. The review panel is the deck's
   reference list — a fact that can't be mapped gets cut or marked editorial.

## Annotation pipeline mechanics

Repo standard (slides repo): front-matter `sources:` list; deck at
`decks/paper-reviews/<slug>/slides.md` (Marp; for Quarto decks the review
pipeline is not wired up yet); `scripts/review.sh` drives
fetch → annotate → ingest (this skill's `scripts/annotate/` — workflow in
`annotate-source.md`, this directory) and appends the `sr:review-include`
block; kinds/verdict rendering per `source-review/CONTRACT.md`. Note:
`review.sh` is deck-repo glue, NOT shipped with this plugin — the slides
repo's copy must point at this skill's `scripts/annotate/` directory (a
hardcoded checkout path there today; check it resolves on your machine). Gotchas (Marp and Quarto alike): soft line
breaks render as `<br>` (unwrap prose); `---` needs a preceding blank line;
`grep` may misread PDF dumps as binary — use `rg`.

## Sources & credits

Distilled prescriptions (offline, self-contained):
**`reading-and-presenting-distilled.md`** (this directory). Original sources:

- S. Keshav, *How to Read a Paper*, ACM SIGCOMM CCR 2007 — five Cs, figure
  forensics, challenge-every-assumption ([paper](http://ccr.sigcomm.org/online/files/p83-keshavA.pdf)).
- Mary Shaw (CMU) — abstract close-read ([arXiv 2405.02734](https://arxiv.org/pdf/2405.02734)).
- Andrew Ng, Stanford CS230 L8 — figures-first passes ([video](https://www.youtube.com/watch?v=733m6qBH-jI)).
- Sam Hopkins (MIT)/Tim Roughgarden — contribution-in-one-sentence, baseline &
  special-case tests ([ALT'22 slides](https://let-all.com/assets/slides/How-to-ALT22-Sam.pdf)).
- Sasha Rush — active skepticism of all claims ([thread](https://x.com/srush_nlp/status/1276514523726389250)).
- Simon Peyton Jones — one key idea, examples-first ([page](https://simon.peytonjones.org/great-research-talk/)).
- Journal-club protocols: [Stanford CCOP](https://ccop.stanford.edu/post/how-to-give-a-journal-club-presentation),
  [UVA Pharm](https://pharm.virginia.edu/wp-content/blogs.dir/49/files/2014/03/JournalClubTips.pdf?r=1),
  [Utah Genetics](https://www.genetics.utah.edu/journal-club-and-research-in-progress-information/tips-on-preparing-a-jc-or-rip).
- Compiled-truth wiki pages — claim-first density as the content bar.
