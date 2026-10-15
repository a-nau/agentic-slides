# Deck type: research presentation — single-paper deep dive

For a survey of *many* papers, use `deck-research-overview.md` instead. This
reference covers **one paper, presented in depth** — the format a reading group
uses when it spends a whole session on a single work.

**Audience:** technical peers who will dwell on one paper and want to understand it
well enough to *use it, extend it, or argue with it* — not just hear its abstract.

**Core principle:** a deep dive explains **how the method works and whether to
believe the results**, not what the paper is about. Teach the mechanism, walk the
key figure, show what the ablations prove, and end with an honest critique. If a
peer could get the same understanding from skimming the abstract, the deck failed.

## Sourcing the content

Before building, situate the paper: pull its prior art, the baselines it competes
against, and the SOTA context from arXiv, Semantic Scholar, the paper's own
references, a team research wiki if you have one, and the web. If a reference
implementation exists and is cheap to run, reproducing one headline number beats
quoting it.

## Recommended arc

1. **Title** (`_class: title paper`, kicker `Paper deep dive`) — paper name + a
   one-line "what it claims" subtitle + a byline *authors · institution · venue
   year* + link pills (arXiv · code · project).
2. **TL;DR / why this paper** — the headline result and why it matters, in 2-3
   sentences. The single takeaway a reader keeps if they remember nothing else.
3. **Problem & prior art** — the gap it addresses; what prior approaches did and
   *why they fell short*. This is the prior-work context that makes the
   contribution legible.
4. **The key idea** — the core insight in plain language, anchored to a known
   concept, **before any notation**. One sentence a peer could repeat at lunch.
5. **Method** (1-3 slides) — the architecture / algorithm walked at increasing zoom
   around the paper's **main method figure, annotated** (point at what to look at).
   Include the objective/loss and the train + inference procedure. Notation only
   after the intuition.
6. **What makes it work** — the details that matter: data, scale, compute,
   influential hyperparameters, and the non-obvious trick.
7. **Results** — the main table/plot with the **headline number, the metric, and
   the baseline it beats** all named. Don't show a table without saying which cell
   matters.
8. **Ablations — what drives the gain** — the reading-group payoff: which component
   is actually responsible. A method slide without this is marketing.
9. **Critical assessment** — strengths, limitations, threats to validity,
   reproducibility, what the paper *doesn't* show. A deep dive with no critique
   slide is a press release.
10. **Relation to our work** — why this team cares; what we'd borrow, test, or
    avoid.
11. **Discussion** (`_class: lead`) — 2-4 prompts that open debate (what would you
    ask the authors? what's the next experiment? does it transfer to our setting?).
12. **(Optional) appendix** — extra figures, the derivation, failure cases.

## Signature techniques

- **Mechanism over summary** — spend the slide budget on *how it works*. The
  abstract is the thing you are improving on, not reproducing.
- **Walk the main figure** — annotate the paper's key figure and narrate it; unlike
  an overview deck (where figures can stay terse), a deep dive must say what to look
  at.
- **Ablations carry the story** — lead the results with "which part matters", not
  the leaderboard.
- **Name the number, the metric, and the baseline** together — a result is
  meaningless without all three.
- **Intuition before notation** — give the plain-language idea, then the math for
  those who want it.
- **A real critique** — a dedicated limitations/validity slide; reading groups exist
  to interrogate, not applaud.
- **Reproduce if you can** — if a reference impl is cheap to run, show one number or
  a snippet you ran; it beats quoting and surfaces what the paper glosses.

## Quality bar

- [ ] Headline result + why-it-matters land on an early slide (TL;DR).
- [ ] The method is explained **mechanistically**, around at least one annotated
      figure, with the objective and train/inference procedure stated.
- [ ] Intuition precedes notation.
- [ ] Results name the number, the metric, and the baseline; ablations show what
      drives the gain.
- [ ] A genuine **critical-assessment** slide (limitations, validity,
      reproducibility, what's not shown).
- [ ] Tied to the audience's own work, and closes on discussion prompts.
- [ ] Every claim links to the paper / code; figures are the paper's own, sourced.

## Anti-patterns to avoid

- **Abstract-recital** — walking the paper's section order with no thesis. Lead with
  the takeaway, then teach the mechanism.
- **Leaderboard with no interpretation** — a results table where the audience can't
  tell which number matters or what it beats.
- **No critique** — presenting the paper as settled truth. The limitations slide is
  the point of a reading group.
- **Death by equations** — notation with no intuition; nobody follows a derivation
  they have no mental model for.
- **Every figure copied in** — choose figures that explain the method or support
  the conclusions; put the rest in an appendix.

## Build note

Use the `FIGSM` token for the annotated method figure so caption/annotation text
fits beside it; reserve `FIGFULL` (on a `_class: bleed` slide) for a single
dominant architecture figure. Annotate by overlaying labels in the SVG, not in
prose below it.
