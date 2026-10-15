# Deck type: repo introduction / onboarding

**Audience:** a new engineer who must understand a codebase — its architecture,
subsystems, data flow, entry points, and where to look for things.

**The reader should leave with** a *mental model* of the system and a *navigable
map into the real code* they can keep open while spelunking.

**Prime directive:** concept before code, big-picture first, and every file name
and diagram box is a clickable deep-link pinned to one commit.

## Research before slides

Read the README, architecture docs, entry points, and key files until you can
explain the system end to end. An onboarding deck is only as trustworthy as the
understanding behind it.

1. **Pin a commit** of the target repo; record the SHA and the date. Every link
   in the deck points at that SHA so links never rot silently.
2. **Trace one real flow end to end — when it's cheap to.** If the repo has a test,
   smoke run, or simple setup that exercises the main path, follow it through the
   code (tagging process/IPC boundaries — `SUBPROCESS`, `FILE`, `gRPC`, `QUEUE`,
   `THREAD` — with `file:line`) and keep it as a checked-in `CALL_CHAIN.md`-style
   doc; the flow slides render it. **If there's no easy way to run the code, ask the
   user** whether a trace is feasible or worth it before investing — don't fabricate
   one from static reading alone.

Minor note (only when it applies): if the repo mixes shipped and unshipped work,
state what is NOT there — branch-only features, roadmap, framework-owned vs
repo-owned — so the deck doesn't blur reality and roadmap.

## Recommended arc

1. **Title** (`_class: title repo`, kicker `Repo tour`) — one sentence: what the repo *is*; link the repo
   with `<a class="repo-link" href="…">owner/repo</a>`.
2. **What you'll leave with** — the promise + the deep-link contract ("every box
   and file name is a clickable link, pinned to `<sha>`, snapshot `<date>`").
3. **Agenda** — numbered chapters, each an in-deck anchor link; doubles as TOC.
4. **Big Picture chapter** (concept before code):
   - *What is X?* — plain definition, the 3-4 moving parts, why it exists (vs the
     predecessor / alternative).
   - *The mental model* — anchor to a **known abstraction** the reader already has
     (e.g. "the classic agent ⇄ environment loop"). This slide hosts the **hero
     architecture diagram** with clickable boxes + a text legend mapping each box
     → its entry-point file.
   - *Glossary* — define the jargon **early**, before subsystem chapters use it.
   - *Repository layout* — package / module map.
   - *How it flows end to end* — one numbered high-level walkthrough; link out to
     the full trace if you built one.
5. **Run It / hello-world, placed early** — a copy-pasteable command, local vs
   cluster, and a "why start here?" rationale (it exercises the interfaces you're
   about to learn). Include a setup/troubleshooting note.
6. **Subsystem chapters**, one per major subsystem, each:
   - opens with an `_class: invert` divider: title + one-line scope
     (`package/path — what it does, where it runs`);
   - leads with *What is this subsystem?* before any file;
   - shows a flow/structure diagram with **clickable boxes**;
   - ends with a **blockquote invariant** stating a rule needed for correct behavior
     (e.g. "one frozen config drives everything downstream — never ad-hoc flags");
   - cross-links sibling chapters inline.
7. **Engineering culture / conventions** — code principles, test philosophy,
   review norms. State the target reader ("someone who will modify the code").
8. **Where to look — the reference map** — a by-subsystem index of key files, each
   deep-linked. The take-home artifact.
9. **"You want to…" task index** (high value) — a cookbook of common first
   changes: "add a reward → edit X; add a model → edit Y; change config → Z".
10. **Close** (`_class: lead`) — a directed next action ("run the smoke test, then
    follow the reference map into the code").

## Signature techniques

- **Concept before code, in every chapter.** Black-box external dependencies on
  first mention; explain *what* and *why* before showing a file.
- **The hero diagram is the spine** — reused/referenced across chapters, its boxes
  restated as a text legend, every box a deep-link to its entry-point file.
- **Same flow at increasing zoom** — high-level numbered walkthrough → per-subsystem
  diagram → optional full interactive trace with an "open full ↗" escape hatch.
- **Glossary early, invariants as blockquotes, reality-vs-roadmap tagged**
  (`on main` / `design proposal` / dashed "roadmap" edges).

## Quality bar

- [ ] Every architecture box and every file name in prose hyperlinks to that file
      at the pinned commit. Inline SVGs (not `<img>`) so links survive HTML export.
- [ ] Concept-before-code holds in every chapter.
- [ ] Glossary appears *before* the jargon is used, not as an appendix.
- [ ] Each subsystem chapter ends with its required invariant.
- [ ] Pinned SHA + dated snapshot on slide 2 and in the footer.
- [ ] Ends with both a map (where things live) and a directed first action.

## Anti-patterns to avoid

- **Design-review depth in an onboarding deck.** A subsystem that needs deep
  mechanism detail (rendezvous protocols, CAS races) does not belong at onboarding
  altitude — mark it skippable-on-first-read or move it to an appendix. Onboarding
  altitude ≠ design-review altitude.
- **Uneven altitude with no signposting** — don't ramp from conceptual to
  distributed-systems-fluent without telling the reader they can skip.
- **Speculative chapters in the main flow** — temporary shims and design proposals
  expand scope past "understand the *current* codebase"; appendix them.
- **By-subsystem map but no task cookbook** — the "you want to…" index is the
  single highest-value slide for someone about to make a change. Don't omit it.
