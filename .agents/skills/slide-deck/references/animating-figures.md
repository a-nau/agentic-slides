# Animating deck figures (inline SVG)

Part of the slide-deck skill. Read when a slide needs an animated figure — a
looping simulation, moving dots, a phased step-by-step walkthrough,
pulsing/blinking elements — or when an animated SVG renders blank or
invisible inside a built/served deck while looking fine standalone.

Animate with a single self-animating SVG in `images/`, inlined by
`build_deck.py` like any other figure. No GIF/video assets: stays
vector-crisp, in-figure links keep working, plays wherever the deck HTML is
viewed. **Author the animation as CSS keyframes in the figure's `<style>`**;
SMIL (`<animate>`/`<animateMotion>` tags) is safe only in its simplest form —
see the pitfall.

## The SMIL pitfall (why this reference exists)

(Measured under Marp, which renders each slide inside `<svg><foreignObject>`;
reveal.js slides are plain HTML, so the blanking may not reproduce here — CSS
keyframes stay the safe default either way.) In that context,
Chromium **silently blanks the ENTIRE figure** — every static box included —
when one element carries both an `<animateMotion keyPoints=... keyTimes=...>`
and a sibling `<animate>`. Bisected 2026-07-09:

| Construct (inside the built deck) | Result |
|---|---|
| `animateMotion` alone (plain or with keyPoints) | renders |
| `animate` alone (even invalid keyTimes) | renders (bad anim ignored) |
| `animateMotion` + `animate` on same element, no keyPoints | renders |
| `animateMotion` **with keyPoints** + sibling `animate` | **whole figure blank** |

The same file renders fine standalone and in a bare HTML page — "I opened the
SVG and it works" is false confidence. Simple SMIL loops (constant `dur`,
plain `path`, no keyTimes gymnastics) are fine in the deck; anything
multi-phase belongs in CSS keyframes.

## Core pattern: generator-computed CSS keyframes

For a phased storyboard (N phases in one loop), generate the SVG with a small
Python script — static skeleton plus one `@keyframes` rule per animated
element, percentages computed from the phase table. Adapt
[animation_example_generator.py](animation_example_generator.py).

- **Prefix every class and keyframe name per figure** (e.g. `rn-`): all
  figures share one HTML document; collisions bleed across slides.
- **Movement**: wrap the element in `<g class="...">` and animate
  `transform: translate(...)` through waypoints (3–4 waypoints approximate a
  curve). Keep the base element at the path's start coordinates so the layout
  checker sees real positions and the static frame looks right.
- **Design the static frame deliberately**: attributes (not CSS) define what
  PDF/PPTX exports and the pre-paint state show — e.g. `opacity="1"` on the
  phase-1 caption, `0` on the rest. Phase-1 elements also need a
  *starts-visible* keyframe branch (`0% {opacity:1}` … fade out at phase end)
  or they blink at every loop wrap — the generator's `vis()` handles phase 0
  this way. A robust alternative for loops that *reveal* a layout: park every
  element at attribute `opacity="0.25"` and animate **up** to 1 — the export
  then shows the whole labelled layout, dimmed, instead of a half-empty frame.
- **Never caption that a figure animates** ("animates in the HTML deck",
  "watch the dots"). That describes the medium, not the subject; the static
  frame must carry the slide on its own.
- Build contract still applies: exact `viewBox="0 0 1160 600"` root line,
  **no blank lines** in the file, run `scripts/check_layout.py figs` (it
  ignores animation, hence base positions must be on-canvas). A
  snap-confined inkscape cannot read `/tmp` or hidden dirs — for scratch
  decks, copy the SVG under a visible `$HOME` path before checking.

## Verify inside the deck, never standalone

1. `python3 build_deck.py`, then render the real HTML (`quarto/bin/quarto render`).
2. Headless screenshot of the slide: `scripts/check_layout.py slides <deck>` (or
   open `decks/<category>/<name>/slides.html#/N` in headless Chromium at 1280x720)
   → the figure must be **visible** (the pitfall's symptom is a blank slide).
3. Prove it *moves*: copy deck.html, inject
   `<style>[class*="rn-"]{animation-delay:-9.5s !important}</style>` before
   `</head>`, screenshot again → must show the mid-loop state.
   (`--virtual-time-budget` does NOT advance CSS animations; negative delay
   does.)
4. Probe one late phase the same way (e.g. `-18.5s`) to confirm the whole
   timeline. Counting is stronger than looking: evaluate how many animated
   groups are lit at each probe (e.g. 3 of 38 at 2 s, 19 of 38 at 11 s).
5. Overflow check without an export: with Playwright, compare each
   `section.scrollHeight` to `clientHeight`. Decks with the permalink hotspot
   carry a constant baseline of a few dozen px above `clientHeight` — measure
   a known-good slide first, then flag only slides well above that baseline.
   Fix by trimming the caption or adding `<!-- _class: fs-sm -->`, not by
   shrinking an essential figure.

## Lessons from iterated decks

Patterns that survived a dozen review rounds on long explainer decks:

- **Compute the geometry from the function it depicts.** Hand-placed arrows
  lie. When a figure shows a density, a gradient field, a schedule or a
  trajectory, have the generator script evaluate the real formula (or read a
  small data file written by a runnable toy, fixed seed) and emit the paths
  from that. The figure is then its own proof, and a reviewer's "is that
  arrow right?" has an answer.
- **One glyph per concept, reused everywhere.** Define the encoder shape, the
  token box, the noise dot once in the generator and call it from every
  figure; the reader binds the symbol once. Mixed vocabularies across slides
  cost more rounds than any single wrong figure.
- **Counts must be honest.** Nine dots labelled "~50" get flagged. Draw the
  real count, or elide visibly (`●●●● … ●●●● ~50`).
- **Legend rows beat in-figure labels** once more than two series share a
  panel; crowded labels overlap first and get noticed last.
- **Interactive widgets** (drag a point, pick a parameter): keep the JS in
  its own file next to the deck (`<script src="widget.js">`) — an inline
  `<script>` in slide markdown gets its `<` escaped to `&lt;` and every
  comparison breaks. Data files load relative to the deck URL
  (`fetch('data.json')`). Render the widget's default state into the template
  statically (a small generator between marker comments) so exports and the
  pre-JS paint show the finished picture.
- **Explainer video as a slide**: `<video controls preload="metadata">` beside
  a chapter list with timestamps and a transcript link. Every symbol defined
  on screen before it is used; one text serves narration and captions.

## Common mistakes

- Multi-phase SMIL with keyPoints windows → whole figure blank in the deck
  (port to CSS keyframes).
- Verifying only standalone / bare HTML / inkscape — all render cases the
  deck doesn't.
- Unprefixed keyframe or class names colliding with other figures in the same
  deck.
- Animating an element parked at `(0,0)` — off-canvas flags in the checker
  and a broken static frame.
