# Template deck — repo/tool introduction

A ready-to-build starter deck in the house style. Copy this whole folder into a
deck folder under `decks/<category>/` of the agentic-slides repo, then edit `slides.tpl.qmd` and the
figures in `images/`.

```bash
REPO="$(git rev-parse --show-toplevel)"      # run from inside the agentic-slides repo
SKILL_DIR="$REPO/.agents/skills/slide-deck"
DECK_DIR="$REPO/decks/<category>/my-deck"

python3 build_deck.py                         # slides.tpl.qmd + images/*.svg -> slides.qmd
(cd "$REPO" && quarto/bin/quarto render "$DECK_DIR/slides.qmd")   # or let the :8093 server do it
bash "$SKILL_DIR/scripts/export.sh" "$DECK_DIR" html
```

- **`slides.tpl.qmd`** — the source you edit. `slides.qmd` is generated; don't edit it.
- **`images/*.svg`** — clickable diagrams (1160x600 canvas, links pinned to a SHA).
- **`build_deck.py`** — inlines figure tokens and injects per-slide permalinks.

Before final export, replace every `Forge`, `your.gitlab/org/repo`, and `COMMIT`
with the real subject, repo URL, and pinned commit SHA. Keep the deck brief at
the top accurate while drafting; remove only comments that no longer help the
next author.
