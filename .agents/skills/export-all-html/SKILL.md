---
name: export-all-html
description: Use when asked to export all slide decks (or the whole deck collection) as single-file / self-contained / offline HTML, or to build a browsable HTML bundle of every deck in this repo.
---

# Export All Decks as Self-Contained HTML

## Overview

One command exports every deck in `decks/` to a single self-contained HTML
file each, plus an `index.html` grouped by category in the same order as the
decks/ overview page (newest-first within each category):

```bash
.agents/skills/export-all-html/export_all_html.sh              # → exports/<category>/<deck>.html + exports/index.html
.agents/skills/export-all-html/export_all_html.sh /some/dir    # → same layout under /some/dir instead
```

The script is bundled with this skill and works from any cwd (it cd's to the
repo root itself).

## What it does

- Iterates the overview's categories (tools, repos, reading-groups,
  paper-reviews, investigations, mrs, templates) — hidden folders
  outside that list are skipped, just like on the landing page.
- Each deck goes through `scripts/export.sh <deck> html` (Quarto
  `embed-resources`, MathJax inlined), so images and styles are inlined —
  files can be mailed or moved anywhere.
- With a custom output dir, exports still land in `exports/` first and are
  copied over.

## Notes

- Requires the Quarto toolchain (`quarto/scripts/setup.sh`). Expect ~5–15 s
  per deck; a full run over all decks takes 15–40 min. Run it in the background.
- A deck that fails to export is skipped and excluded from the index; the
  script lists failures at the end and exits non-zero.
- Everything is re-exported on each run (no freshness cache).
