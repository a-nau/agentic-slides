# Distilled: how to read & present papers (verified sources)

Compact prescriptions distilled from the two adversarially-verified research
passes (2026-07). Use this offline; original links in SKILL.md's Sources.

## Reading

### Keshav — three passes (ACM SIGCOMM CCR 2007)
- Up to three passes, never front-to-back; decide after each whether to continue.
- **P1 (5-10 min):** title/abstract/intro, headings, conclusions, glance refs →
  the **five Cs**: Category, Context, Correctness (assumptions valid?),
  Contributions, Clarity → go/no-go.
- **P2 (≤1 h, skip proofs):** scrutinize **figures/graphs** — labeled axes?
  error bars? "Common mistakes like these separate rushed, shoddy work from the
  truly excellent." Exit: you can summarize the thrust, with evidence, to someone.
- **P3 (1-5 h):** *virtual re-implementation* — re-create the work; "identify
  and challenge every assumption in every statement"; find implicit assumptions,
  missing citations, technique problems. (UC Davis addition: enough info to
  reproduce? would you have done it the same way?)

### Hopkins / Roughgarden — Big Questions (MIT, ALT'22; theory-oriented)
- Five Big Questions: what problem · why interesting · primary contribution
  (often one theorem/definition) · how done · key takeaways.
- P1: **skip the abstract** ("written for experts") — first paragraphs, headers,
  conclusions, figures.
- P2: interrogate result *statements* via examples, improvement-over-obvious
  baselines, simplest nontrivial special cases; black-box the rest.
- P3: "prove it for yourself — the paper is a series of hints"; Chekhov's gun:
  "Assumptions must be used! What happens when assumptions break down?";
  expect published errors, fix them yourself.

### Shaw — conceptual/storyboard (CMU, arXiv 2405.02734)
- Read with a **goal**; find the core scientific argument; read selectively.
- Extract from a **close read of the abstract**: the problem/question, the
  *kind* of result, the coupled method + validation.
- Identify the paper *type* (analytical/empirical/technological/methodological)
  and tailor strategy; read critically "using criteria similar to review criteria."
- Critiques Keshav as textual-level, not conceptual-level.

### Ng — figures-first passes (Stanford CS230 L8)
- Passes: (1) title/abstract/**figures**; (2) intro + conclusions + figures,
  skim rest; (3) all minus math; (4) all minus what doesn't parse.
- Four questions: what did the authors try to accomplish · key elements ·
  what can *you* use · which references to follow.
- Volume: 5-20 papers = working knowledge; 50-100 = deep.

### Rush — pacing & skepticism (Cornell)
- Reading is genuinely hard — give it real time (a week for a new subject).
- **Depth over breadth**; "be actively skeptical of all claims" (2× for your own).

### Cross-school
- Keshav reads the abstract first, Hopkins skips it, and Shaw treats it as the
  primary object of close reading.
  None reads linearly; all use figures to understand methods and assess results.
  All critique assumptions.

## Presenting

### Simon Peyton Jones (1993 paper w/ Hughes & Launchbury; 2016 MSR deck)
- **One key idea**; say it aloud: "If you remember nothing else, remember this."
  Ruthlessly prune; narrow-deep > wide-shallow; a talk is a *taster*.
- **Structure: Motivation 20% + key idea 80% + "there is no 3."** You have
  2 minutes before the audience dozes.
- **Examples are your main weapon** (motivate, intuition, idea-in-action,
  extreme cases, shortcomings); framework-without-examples is "the Awful Trap";
  short on time → cut the general case, not the example.
- Slides: no opening outline; no related-work slide (praise the opposition
  inline); no dense notation; ≤6-7 things/slide; slides emphasise, never repeat,
  speech; animation "very very very sparingly."
- Delivery: enthusiasm is the most potent weapon; never apologise; questions
  are golden; finish on time — truncate and conclude.

### Journal-club protocols (.edu)
- **Stanford CCOP — six elements per figure:** aim · methods · results · YOUR
  interpretation · the AUTHORS' interpretation · contribution to the main question.
- **UVA Pharm:** open with the scientific model *before naming the paper*; one
  experiment per slide (technique → what it measures → result → how it answers
  the question → interpretive limits + controls). Success test: everyone can
  state the question, the most significant data, and whether it was answered.
- **Utah Genetics:** four sections (intro ≈4-5 slides, data/results,
  conclusions, **proposed future experiments**); a **self-made model diagram**
  shown early and revisited — better than reusing the paper's.
- Refuted in verification (don't cite): CCOP's "max 3 background slides" cap.

## Local practice (this repo)
- Compiled-truth wiki pages: bold-term claim-first density, numbers-first
  ablations, Connections/Significance — the *content* bar (not a slide format).
- arXiv source tarball beats the PDF for comprehension (lossless text, exact
  math, original figure assets); the PDF stays the annotation substrate —
  quotes must match its text layer. See `docs/research/2026-07-09-arxiv-source-vs-pdf.md`.
