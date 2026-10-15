# Deck type: tool / workflow presentation

**Audience:** a teammate who might adopt a tool or workflow — they've never heard
of it, or aren't yet convinced.

**The reader should leave with** wanting to try it and knowing their first command.
Three jobs, in order: **(1) make them feel the pain, (2) show it working, (3) hand
them the on-ramp.**

## Branch first: one tool or many?

- **One tool → single-tool arc** (no agenda; dive straight into the problem).
- **2+ tools → umbrella arc:** `Title → Agenda (anchor links + one-line value prop
  each) → [per-tool mini-arc] × N → Thank You`. Each tool gets an `_class: invert`
  divider and a structurally **identical** 2-3 slide mini-arc, so the deck has
  rhythm.

## Recommended single-tool arc

1. **Title** (`_class: title tool`, kicker `Tool demo`) — H1 + a one-line tagline saying *what it is in plain
   words* ("an auto-curated AI research knowledge base"). No marketing.
2. **The Problem / The Solution** (2-column) — **mandatory and first.** Left
   `### The Problem`: 3-4 bullets in the reader's own voice, concrete and specific
   ("`squeue` output is a wall of text", not "observability is hard"). Right column
   named after the tool: how it kills each pain. This slide earns adoption — never
   skip it, even for capability-rich tools.
3. **Show it working** — the most important slide, and the one most often missing.
   Show the real product: a screenshot of the GUI / web / Slack / TUI (large
   `![w:900 center]` with a one-line caption, or `![bg right:45%]` beside feature
   bullets), or real command output. A keybindings table or feature list alone is
   *not* "showing it working."
4. **How it works / Architecture** (only if the flow or topology matters to the
   adopter) — usually a hand-authored SVG; see "Choosing the visual" below. Skip for
   a simple single-binary tool.
5. **Workflow / usage** — the lifecycle in **real, copy-pasteable commands**,
   chunked by phase (build → launch → iterate; or Save / Restore). Deep-link every
   script to its source. For an API/MCP surface, a **Tools table** (name +
   one-line purpose) is the right form.
6. **Get Started** (`## Quick Start` / `## Installation`) — exact copy-pasteable
   commands, real binary names, nothing elided. State the **lowest-friction path
   first** ("one remote server, no local setup"). Cover each client/runtime if
   there are several (cards or columns). List prerequisites here (auth, runtime,
   deps) so the reader doesn't hit an unlisted wall.
7. **Thank you** (`_class: lead`) — repo link + "Questions?".

## Signature techniques

- **Problem-first framing.** The reader recognizes their own pain in the first
  column before being sold anything — the single most adoption-friendly move.
- **Parallel Problem/Solution columns** make the value prop scannable in one glance.
- **Every command is real and copy-pasteable** — `uv tool install turm`,
  `claude mcp add --transport http …`, not pseudo-code or "run the included script".
- **Deep-links to source** on workflow/architecture slides — slide-to-code in one
  click.
- **"Why X?" recap** that preempts the "why not just use what I already have"
  objection ("same CLI flags as `squeue` — nothing new to learn").
- **Honest limits** — a `Caveats` / "not yet" note where they exist. Builds trust
  with an evaluating adopter.

## Choosing the visual

Always pick whatever teaches fastest — the question is "what makes the adopter
understand quickest", not "which category is this tool in". In practice:

- **Use a screenshot when one exists and helps.** For a GUI, web UI, Slack reply, or
  TUI, a shot of the real product working is the most convincing thing you can show.
- **Reach for a hand-authored SVG often — it's frequently the best option.** It shows
  *flow* a screenshot can't (producer → queue → consumer, read vs write paths), stays
  crisp and themed, and its nodes can deep-link to source. Between a busy screenshot
  and a clean diagram, the diagram usually wins.
- **A table** suits a flat *surface* — an API / MCP / CLI's tools, endpoints, or
  keybindings (name + one-line purpose).
- **Live command output** when neither fits — just show the real thing running.

Often the best answer is both: a screenshot of the product *and* an SVG of the flow.

## Quality bar

- [ ] **Pain before pitch** — the first content slide names a concrete problem the
      audience already has. No deck-wide assumption that they want it.
- [ ] **At least one "in action" view** — a screenshot, an SVG flow, or live
      output. If the deck never shows the tool doing its thing, it fails this bar.
- [ ] **Every command is real and copy-pasteable** — name and link the script; no
      hand-waving.
- [ ] **One frictionless on-ramp slide**, lowest-effort path stated first.
- [ ] **Prerequisites stated** (auth, runtime, deps).
- [ ] **Honest limits** noted where they exist.
- [ ] Consistent mini-arc if multi-tool; consistent column/card/tag idioms
      throughout.

## Anti-patterns to avoid

- **Capability-first with no problem slide** — a cold reader never learns *why this
  beats what they already do*. Lead with the pain even for capability-rich tools.
- **Never showing the product** — describing a Slack bot or web UI with zero
  screenshot. The adopter must *see* what using it looks like.
- **Fake demos** — a "Demo" slide that is just static commands or a keybindings
  table. Show it running.
- **Hand-waved get-started** — "run the included script" without naming it; eliding
  prerequisites the reader then hits as an unlisted wall.
