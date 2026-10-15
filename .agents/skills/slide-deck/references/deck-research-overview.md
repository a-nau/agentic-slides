# Deck type: research presentation — literature overview

For a deep dive on a *single* paper, use `deck-research-deep-dive.md` instead.
This reference covers the **survey of a body of work**.

**Audience:** technical peers in a reading group who want to understand a *body* of
recent papers — the landscape, the key ideas, how the papers relate, and the
takeaways.

**Core principle:** a reading-group deck is **a navigable map of a body of work,
not N stapled paper summaries.** Pick one organizing axis (a *taxonomy*), make it
the spine, and make every paper reachable in one click. The deck doubles as a
curated, sourced reading list.

## Sourcing the content

Don't assemble the landscape from memory. Pull prior art, SOTA, benchmarks, and
paper/technique comparisons from a literature source — arXiv, Semantic Scholar,
Papers with Code, a team research wiki or knowledge-base MCP if you have one —
and the web. Use the same sourcing for both research-deck types (this one and
the deep dive). Go broader (a multi-source deep-research pass) when the user
asks for more coverage.

## Recommended arc

1. **Title** (`_class: title research`, kicker `Research overview`) — topic + a
   sharp scoping subtitle ("what's usable / where the gaps are") + a byline with
   audience and timeframe ("the 2023→2026 landscape").
2. **What you'll leave with** — promise 2-3 concrete outcomes, such as understanding
   methods, comparing papers, and identifying unresolved questions. For clickable
   decks, explain that each paper opens its card and the deck serves as a reading list.
3. **Agenda / TOC** — linked anchors with one-line glosses.
4. **Motivation: "why now"** — contrast prior art against the new wave; name the
   *jobs* the technology does (this framing recurs through the deck).
5. **The taxonomy slide** — define the organizing axis **explicitly**, name the N
   families/clusters, and **warn against the most common confusion** ("most
   confusion comes from comparing models across families as if they did the same
   job"). Render it as a spatial map of clickable paper nodes, **color-coded by
   category**.
6. **"The axes that matter"** — the comparison rubric *before* the papers: list the
   dimensions you'll compare on (e.g. multi-cam, conditioning, diffusion vs AR,
   real-time, open weights). Close with "no single one wins every axis."
7. **Timeline** — temporal evolution, color-coded by category, to show the
   trajectory / convergence.
8. **Per-category deep dives** (repeat per family): a category `_class: invert`
   divider → one concept slide (mechanism + Strengths/Limits columns) → a roster of
   that category's papers as clickable links with one-line distinguishing glosses.
   Add a highlighted `card` callout for the one non-obvious insight per family.
9. **(Optional) framework / tooling spotlight** — if one stack spans categories.
10. **Comparison matrix** — a feature table (papers × dimensions, ✅/❌), with **every
    paper name linked to its card**. Follow with a **decision guide**: "Need X? →
    use Y" prescriptions.
11. **Gaps & open questions** — split capability gaps vs methodology gaps and **cite
    contrary / negative evidence** (don't only sell). Then a numbered list of
    **actionable open questions tied to your team/context**, naming candidate
    approaches.
12. **Reading list** — curated and grouped (survey/concepts · open & runnable first
    · frontier/closed).
13. **Appendix — paper gallery** — one uniform card per paper, grouped by category
    with dividers.
14. **Closer** (`_class: lead`) — one provocative decision/discussion question to
    launch the conversation.

## Per-paper card template (uniform, scannable)

```
## <PaperName> <category-tag>
[columns-wide-left: figure on left | text on right]
  <main figure from the paper, max-height:56vh on a white card>
  **Task** — one sentence: the problem it solves
  **What's new** — 2-3 bullets (contributions)
  **Key result** — the headline number / benchmark    ← don't skip this
  *Venue Year · Institution*
  📄 Paper · 💻 Code · 🌐 Project · ▶️ Demo
```

## Signature techniques

- **Taxonomy-first** — the whole deck hangs off one *functional* axis (what the
  work *does*), not chronology or institution. State the axis, visualize it as a
  map, then use it as the navigation skeleton (dividers, color tags, gallery groups).
- **One color = one category, everywhere** — landscape map quadrants, timeline
  nodes, the `<span class="tag tag-X">` badge on every gallery card, legends. Teach
  the code once; the reader can then place any paper instantly.
- **Clickable everything → the deck IS a reading list** — TOC items, rosters, and
  *every cell of the capability matrix* link to `#p-<paper>` gallery cards; SVG
  diagram nodes wrap `<a href="#p-...">`; gallery cards link out to
  arXiv/code/project/demo.
- **Three orthogonal comparison views** — a spatial **map** (where it sits), a
  **timeline** (when / trajectory), and a feature **matrix** (what it can do). Each
  answers a different question; one alone is not enough for a body of work.
- **Breadth in the main deck, depth in the appendix** — the linear talk stays
  skimmable; per-paper detail lives behind one-click jumps.
- **Takeaways are contextual and actionable** — tie open questions to the audience's
  own work, name candidate methods, end on a decision question (not generic "future
  work").
- **Honesty** — make open-vs-closed availability a first-class comparison dimension;
  cite negative/contrary evidence; don't make the deck a sales pitch even when one
  vendor dominates.

## Quality bar

- [ ] One **functional** taxonomy axis, stated; category boundaries defended;
      straddlers flagged.
- [ ] One consistent color per category, used on every map, timeline, tag, legend.
- [ ] At least three orthogonal comparison views (map + timeline + matrix).
- [ ] Every paper claim is sourced (arXiv + code + project on every card); open vs
      closed marked explicitly.
- [ ] Every per-paper card carries a **key quantitative result**, not just
      contributions.
- [ ] Breadth in the main deck; per-paper depth one click away; matrix and rosters
      link into the gallery.
- [ ] Gaps section cites contrary evidence; open questions are actionable and tied
      to the audience's own work; closes on a decision question.

## Lessons from iterated status and investigation decks

- **Lead with the current state.** The result slide comes first; earlier
  generations, attempts and history move to the appendix. Reviewers of a
  living deck want "where are we" on slide 2, not a chronology.
- **Write the question each caption answers before the caption.** A figure
  caption is the answer to one explicit question ("does the frozen backbone
  still rank the same examples?"); if you cannot name the question, the
  figure is decoration.
- **Numbers carry a slide only when the table is large enough to read** —
  grow the table, shrink the prose around it, and put the one comparison that
  matters in the title.
- **Record disagreement next to the claim.** Where a second source, model or
  reviewer disagrees with a result, say so on the slide in a dimmer line;
  hidden caveats surface later as rounds.
- **Stable ids for recurring examples.** When a deck revisits the same
  samples (frames, scenes, runs) across builds, give each a fixed id and show
  it, so comments can name "frame 17" in any version.

## Anti-patterns to avoid

- **N stapled summaries** with no organizing axis — the reader leaves without a
  framework to slot future papers into.
- **Cards that list contributions but no headline number** — a reading group wants
  the key quantitative result. This is the most common miss.
- **Uncaptioned figures presented as standalone reference** — fine when a presenter
  narrates live, but a self-serve deck should annotate what to look at.
- **Single comparison view** — a matrix alone (or a timeline alone) under-serves a
  body of work; use all three.
- **Sales-pitch framing** — even when one vendor/stack dominates, keep the gaps and
  contrary evidence honest.

## Build note

If you want clickable diagram nodes (map/timeline boxes that jump to a paper card),
author the diagram as **SVG with embedded `<a href="#anchor">` links and inline it**
via the `FIG` token — `<img src>` references drop the in-figure links in HTML export.
