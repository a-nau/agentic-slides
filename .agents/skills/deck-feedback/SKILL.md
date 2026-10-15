---
name: deck-feedback
description: Use when a slide deck is built and needs a fresh-eyes comprehension check before delivery — spawns reviewer subagents (one codex, two claude) that read ONLY the presentation and ask questions from a junior ML engineer's perspective.
version: 1.0.1
tags: [slides, presentation, review, feedback, sub-agent]
---

# deck-feedback — junior questions from fresh eyes

Three reviewers, cold, deck only. They never see the paper, the repo, the
research notes, or the chat. If the deck can't answer their questions, the
deck has a gap — fix the deck, don't explain in chat.

## Inputs

- `DECK_DIR` — absolute path to the built deck directory. It must contain
  `slides.qmd`; reviewers may also inspect `images/` below it.
- `OUT` — absolute path to a fresh reviewer-output directory outside
  `DECK_DIR`.

Before launching reviewers, set both paths, verify `"$DECK_DIR/slides.qmd"`
exists, and create the output directory with `mkdir -p "$OUT"`.

## Artifacts

Each reviewer owns one question-list artifact:

| Reviewer | Artifact |
|---|---|
| Codex | `$OUT/codex-questions.md` |
| Claude reviewer 1 | `$OUT/claude-1-questions.md` |
| Claude reviewer 2 | `$OUT/claude-2-questions.md` |

Write only the reviewer's final numbered question list to its artifact. Do not
combine the lists until all three artifacts exist and are non-empty.

## Reviewers

Spawn all three **in parallel**:

- **1 × codex** — the latest Codex model (`<codex-model>`), read-only:

  ```bash
  (
    cd "$DECK_DIR"
    codex exec -m "<codex-model>" -s read-only --skip-git-repo-check \
      --ignore-rules --ignore-user-config --ephemeral \
      -o "$OUT/codex-questions.md" "<reviewer prompt below>"
  )
  ```

- **2 × claude** — Agent tool, `model: opus`, one reviewer
  prompt each. Give neither agent inherited chat or repo context; expose only
  `slides.qmd` and `images/` below `DECK_DIR` as read-only inputs. Save each
  agent's final response verbatim to its own Claude artifact.

  No Agent tool in this runtime (Codex/Cursor)? Run these two Claude CLI
  invocations in parallel:

  ```bash
  (
    cd "$DECK_DIR"
    claude -p --bare --disable-slash-commands --model opus \
      --allowedTools "Read,Glob" \
      --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Agent,Skill" \
      "<reviewer prompt below>" > "$OUT/claude-1-questions.md"
  )

  (
    cd "$DECK_DIR"
    claude -p --bare --disable-slash-commands --model opus \
      --allowedTools "Read,Glob" \
      --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Agent,Skill" \
      "<reviewer prompt below>" > "$OUT/claude-2-questions.md"
  )
  ```

## Reviewer prompt

Same prompt for all three (adapt paths):

> You are a junior machine learning engineer. You open this slide deck cold —
> you have NOT read the paper, codebase, or anything it is based on.
> Read ONLY the deck: `<deck-dir>/slides.qmd` (and `images/` if you need a
> figure's text). Do not open other files, do not search the web, do not read
> the source material.
>
> Your job is ONLY to ask questions. No praise, no fixes, no summaries, no
> rewriting slides. Output a numbered list; for each item:
> - **slide**: number or title where you got stuck
> - **question**: what you would ask the presenter
> - **why**: one line on what confused you (undefined term, missing step,
>   figure you can't parse, claim with no support, lost thread)
>
> Ask everything a junior would actually ask — basics included. 8-15
> questions is typical for a full deck. Make sure the list probes these
> recurring failure modes:
> - **meaning** — a prerequisite, term, symbol, or actor appears before it is
>   explained;
> - **mechanism** — the deck jumps over how a step, calculation, or transition
>   works;
> - **evidence** — a figure or result lacks a direct verdict, decisive number,
>   provenance, scope, or important caveat;
> - **thread** — the reader cannot tell why this slide follows, what belongs in
>   the main story versus the appendix, or what to do, decide, discuss, or inspect
>   at the end.

## Consume the feedback (main skill's job)

1. Collect all three question lists.
2. Cluster by slide/topic. **A question two or more reviewers share is a
   confirmed gap** — fix it, no debate. Single-reviewer questions: judge, fix
   the reasonable ones.
3. Fix in the deck itself, smallest sufficient edit first:
   - prerequisite used too early → move or add its plain-language bridge before
     first use;
   - undefined term → `.term` hover tooltip (+ glossary entry);
   - missing mechanism / lost thread → a bullet, sequence, or bridging slide;
   - unparseable figure → hover overlays, larger crop, or a simpler figure;
   - weak evidence → lead with the verdict and add the number, provenance, scope,
     and caveat beside the figure;
   - overloaded main path → keep the bridge, move the depth to the appendix;
   - unsupported claim or missing close → link, qualify, cut, or add the next
     action/decision.
4. Rebuild, re-verify (layout checks still apply).
5. Heavy rework (new slides, restructure) → run one more feedback round.
   Small patches → done after one round.
6. Report to the user: how many questions, the confirmed gaps, what changed.

## Outputs

- Three independent question-list artifacts under `OUT`.
- The updated, rebuilt deck with accepted gaps fixed in the deck itself.
- A user report with the total question count, confirmed gaps, and changes.

## Verification

1. Require all three reviewer invocations to exit successfully.
2. Run `test -s` on each artifact and confirm each contains only a numbered
   question list in the requested format.
3. Confirm every repeated question is represented in the gap clusters and
   every accepted gap maps to a deck edit.
4. Run the deck's existing build command and require it to succeed.
5. Re-run the deck's layout checks and inspect every changed slide for
   overflow, collisions, clipped text, and unreadable figures.
6. After heavy rework, repeat the review with a new `OUT` directory and three
   new reviewer processes.

## Rules

- Reviewers get the **built deck only**. Never pass research notes, the paper,
  or your own summary — that contaminates the fresh-eyes premise.
- Don't argue with a question. "It's on slide 12" means slide 12 failed to
  land where the reader needed it.
- Don't answer questions in the report instead of the deck.

## Pitfalls

1. **Output contamination.** Keep `OUT` outside `DECK_DIR` and use a fresh
   directory per round so reviewers cannot read prior questions or stale
   artifacts.
2. **Shared reviewer state.** Launch three independent processes or agents in
   parallel. Reusing one conversation invalidates the fresh-eyes comparison.
3. **Silent reviewer failure.** A missing or empty artifact is a failed
   reviewer, not a zero-question result. Rerun only that reviewer before
   clustering.
4. **Bare Claude authentication.** `--bare` deliberately skips persisted
   user configuration. If it cannot authenticate, use a clean Agent-tool
   reviewer or configure supported bare-mode authentication; do not remove the
   isolation flags.
