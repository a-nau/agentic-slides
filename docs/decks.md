# Working with decks

## Adding a Deck

Quickest: ask your agent (the `slide-deck` skill builds and verifies the deck),
or scaffold one yourself:

```bash
scripts/new_deck.sh tools/my-topic        # → decks/tools/my-topic/slides.qmd
```

By hand:

1. Create a folder under the right category in `decks/` — one of `tools/`,
   `repos/`, `reading-groups/`, `paper-reviews/`, `investigations/`, or `templates/`
   (`paper-reviews/` has four worked examples):
   ```
   mkdir decks/tools/my-topic
   ```
2. Add a `slides.qmd`: slides are split on `---`, Marp comment directives
   (`<!-- _class: title -->`, `<!-- paginate: true -->`) work, and the theme is
   picked by the `css:` list in the front matter:
   ```markdown
   ---
   pagetitle: My Topic
   css:
   - ../../../quarto/themes/base.css
   - ../../../quarto/themes/agentic.css
   ---

   <!-- paginate: true -->
   <!-- _class: title -->

   # My Topic

   ---

   ## Second Slide

   Content here
   ```
3. The deck server renders it within a second or two and lists it on the
   landing page (`quarto/scripts/gen_index.py`, a post-render step).

A Marp deck works too: drop a `slides.md` (`marp: true`, e.g. from a Marp
slide-deck skill) into the folder and the deck server converts it to
`slides.qmd` next to it (`quarto/scripts/marp2qmd.py --keep`) on every change,
so the Marp file stays the source. `python3 quarto/scripts/marp2qmd.py <deck dir>`
converts one for good (deletes the Marp source).

## Short deck links

`/<deck>/slides.md` works without the category: the deck server redirects
`/<deck>/…` to `/<category>/<deck>/…` (`#N` slide and `#<uuid>` permalink
hashes included).

## MR decks

Walkthrough decks for individual merge requests live under
`decks/mrs/`, one folder per MR
(`mr-<iid>-<descr>`), with a landing page sorted newest-first and linked from the
main index. To add one, use the **`slide-deck`** skill (MR review deck type);
archive a merged one with `scripts/archive_mr.sh <iid>`.

## Git hooks

Some decks generate `slides.qmd` from a `slides.tpl.qmd` template via a
`build_deck.py` (FIG tokens → inline SVG; e.g. `decks/templates/visual-gallery`).
A `pre-commit` hook keeps the committed `slides.qmd` in sync: it rebuilds and
stages the output for any deck with staged changes. Install it once per clone:

```bash
scripts/install-hooks.sh
```
