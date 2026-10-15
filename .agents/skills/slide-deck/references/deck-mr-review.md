# Deck type: MR / merge-request review

**Audience:** a reviewer who must understand a change well enough to **approve,
request changes, or ask the right question** — and know exactly which lines to
stare at.

**The reader should leave with** answers to the reviewer's three implicit
questions: *(a) what changed and why, (b) what could go wrong, (c) where do I look
to check.* A deck that only answers (a) is documentation, not a review aid — it
has failed its purpose.

**Prime directive:** spend slide budget proportional to **risk, not line count**.
A 10-line formula inside a 2,000-line refactor deserves half the deck.

## Research before slides

Read the diff, commits, tests, rollout notes, and review discussion. Pin links to
the **MR head SHA**; link deleted files / before-state to the **base commit** so
before/after is checkable. Decide the single riskiest part of the change — that
decision drives the whole deck.

## Recommended arc

1. **Title** (`_class: title mr`, kicker `MR review`) — plain-English change name (NOT the raw MR title) +
   a one-line subtitle stating the change in human terms + an `MR !N` byline.
   Include an **at-a-glance metadata line** so the reviewer sizes the change
   before reading: **+lines / −lines**, **commit count**, **author**, and
   **reviewer(s)** — e.g. `+127 / −8 · 4 commits · @author → @reviewer`. Render it
   as a `<p class="stats">` row (`.add` / `.del` colour the line counts) and
   deep-link the `MR !N` pill in `<p class="links">` to the MR.
2. **Thesis + "Where to look hard"** (`_class: lead`) — the problem and fix in 2-3
   sentences, then a **bolded paragraph naming the single riskiest part** and
   stating the deck will spend its focus there. End with the SHA-pinned-links note.
3. **Agenda** — anchored two-column chapter list; 5-7 chapters.
4. **Hero diagram** (`_class: invert` divider + full-bleed clickable SVG) — the
   whole change at a glance, `<span class="tag tag-green">Tap any box</span>`.
5. **The problem** — the concrete defect with numbers (e.g. "3 replicas × 12 = 36
   threads on 12 slots"); a root-cause blockquote.
6. **The two kinds of change** (mandatory if the diff mixes refactor + behavior) —
   explicitly partition into `mechanical / behavior-preserving` vs
   `behavior-changing`, then point the reviewer at the latter: "the refactor is the
   bulk of the diff; X is the bulk of the risk."
7. **The mechanism / fix** — **literal before/after code fences** (`# before` /
   `# after`), one card per edit, "no other call sites touched" reassurance where
   true.
8. **The hard part** (1-2 slides) — the formula / trade-off / equivalence claim.
   Worked **truth tables on real configs**. Name the **invariant** it must preserve
   and whether it does. Name the **edge case** and whether any shipping config hits
   it (live risk vs latent risk).
9. **Questions for the author** — 3-4 numbered cards, each a genuine review concern
   phrased as a decision the author must make (correctness gap, missing test,
   hard-coded constant, merge/sequencing collision).
10. **Tests & gaps** — what the tests assert + the pass result, **and explicitly
    what they don't cover**. Note whether runtime/integration verification has
    actually run.
11. **Files — where to look** — inventory split by behavior / mechanical / tests /
    docs; the diff size with the tests-docs fraction called out ("+127/−8 across 7
    files — mostly tests + docs"); a **"You want to… | Open"** line-anchored link
    table.
12. **Thank you** (`_class: lead`) — recap + the one open question + `MR !N`.

## Signature techniques

- **Risk-first, repeated.** "Where to look hard" on slide 2, a dedicated hard-part
  chapter, "Questions for the author", and a closing "the risk is X, not the diff"
  recap all converge the reviewer's attention. This is the biggest reviewer win.
- **Behavior vs mechanical split** so the reviewer doesn't burn attention on rename
  noise.
- **Before/after is literal** — diff fences and/or paired red/green SVGs, never just
  prose.
- **Worked numeric tables** for any arithmetic-heavy change (integer division,
  capacity formulas, token ids) — proven on real presets. This is where review bugs
  hide.
- **Test coverage is assessed, not just listed** — gaps and unrun verification
  called out. "No test for the floor=1 2× case" is reviewer gold.
- **Diff size + composition** stated to calibrate effort.
- **Cross-MR / merge-order hazards** flagged if the change collides with other open
  work.
- **Every file/box deep-links**, pinned to MR head SHA, with line anchors
  (`#L84-99`); deleted files and before-state link to the base commit.

## Quality bar

- [ ] The riskiest part is named on slide 2 and gets a dedicated chapter. If the
      deck can't name what to scrutinize, it has failed.
- [ ] Behavior vs mechanical is separated whenever the diff mixes them.
- [ ] Before/after is literal (fences and/or paired SVGs).
- [ ] Invariants and edge cases are stated, with whether any shipping config
      triggers them (live vs latent).
- [ ] Test coverage is *assessed* — gaps and unrun verification called out.
- [ ] Open questions are real decisions phrased for the author, not rhetorical.
- [ ] Closes by restating the one thing to settle.

## Anti-patterns to avoid

- **The subsystem-explainer trap.** A deck that explains how the system works but
  never tells the reviewer *what to scrutinize* answers only (a). For a large MR
  that is the worst failure mode — explain mechanism in service of risk, not for
  its own sake.
- **Reporting tests without assessing them** — "7 passed" tells the reviewer
  nothing about coverage. Name what the tests *don't* prove.
- **Rhetorical open questions** — every "Questions for the author" item must be a
  decision the author actually has to make.
- **Dense un-bolded thesis prose** — if the buried risk isn't bolded, a skimming
  reviewer misses it.
